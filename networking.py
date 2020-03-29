import random
import threading

import database
import interface
import utils
from config import P2P_PORT
from peering import Peer


def init_node():
    successful_connections = []
    failed_connections = []
    mailbox = {}
    request_to_function = {'read_peers':       interface.active_peers,
                           'read_block':       interface.read_block,
                           'read_transaction': interface.read_transaction,
                           'add_transaction':  interface.store_unverified_transaction,
                           'add_block':        interface.store_block,
                           'ping':             utils.ping
                           }
    request_to_function = {key: utils.reply_wrapper(function) for key, function in
                           request_to_function.items()}
    request_to_function['reply'] = interface.mailbox_handler(mailbox)

    node = Peer("0.0.0.0", P2P_PORT)
    node.register_routes(request_to_function)

    listener = [threading.Thread(target=node.listen)]
    listener[0].start()

    def add_connection(ip):
        if ip not in failed_connections and ip not in successful_connections:
            response = node.send({'request_type': 'ping'}, ip)
            if response:
                del mailbox['ping']
                database.append(ip, "peer", "white")
                successful_connections.append(ip)
            else:
                failed_connections.append(ip)

    def online(status):
        if listener and not status:
            del listener[0]
        elif not listener and status:
            listener[0] = threading.Thread(target=node.listen)
            listener[0].start()

    def send(message, connection_id=False):
        if connection_id is None:
            for connection in successful_connections:
                node.send(message, connection)
            return None
        if connection_id is False:
            return node.send(message, random.choice(successful_connections))
        return node.send(message, successful_connections[connection_id])

    any(add_connection(peer) for peer in interface.active_peers())

    return online, add_connection, send


class Node:
    def __init__(self):
        self.online, self.add_connection, self.send = init_node()

    def start(self):
        self.online(True)

    def stop(self):
        self.online(False)

    def add_peers(self, peer_list: list = None):
        if peer_list is None:
            peer_list = self.send({'request_type': 'read_peers'}, None, True)
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
        print(block_index)
        self.send({'request_type':   'add_block',
                   'block_index':    block_index,
                   'wallet':         wallet,
                   'transactions':   transactions,
                   'difficulty':     difficulty,
                   'block_previous': block_previous,
                   'timestamp':      timestamp,
                   'nonce':          nonce,
                   'signature':      signature
                   }, None, False)

        def send_transaction(self, wallet_in, wallet_out, amount, index, signature,
                             data_type=None):  # skipcq
            """
            :param wallet_in: public address funds come from
            :param wallet_out: public address funds go to
            :param amount: amount of funds (in atomic units) to be sent
            :param index: unique index of transaction for user
            :param signature: signature of transaction hash
            :param data_type: Supressed keywordargument
            :return: None
            """
            self.send({'request_type': 'add_transaction',
                       'wallet_in':    wallet_in,
                       'wallet_out':   wallet_out,
                       'amount':       amount,
                       'index':        index,
                       'signature':    signature
                       }, None, False)

    class BaseNode:
        def __init__(self):
            self._node = None

        @property
        def node(self):
            if self._node is None:
                self._node = Node()
            return self._node

    BASE_NODE = BaseNode()
