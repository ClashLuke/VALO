import pickle

from redis import Redis

DATABASE = Redis()
CONNECTED_DATA_TYPES = ('wallet', 'block', 'transaction')


def get_key(data_type: str, key: str):
    return '+'.join([data_type, key])


def read(data_type: str, key: str):
    return DATABASE.get(get_key(data_type, key))


def put(data_type: str, key: str, item):
    DATABASE.set(get_key(data_type, key), item)


def append(data_type: str, key: str, item: dict):
    previous = read(data_type, key)
    item = [item]
    if previous is not None:
        item.extend(previous)
    put(data_type, key, item)


def write(item, data_type=None, key=None):
    if data_type is None:
        data_type = item.pop('data_type')
        key = item.pop('key')
    put(data_type, key, item)
    if isinstance(item, dict):
        for item_key, item_value in item.items():
            if item_key.startswith(CONNECTED_DATA_TYPES):
                put('+'.join(['connection', data_type, item_key]), key, item_value)
                put('+'.join(['connection', item_key, data_type]), item_value, key)


def add(data_type, key, amount):
    DATABASE.incr(get_key(data_type, key), amount)


def sub(data_type, key, amount):
    DATABASE.decr(get_key(data_type, key), amount)
