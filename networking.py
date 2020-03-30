import atexit
import random
import threading
import time

import config
import database
import interface
import utils
from config import P2P_PORT
from peering import Peer


def init_node():
    successful_connections = set()
    failed_connections = set()
    mailbox = {}
    request_to_function = {'read_peers':       interface.active_peers,
                           'read_block':       interface.read_block,
                           'read_transaction': interface.read_transaction,
                           'read_height':      interface.block_height,
                           'add_transaction':  interface.store_unverified_transaction,
                           'ping':             utils.ping,
                           'reply':            interface.mailbox_handler(mailbox)
                           }

    request_to_function = {key: utils.networking_wrapper(function) for key, function in
                           request_to_function.items()}
    iterators = {'reverse_hashes': interface.reverse_hashes}

    request_to_function['add_block'] = interface.store_block
    node = Peer("0.0.0.0", P2P_PORT)
    node.routes.update(request_to_function)
    node.iterator.update(iterators)

    listener = [threading.Thread(target=node.listen, daemon=True,
                                 args=(successful_connections,))]
    listener[0].start()

    @atexit.register
    def cleanup():
        database.put('peer', 'white', list(successful_connections))

    def add_connection(ip):
        if ip not in failed_connections and ip not in successful_connections:
            response = node.send({'request_type': 'ping'}, ip)
            if response:
                successful_connections.add(ip)
            else:
                failed_connections.add(ip)

    def online(status):
        if listener and not status:
            del listener[0]
        elif not listener and status:
            listener[0] = threading.Thread(target=node.listen, daemon=True,
                                           args=(successful_connections,))
            listener[0].start()

    def send(message, connection_ip=False, function_name='send'):
        function = getattr(node, function_name)
        if connection_ip is None:
            return {connection: function(message, connection) for connection in
                    successful_connections}
        if connection_ip is False:
            return function(message, random.sample(successful_connections, 1)[0])
        return function(message, connection_ip)

    any(add_connection(peer) for peer in interface.active_peers())

    return online, add_connection, send


class Node:
    def __init__(self):
        self.online, self.add_connection, self.send = init_node()
        self.syncing = True
        self.start()
        self.sync_thread = None

    def start(self):
        self.online(True)
        self.syncing = True
        self.sync_thread = threading.Thread(target=self.sync_loop, daemon=True)
        self.sync_thread.start()

    def stop(self):
        self.online(False)
        self.syncing = False

    def single_sync(self):
        self.add_peers()
        heights = self.send({'request_type': 'read_height'}, None)
        if not heights:
            print("Unable to connect to nodes. Skipping synchronization.")
            return
        ip = max(heights, key=heights.get)
        any(interface.store_block(
                **self.send({'request_type': 'read_block', 'block_index': i},
                            ip)) is False for i in
            range(interface.block_height(), heights[ip]))

    def sync_loop(self):
        while self.syncing:
            self.single_sync()
            time.sleep(config.SYNC_INTERVAL)

    def add_peers(self, peers: list = None):
        if peers is None:
            peer_list_list = self.send({'request_type': 'read_peers'}, None)
            peers = set()
            for peer_list in peer_list_list:
                if isinstance(peer_list, list):
                    peers.update(peer_list)
                elif isinstance(peer_list, str):
                    peers.add(peer_list)
        for peer in peers:
            self.add_connection(peer)

    def request_block(self, block_index, ip=False):
        return self.send({'request_type': 'read_block', 'block_index': block_index},
                         ip)

    def request_transaction(self, transaction_hash):
        return self.send({'request_type':     'read_transaction',
                          'transaction_hash': transaction_hash
                          }, False)

    def send_block(self, wallet, transactions, timestamp, nonce, signature, **kwargs):
        self.send({'request_type': 'add_block',
                   'wallet':       wallet,
                   'transactions': transactions,
                   'timestamp':    timestamp,
                   'nonce':        nonce,
                   'signature':    signature
                   }, None)

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
                   }, None)

    def get_split(self, ip):
        return self.send({'target':        1,
                          'iterator':      interface.reverse_hashes(),
                          'iterator_name': 'reverse_hashes'
                          }, ip, 'compare')

    def request_height(self, ip=False):
        return self.send({'request_type': 'read_height'}, ip)


class BaseNode:
    def __init__(self):
        self._node = None

    def node(self):
        if self._node is None:
            self._node = Node()
        return self._node


BASE_NODE = BaseNode()
