import threading

import pyp2p.net as net

import interface
from config import P2P_PORT

REQUEST_TO_FUNCTION = {'read_block':       interface.read_block,
                       'read_transaction': interface.read_transaction,
                       'add_transaction':  interface.store_transaction,
                       'add_block':        interface.store_block
                       }


def init_node():
    running = True

    def start_node(port):
        node = net.Net(passive_port=port, node_type='passive')
        node.start()
        node.bootstrap()
        node.advertise()
        return node

    passive_node = start_node(P2P_PORT)
    active_node = start_node(P2P_PORT + 1)

    def handler():
        while running:
            for connection in passive_node:
                for reply in connection:
                    try:
                        function = REQUEST_TO_FUNCTION.get(reply.pop('request_type'))
                        function(**reply)
                    except Exception as exc:
                        print(f'{exc.__class__.__name__} occured with message "{exc}"')
                        continue

    thread = threading.Thread(target=handler)
    thread.start()
