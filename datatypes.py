import pickle
import random
import sys
import time

import config
import crypto
import database
import utils
import interface


def transaction(wallet_in: str, wallet_out: str, amount: int, index: int,
                private_key=None):
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
            database.write(transaction_dict, 'transaction', transaction_hash[0])
            database.sub('wallet', wallet_in, amount)
            database.add('wallet', wallet_out, amount)

    return sign, verify, store
