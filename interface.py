import os

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
        return os.urandom(256).decode(errors='ignore')
    return block


def read_block(block_index):
    block_hash = block_hash_at_index(block_index)
    if block_hash is None:
        return None
    return database.read('block', block_hash)


def read_transaction(transaction_hash):
    return database.read('transaction', transaction_hash)


def store_block(*args, **kwargs):
    _, _, _, store = datatypes.top_block(*args, **kwargs)
    store()


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


def send_block(header):
    networking.BASE_NODE.node().send_block(**header)
    store_block(**header)


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


def difficulty_at_index(index):
    start_height = index - config.LWMA_WINDOW - 1
    if start_height < 1:
        return 5000
    recent_blocks = [read_block(idx) for idx in range(start_height, index)]
    if not all(recent_blocks):
        raise UserWarning("Index too high.")
    recent_blocks = [(block['timestamp'], block['difficulty']) for block in
                     recent_blocks]
    timestamps, difficulties = list(zip(*recent_blocks))
    return utils.next_difficulty(timestamps, difficulties)


def mine_top():
    wallet, private_key = keypair()
    _, mine, _, _ = datatypes.top_block(wallet, [], private_key=private_key)
    mine(True, send_block)


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
