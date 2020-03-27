import pickle
import random
import sys
import time

import config
import crypto
import database
import interface
import utils


def transaction(wallet_in: str, wallet_out: str, amount: int, index: int,
                private_key=None, cache=False):
    transaction_dict = {'wallet_in': wallet_in, 'wallet_out': wallet_out,
                        'amount':    amount, 'index': index
                        }
    signer, verifier, _ = crypto.eddsa(wallet_in, private_key)
    validated = [None]
    transaction_hash = [None]

    def sign():
        return signer(crypto.pickle_hash(transaction_dict))

    def verify(signature: bytes):
        if not verifier(crypto.pickle_hash(transaction_dict), signature):
            return False
        if not database.read('wallet', wallet_in) >= amount:
            return False
        tx_hash = crypto.pickle_hash(transaction_dict)
        if database.read('transaction', tx_hash) is not None:
            return False
        validated[0] = True
        transaction_hash[0] = tx_hash
        return True

    def store(signature: bytes):
        if validated[0] or (validated[0] is None and verify(signature)):
            if cache:
                database.append(transaction_dict, 'transaction', 'cache')
            else:
                database.write(transaction_dict, 'transaction', transaction_hash[0])
                database.sub('wallet', wallet_in, amount)
                database.add('wallet', wallet_out, amount)

    return sign, verify, store


def block(block_index, wallet, transactions, difficulty, block_previous, timestamp=None,
          nonce=None,
          signature=None, private_key=None):
    header = {'wallet':     wallet, 'transactions': transactions, 'nonce': nonce,
              'timestamp':  int(time.time()) if timestamp is None else timestamp,
              'difficulty': difficulty, 'block_index': block_index,
              'signature':  signature, 'block_previous': block_previous
              }

    signer, verifier, _ = crypto.eddsa(wallet, private_key)

    def sign():
        header['signature'] = None
        header['signature'] = signer(crypto.pickle_hash(header))

    if signature is None:
        sign()

    diff = 2 ** 512 - 1
    diff //= difficulty

    def check_hash(header_hash):
        return utils.bytes_to_int(header_hash) < difficulty

    def random_hash():
        header['nonce'] = random.randint(0, 2 ** 512)
        sign()
        return crypto.pickle_hash(header)

    def mine():
        header_hash = random_hash()
        while check_hash(header_hash):
            header_hash = random_hash()
        return header

    def verify():
        block_hash = check_hash(crypto.pickle_hash(header))
        if not check_hash(block_hash):
            return False
        header['signature'] = None
        if not verifier(crypto.pickle_hash(header), signature):
            header['signature'] = signature
            return False
        if database.read('connection+block_index+block', block_index) is not None:
            return False
        header['signature'] = signature
        for i in range(transactions):
            transactions[i] = transaction(**transactions[i])
            if not transactions[i][0]():
                return False
        return True

    def store():
        if verify():
            database.write(header, 'block', crypto.pickle_hash(header))
            for tx in transactions:
                tx[2]()
            block_size = sys.getsizeof(pickle.dumps(header, protocol=4))
            old_mean = interface.add_mean_block_size(block_size)
            reward = config.reward_function(block_index, block_size, old_mean)
            database.add('wallet', wallet, reward)
            database.add('block_height', 'main', 1)

    return check_hash, mine, verify, store
