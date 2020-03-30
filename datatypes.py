import multiprocessing
import pickle
import random
import sys
import threading
import time

import config
import crypto
import database
import interface
import utils


def transaction(wallet_in: str, wallet_out: str, amount: int, index: int,
                private_key=None, cache=False, signature=None, data_type='transaction'):
    if data_type != 'transaction':
        raise UserWarning
    transaction_dict = {'wallet_in': wallet_in, 'wallet_out': wallet_out,
                        'amount':    amount, 'index': index, 'data_type': 'transaction',
                        'signature': signature
                        }
    signer, verifier, _ = crypto.eddsa(wallet_in, private_key)
    validated = [None]
    transaction_hash = [None]

    def sign():
        transaction_dict['signature'] = signer(crypto.pickle_hash(transaction_dict))

    def verify():
        updated_signature = transaction_dict.pop('signature')
        transaction_dict['signature'] = None
        if not verifier(crypto.pickle_hash(transaction_dict), updated_signature):
            transaction_dict['signature'] = updated_signature
            return False
        transaction_dict['signature'] = updated_signature
        try:
            if not database.read('wallet', wallet_in) >= amount:
                return False
        except TypeError:
            return False
        tx_hash = crypto.pickle_hash(transaction_dict).decode(errors='ignore')
        if database.read('transaction', tx_hash) is not None:
            return False
        validated[0] = True
        transaction_hash[0] = tx_hash
        return True

    def store():
        if validated[0] or (validated[0] is None and verify()):
            if cache:
                database.append(transaction_dict, 'transaction', 'cache')
            else:
                database.write(transaction_dict, 'transaction', transaction_hash[0])
                database.sub('wallet', wallet_in, amount)
                database.add('wallet', wallet_out, amount)
            return transaction_dict

    return sign, verify, store


def block(block_index, wallet, transactions: list, difficulty, block_previous,
          timestamp=None, nonce=None, signature=None, private_key=None):
    header = {'wallet':     wallet, 'transactions': transactions, 'nonce': nonce,
              'timestamp':  int(time.time()) if timestamp is None else timestamp,
              'difficulty': difficulty, 'block_index': str(block_index),
              'signature':  signature, 'block_previous': block_previous
              }
    signer, verifier, _ = crypto.eddsa(wallet, private_key)

    def sign():
        header['signature'] = None
        header['signature'] = signer(crypto.pickle_hash(header))

    if signature is None:
        sign()

    diff = 2 ** 256 - 1
    diff //= difficulty
    mining_manager = multiprocessing.Manager()
    mining = mining_manager.list()
    mining.append(False)
    mining_thread = []
    verified = [None]

    def update_timestamp():
        if mining[0]:
            header['timestamp'] = int(time.time())
        while mining[0]:
            time.sleep(1)
            header['timestamp'] += 1

    def add_transactions():
        while mining[0]:
            new_transactions = database.read('transaction', 'cache')
            transactions.extend(new_transactions)
            database.write([], 'transaction', 'cache')
            database.append(new_transactions, 'transaction', 'mined')
            time.sleep(1)

    def check_hash(header_hash):
        return utils.bytes_to_int(header_hash) < diff

    def random_hash():
        header['nonce'] = random.randint(0, 2 ** 256)
        sign()
        return crypto.pickle_hash(header)

    def mining_process(event, callback):
        header_hash = random_hash()
        threading.Thread(target=add_transactions, daemon=True).start()
        threading.Thread(target=update_timestamp, daemon=True).start()
        while not check_hash(header_hash):
            header_hash = random_hash()
        multiprocessing.Process(target=callback, args=(header,)).start()
        event.set()

    def mining_handler(callback, threads):
        found_block = multiprocessing.Event()
        processes = [multiprocessing.Process(target=mining_process,
                                             args=(found_block, callback))
                     for _ in range(threads)]
        any(proc.start() for proc in processes)
        while not found_block.wait(1e-3) and interface.block_height() <= block_index:
            time.sleep(1e-3)
        any(proc.terminate() for proc in processes)
        any(proc.join() for proc in processes)

    def mine(state, callback=None, threads=16):
        mining[0] = state
        if state and len(mining_thread) < threads:
            mining_thread.append(threading.Thread(target=mining_handler,
                                                  args=(callback, threads)))
            mining_thread[-1].start()
        elif not state and mining_thread:
            mining_thread.clear()

    def _verify():
        if not check_hash(crypto.pickle_hash(header)):
            return False
        header['signature'] = None
        if not verifier(crypto.pickle_hash(header), signature):
            header['signature'] = signature
            return False
        if database.read('connection+block_index+block', str(block_index)) is not None:
            return False
        header['signature'] = signature
        for tx in transactions:
            if not isinstance(tx, dict):
                raise UserWarning
            if not transaction(**tx)[1]():
                return False
        return True

    def verify():
        if verified[0] is None:
            verified[0] = _verify()
        return verified[0]

    def store():
        if verify():
            database.write(header, 'block',
                           crypto.pickle_hash(header).decode(errors='ignore'))
            for tx in transactions:
                transaction(**tx)[2]()
            block_size = sys.getsizeof(pickle.dumps(header, protocol=4))
            old_mean = interface.add_mean_block_size(block_size)
            reward = config.reward_function(block_index, block_size, old_mean)
            database.add('wallet', wallet, reward)
            database.add('block_height', 'main', 1)
            return
        return False

    return check_hash, mine, verify, store


def block_at_index(index, wallet, transactions: list, timestamp=None, nonce=None,
                   signature=None, private_key=None, **kwargs):
    return block(index, wallet, transactions, interface.difficulty_at_index(index),
                 interface.block_hash_at_index(index), timestamp, nonce, signature,
                 private_key)


def top_block(*args, **kwargs):
    index = interface.block_height()
    return block_at_index(index, *args, **kwargs)
