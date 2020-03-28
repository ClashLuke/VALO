import pickle

from nacl import encoding, signing
from nacl.hashlib import blake2b as hash_function


def eddsa(public=None, private=None):
    if public is None:
        private = signing.SigningKey.generate()
        public = private.verify_key
    elif not isinstance(public, signing.VerifyKey):
        public = signing.VerifyKey(public.encode(), encoder=encoding.Base32Encoder)

    def sign(msg):
        sig = private.sign(msg).signature
        return sig

    def keys():
        return public.encode(encoder=encoding.Base32Encoder).decode(), private

    def verify(msg, sig):
        return public.verify(msg, sig)

    return sign, verify, keys


def pickle_hash(obj):
    return hash_function(pickle.dumps(obj)).digest()
