from nacl import encoding, signing

import config
import crypto
import database
import threading
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
    return (block_hash_at_index(idx-1) for idx in range(block_height(),0,-1))


def read_block(block_index):
    block_hash = block_hash_at_index(block_index)
    if block_hash is None:
        return None
    return database.read('block', block_hash)


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


def add_mean_block_size(block_size):
    old_mean = database.read('block_size', 'mean')
    new_mean = (3 * old_mean + block_size) / 4
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
    threading.Thread(target=store_block, kwargs=header).start()
    networking.BASE_NODE.node().send_block(**header)


def load_key(private):
    private = signing.SigningKey(private.encode(),
                                 encoder=encoding.URLSafeBase64Encoder)
    public = private.verify_key
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


def difficulty_at_index(index, default=5000):
    if index is None:
        return default
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


def balance(address=None):
    if address is None:
        address = public_key()
    atomic_amount = database.read('wallet', address)
    if atomic_amount is None:
        return 0
    return atomic_amount / config.UNIT


def handle_split(ip):
    height = networking.BASE_NODE.node().request_height(ip)
    own_height = block_height()
    if height <= own_height:
        return
    skip = height - own_height
    split = networking.BASE_NODE.node().get_split(ip, skip)
    old_block = [read_block(index) for index in range(own_height - split - 1, own_height)]
    if not all(store_block(index=index, at_index=True, resolve=False,
                           **networking.BASE_NODE.node().request_block(index,
                                                                       ip)) is None for
               index in range(own_height - split - 1, own_height)):
        any(store_block(index=index, at_index=True, resolve=False, **block) for
            index, block in enumerate(old_block))
