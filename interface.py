import config
import crypto
import database
import datatypes
import networking
import utils


def store_unverified_transaction(wallet_in, wallet_out, amount, index, signature):
    _, _, store = datatypes.transaction(wallet_in, wallet_out, amount, index,
                                        cache=True)
    store(signature)


def verify_transaction(wallet_in, wallet_out, amount, index, signature):
    _, verify, _ = datatypes.transaction(wallet_in, wallet_out, amount, index)
    return verify(signature)


def block_hash_at_index(block_index):
    return database.read('connection+block_index+block', str(block_index))


def read_block(block_index):
    block_hash = block_hash_at_index(block_index)
    if block_hash is None:
        return None
    return database.read('block', block_hash)


def read_transaction(transaction_hash):
    return database.read('transaction', transaction_hash)


def store_block(*args, **kwargs):
    _, _, _, store = datatypes.block(*args, **kwargs)
    store()


def add_mean_block_size(block_size):
    old_mean = database.read('block_size', 'mean')
    new_mean = (3 * old_mean + block_size) / 4
    database.write(new_mean, 'block_size', 'mean')
    return old_mean


def block_height():
    return database.read('block_height', 'main')


def mailbox_handler(mailbox):
    def assign(data):
        mailbox[0] = data
        return False

    return assign


def send_block(header):
    networking.BASE_NODE.send_block(**header)
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


def mine_top(wallet, private_key):
    height = block_height()
    last_hash = block_hash_at_index(height - 1)
    start_height = height - config.LWMA_WINDOW - 1
    if start_height < 0 or last_hash is None:
        difficulty = 1
    else:
        recent_blocks = [read_block(idx) for idx in range(start_height, height)]
        recent_blocks = [(block['timestamp'], block['difficulty']) for block in
                         recent_blocks]
        timestamps, difficulties = list(zip(*recent_blocks))
        difficulty = utils.next_difficulty(timestamps, difficulties)

    check_hash, mine, verify, store = datatypes.block(height, wallet, [], difficulty,
                                                      last_hash,
                                                      private_key=private_key)
    mine(True, send_block)
