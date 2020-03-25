import crypto
import time
import utils
import random


def make(block_index, wallet, transactions, difficulty, timestamp=None, nonce=None):
    header = {'wallet':     wallet, 'transactions': transactions, 'nonce': nonce,
              'timestamp':  int(time.time()) if timestamp is None else timestamp,
              'difficulty': difficulty, 'block_index': block_index
              }

    diff = 2 ** 512 - 1
    diff //= difficulty

    def check(block_hash=None):
        header_hash = crypto.hash(header)
        return (utils.bytes_to_int(header_hash) < difficulty and
                (block_hash is None or block_hash == header_hash))

    def mine():
        while check():
            header['nonce'] = random.randint(0, 2 ** 512)
        return header

    return check, mine