import inspect
import time

import config
import database
import interface


def main():
    database.init()
    public, private = interface.keypair()
    operations = {}

    def mine():
        interface.mine_top(public, private)

    def get_help():
        operations_string = str(list(operations.keys()))[1:-1].replace("'", "")
        return f"Possible operations are: {operations_string}"

    def loop(function_name, pause):
        function = operations[function_name]
        pause = float(pause)
        while True:
            value = function()
            if value is not None:
                print(value)
            time.sleep(pause)

    def balance(address=public):
        return database.read('wallet', address) / config.UNIT

    operations['mine'] = mine
    operations['?'] = get_help
    operations['help'] = get_help
    operations['exit'] = exit
    operations['height'] = interface.block_height
    operations['keypair'] = interface.keypair
    operations['loop'] = loop
    operations['balance'] = balance

    while True:
        user_input = input(">> ")
        function_name, *args = user_input.lower().split(' ')
        value = None
        try:
            function = operations[function_name]
        except KeyError:
            function = get_help
        try:
            value = function(*args)
        except TypeError:
            print(f"{function_name} expected "
                  f"{len(inspect.signature(function).parameters)} arguments. Got "
                  f"{len(args)}.")
        if value is not None:
            print(value)


if __name__ == '__main__':
    main()
