import inspect
import time

import database
import interface
import networking


def main():
    database.init()
    networking.BASE_NODE.node.start()

    operations = {}


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

    operations['mine'] = interface.mine_top
    operations['?'] = get_help
    operations['help'] = get_help
    operations['exit'] = exit
    operations['height'] = interface.block_height
    operations['keypair'] = interface.keypair
    operations['loop'] = loop
    operations['balance'] = interface.balance
    operations['send'] = interface.transact
    operations['address'] = interface.public_key

    while True:
        user_input = input(">> ")
        function_name, *args = user_input.split(' ')
        value = None
        try:
            function = operations[function_name.lower()]
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
