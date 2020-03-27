import random
import threading
import time

import pyp2p.net as net

import interface
from config import P2P_PORT


def init_node():
    running = [True]
    running_connections = []
    successful_connections = []
    failed_connections = []
    mailbox = []
    request_to_function = {'read_block':       interface.read_block,
                           'read_transaction': interface.read_transaction,
                           'add_transaction':  interface.store_unverified_transaction,
                           'add_block':        interface.store_block,
                           'reply':            interface.mailbox_handler(mailbox)
                           }

    def start_node(port):
        node = net.Net(passive_port=port, node_type='passive')
        node.start()
        node.bootstrap()
        node.advertise()
        return node

    passive_node = start_node(P2P_PORT)
    active_node = start_node(P2P_PORT + 1)

    def handler():
        while running[0]:
            for connection in passive_node:
                for reply in connection:
                    try:
                        function = request_to_function.get(reply.pop('request_type'))
                        answer = function(**reply)
                        if answer is not False:
                            connection.send({'request_type': 'reply', 'data': answer})
                    except Exception as exc:
                        print(f'{exc.__class__.__name__} occured with message "{exc}"')
                        continue

    thread = threading.Thread(target=handler)
    thread.start()

    def add_connection(ip):
        if ip not in failed_connections and ip not in successful_connections:
            connection = active_node.add_node(ip, P2P_PORT, "passive")
            if connection is None:
                failed_connections.append(ip)
            else:
                successful_connections.append(ip)
                running_connections.append(connection)

    def online(status):
        running[0] = status

    def send(message, connection_id=False, requires_answer=False):
        if connection_id is None:
            for connection in running_connections:
                connection.send(message)
        elif connection_id is False:
            random.choice(running_connections).send(message)
        else:
            running_connections[connection_id].send(message)
        if not requires_answer:
            return
        while not mailbox:
            time.sleep(1e-2)
        return mailbox.pop(0)

    return online, add_connection, send


class Node:
    def __init__(self):
        self.online, self.add_connection, self.send = init_node()

    def start(self):
        self.online(True)

    def stop(self):
        self.online(False)

    def add_peers(self, peer_list):
        for peer in peer_list:
            self.add_connection(peer)

    def request_block(self, block_index):
        return self.send({'request_type': 'read_block', 'block_index': block_index},
                         False, True)

    def request_transaction(self, transaction_hash):
        return self.send({'request_type':     'read_transaction',
                          'transaction_hash': transaction_hash
                          }, False, True)

    def send_block(self, block_index, wallet, transactions, difficulty, block_previous,
                   timestamp, nonce, signature):
        self.send({'request_type':   'add_block',
                   'block_index':    block_index,
                   'wallet':         wallet,
                   'transactions':   transactions,
                   'difficulty':     difficulty,
                   'block_previous': block_previous,
                   'timestamp':      timestamp,
                   'nonce':          nonce,
                   'signature':      signature
                   }, True, False)

    def send_transaction(self, wallet_in, wallet_out, amount, index, signature):
        self.send({'request_type': 'add_transaction',
                   'wallet_in':    wallet_in,
                   'wallet_out':   wallet_out,
                   'amount':       amount,
                   'index':        index,
                   'signature':    signature
                   }, True, False)


class BaseNode:
    def __init__(self):
        self._node = None

    @property
    def node(self):
        if self._node is None:
            self._node = Node()
        return self._node


BASE_NODE = BaseNode()
