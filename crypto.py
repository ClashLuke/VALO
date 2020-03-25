from hashlib import blake2b
from ecpy.eddsa import EDDSA, ECPrivateKey
from ecpy.curves import Curve
from random import randint
import pickle

CRYPTO = EDDSA(blake2b)
CURVE = Curve.get_curve('Curve448')


def eddsa(public=None, private=None):
    if public is None:
        private = ECPrivateKey(randint(0, 2 ** 512), CURVE)
        public = private.get_public_key()

    def sign(msg):
        return CRYPTO.sign(msg, private)

    def keys():
        return public, private

    def verify(msg, sig):
        return CRYPTO.verify(msg, sig, public)

    return sign, verify, keys


def pickle_hash(obj):
    return blake2b(pickle.dumps(obj, protocol=4)).digest()
