import database
import datatypes


def store_unverified_transaction(wallet_in, wallet_out, amount, index, signature):
    _, _, store = datatypes.transaction(wallet_in, wallet_out, amount, index,
                                        cache=True)
    store(signature)


def verify_transaction(wallet_in, wallet_out, amount, index, signature):
    _, verify, _ = datatypes.transaction(wallet_in, wallet_out, amount, index)
    return verify(signature)


def read_block(block_index):
    block_hash = database.read('connection+block_index+block', block_index)
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


def mailbox_handler(mailbox):
    def assign(data):
        mailbox[0] = data
        return False

    return assign
