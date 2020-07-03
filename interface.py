import threading
from nacl import encoding, signing

import config
import crypto
import database
import datatypes
import networking
import utils


def store_unverified_transaction(wallet_in, wallet_out, amount, index, signature):
    datatypes.transaction(wallet_in, wallet_out, amount, index, signature=signature,
                          cache=True)[2]()


def verify_transaction(wallet_in, wallet_out, amount, index, signature):
    datatypes.transaction(wallet_in, wallet_out, amount, index, signature=signature,
                          cache=True)[1]()


def block_hash_at_index(block_index):
    block = database.read('connection+block_index+block', str(block_index))
    if block is None:
        return config.GENESIS_HASH
    return block


def reverse_hashes():
    return (block_hash_at_index(idx - 1) for idx in range(block_height(), 0, -1))


def read_block(block_index, return_hash=False):
    block_hash = block_hash_at_index(block_index)
    if block_hash is None:
        return None
    block = database.read('block', block_hash)
    if return_hash:
        return block, block_hash
    return block


def read_transaction(transaction_hash):
    return database.read('transaction', transaction_hash)


def store_block(*args, ip=False, at_index=False, resolve=True, **kwargs):
    function = getattr(datatypes, 'block_at_index' if at_index else 'top_block')
    _, _, _, store = function(*args, **kwargs)
    value = store()
    if value is False and resolve and ip:
        handle_split(ip)
    elif not resolve:
        return value


def add_mean_block_size(block_size, factor=3, divisor=4):
    old_mean = database.read('block_size', 'mean')
    new_mean = (factor * old_mean + block_size) / divisor
    database.write(new_mean, 'block_size', 'mean')
    return old_mean


def block_height():
    return database.read('block_height', 'main')


def mailbox_handler(mailbox):
    def assign(request_type, data):
        mailbox[request_type] = data
        return False

    return assign


def send_block(header: dict):
    threading.Thread(target=store_block, kwargs={**header, 'at_index': True}).start()
    networking.BASE_NODE.node().send_block(**header)


def load_key(private):
    private = signing.SigningKey(private.encode(),
                                 encoder=encoding.URLSafeBase64Encoder)
    public = private.verify_key.encode(encoding.Base32Encoder).decode()
    database.write(public, 'keypair', 'public')
    database.write(private, 'keypair', 'private')


def keypair():
    private = database.read('keypair', 'private')
    if private is None:
        _, _, keygen = crypto.eddsa()
        public, private = keygen()
        database.write(public, 'keypair', 'public')
        database.write(private, 'keypair', 'private')
    else:
        public = database.read('keypair', 'public')

    return public, private


def active_peers():
    return database.read('peer', 'white')


def public_key():
    public = database.read('keypair', 'public')
    if public is None:
        public, _ = keypair()
    return public


def private_key():
    private = database.read('keypair', 'private')
    return private.encode(encoder=encoding.URLSafeBase64Encoder).decode()


def difficulty_at_index(index, default=10 ** 6):
    if index is None:
        return default
    index = int(index)
    start_height = index - config.LWMA_WINDOW - 1
    if start_height < 1:
        return default
    recent_blocks = [read_block(idx) for idx in range(start_height, index)]
    if not all(recent_blocks):
        raise UserWarning("Index too high.")
    recent_blocks = [(block['timestamp'], block['difficulty']) for block in
                     recent_blocks]
    timestamps, difficulties = list(zip(*recent_blocks))
    return utils.next_difficulty(timestamps, difficulties)


def difficulty(index=None):
    if index is None:
        index = block_height()
    return difficulty_at_index(index)


def mine_top(threads=4):
    wallet, private_key = keypair()
    _, mine, _, _ = datatypes.top_block(wallet, [], private_key=private_key)
    mine(True, send_block, int(threads))


def transact(wallet_out, amount):
    amount = float(amount) * config.UNIT
    wallet, private_key = keypair()
    index = database.read('sent', 'transactions')
    sign, _, store = datatypes.transaction(wallet, wallet_out, amount, index,
                                           private_key, cache=True)
    sign()
    transaction = store()
    if transaction is None:
        print('Insufficient funds.')
        return
    database.add('sent', 'transactions', 1)
    del transaction['data_type']

    networking.BASE_NODE.node().send_transaction(**transaction)


def balance(address=None, atomic=False):
    if address is None:
        address = public_key()
    atomic_amount = database.read('wallet', address)
    if atomic_amount is None:
        return 0
    if atomic:
        return atomic_amount
    return atomic_amount / config.UNIT


def handle_split(ip):
    height = networking.BASE_NODE.node().request_height(ip)
    own_height = block_height()
    if height <= own_height:
        return
    skip = height - own_height
    split = networking.BASE_NODE.node().get_split(ip, skip)
    old_blocks = []
    index = own_height - split - 1
    for idx in range(index, own_height):
        old_blocks.append(read_block(idx))
        undo_block(idx)
    while store_block(at_index=True, resolve=False,
                      **networking.BASE_NODE.node().request_block(index,
                                                                  ip)) is not False:
        index += 1
    if index >= own_height:
        return

    for block in old_blocks:
        if block is None:
            break
        store_block(at_index=True, resolve=False, **block)


def undo_block(block_index):
    block, block_hash = read_block(block_index, True)
    block_size = sys.getsizeof(pickle.dumps(block, protocol=4))
    _ = add_mean_block_size(-block_size, 4, 3)
    old_mean = database.read('block_size', 'mean')
    reward = config.reward_function(block_index, block_size, old_mean)
    database.sub('wallet', block['wallet'], reward)
    database.sub('block_height', 'main', 1)
    database.write('block', block_hash, {})


def undo_top_block():
    return undo_block(block_height() - 1)
