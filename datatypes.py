import crypto
import database


def transaction(wallet_in: str, wallet_out: str, amount: int, index: int,
                private_key=None):
    transaction_dict = {'wallet_in': wallet_in, 'wallet_out': wallet_out,
                        'amount':    amount, 'index': index
                        }
    signer, verifier, _ = crypto.eddsa(wallet_in, private_key)

    def verify(signature: bytes):
        return verifier(crypto.pickle_hash(transaction_dict), signature)

    def sign():
        return signer(crypto.pickle_hash(transaction_dict))

    def store(signature: bytes):
        assert verify(signature)
        assert database.read('wallet', wallet_in) >= amount
        transaction_hash = crypto.pickle_hash(transaction_dict)
        assert database.read('transaction', transaction_hash) is None

        database.write(transaction_dict, 'transaction', transaction_hash)
        database.sub('wallet', wallet_in, amount)
        database.add('wallet', wallet_out, amount)

    return sign, verify, store
