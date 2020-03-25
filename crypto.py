from hashlib import blake2b
from ecpy.eddsa import EDDSA
from random import randint
import pickle

CRYPTO = EDDSA(blake2b)


def eddsa(public=None, private=None):
    if public is None:
        private = randint(0, 2 ** 512)
        public = CRYPTO.get_public_key(private)

    def sign(msg):
        return CRYPTO.sign(msg, private)

    def keys():
        return public, private

    def verify(msg):
        return CRYPTO.verify(msg, private)

    return sign, verify, keys


def pickle_hash(obj):
    return blake2b(pickle.dumps(obj, protocol=4)).digest()
