import random
import threading
import time

import database
import interface
import utils
from config import P2P_PORT
from peerstack.peer import Peer


def init_node():
    running = [True]
    running_connections = []
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
    node.add_route_dict(request_to_function)

    listener = [threading.Thread(target=node.listen())]

    def add_connection(ip):
        if ip not in failed_connections and ip not in successful_connections:
            connection = Peer(ip, P2P_PORT)
            node.send(connection, 'ping', {})
            time.sleep(1)
            if 'ping' in mailbox:
                del mailbox['ping']
                database.append(ip, "peer", "white")
                successful_connections.append(ip)
                running_connections.append(connection)
            else:
                failed_connections.append(ip)

    def online(status):
        if listener and not status:
            del listener[0]
        elif not listener and status:
            listener[0] = threading.Thread(target=node.listen())

    def send(request_type, message, connection_id=False, requires_answer=False):
        if connection_id is None:
            for connection in running_connections:
                node.send(connection, request_type, message)
        elif connection_id is False:
            node.send(random.choice(running_connections), request_type, message)
        else:
            node.send(running_connections[connection_id], request_type, message)
        if not requires_answer:
            return
        while request_type not in mailbox:
            time.sleep(1e-2)
        return mailbox.pop(request_type)

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
            peer_list = self.send('read_peers', {}, None, True)
        for peer in peer_list:
            self.add_connection(peer)

    def request_block(self, block_index):
        return self.send('read_block', {'block_index': block_index},
                         False, True)

    def request_transaction(self, transaction_hash):
        return self.send('read_transaction', {'transaction_hash': transaction_hash
                                              }, False, True)

    def send_block(self, block_index, wallet, transactions, difficulty, block_previous,
                   timestamp, nonce, signature):
        self.send('add_block', {'block_index':    block_index,
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
        self.send('add_transaction', {'wallet_in':  wallet_in,
                                      'wallet_out': wallet_out,
                                      'amount':     amount,
                                      'index':      index,
                                      'signature':  signature
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
