import jsonpickle
from redis import Redis

import config
import crypto

DATABASE = Redis()
CONNECTED_DATA_TYPES = ('wallet', 'block', 'transaction')


def get_key(data_type: str, key: str):
    return '+'.join([data_type, key])


def read(data_type: str, key: str):
    return_value = DATABASE.get(get_key(data_type, key))
    if return_value is None:
        return None
    return jsonpickle.loads(return_value)


def put(data_type: str, key: str, item):
    DATABASE.set(get_key(data_type, key), jsonpickle.dumps(item))


def append(item: dict, data_type: str, key: str):
    previous = read(data_type, key)
    item = [item]
    if previous is not None:
        item.extend(previous)
    put(data_type, key, item)


def put_connection(data_type, key, item_key, item_value):
    if isinstance(item_value, dict):
        value = crypto.pickle_hash(item_value).decode(errors='ignore')
        write(item_value, item_value.pop('data_type'), value)
        item_value = value
    put('+'.join(['connection', data_type, item_key]), key, item_value)
    put('+'.join(['connection', item_key, data_type]), item_value, key)


def write(item, data_type=None, key=None):
    if data_type is None:
        data_type = item.pop('data_type')
        key = item.pop('key')
    put(data_type, key, item)
    if isinstance(item, dict):
        for item_key, item_value in item.items():
            if item_key.startswith(CONNECTED_DATA_TYPES):
                if isinstance(item_value, list):
                    for value in item_value:
                        put_connection(data_type, key, item_key, value)
                else:
                    put_connection(data_type, key, item_key, item_value)


def add(data_type, key, amount):
    DATABASE.incr(get_key(data_type, key), int(amount))


def sub(data_type, key, amount):
    DATABASE.decr(get_key(data_type, key), int(amount))


def init():
    if read('block_size', 'mean') is None:
        write(0, 'block_size', 'mean')
        write(0, 'block_height', 'main')
        write(0, 'sent', 'transactions')
        write(config.SEEDS, 'peer', 'white')
    write([], 'transaction', 'cache')
    write([], 'transaction', 'mined')
