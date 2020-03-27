import pickle
from hashlib import sha256 as hash_function
from random import randint

from ecpy.curves import Curve
from ecpy.eddsa import ECPrivateKey, EDDSA


CRYPTO = EDDSA(hash_function)
CURVE = Curve.get_curve('Ed25519')


def eddsa(public=None, private=None):
    if public is None:
        private = ECPrivateKey(randint(0, 2 ** 256), CURVE)
        public = private.get_public_key()

    def sign(msg):
        return CRYPTO.sign(msg, private)

    def keys():
        return public, private

    def verify(msg, sig):
        return CRYPTO.verify(msg, sig, public)

    return sign, verify, keys


def pickle_hash(obj):
    return hash_function(pickle.dumps(obj, protocol=4)).digest()
