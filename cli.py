import database
import interface


def main():
    database.init()
    public, private = interface.keypair()
    operations = {}

    def mine():
        interface.mine_top(public, private)

    def help():
        print(f"Possible operations are: {str(list(operations.keys()))[1:-1]}")

    operations['mine'] = mine
    operations['?'] = help
    operations['help'] = help

    while True:
        user_input = input(">> ")
        user_input = user_input.lower()
        try:
            operations[user_input]()
        except KeyError:
            help()


if __name__ == '__main__':
    main()
