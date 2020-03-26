import threading

import pyp2p.net as net

import interface
from config import P2P_PORT

REQUEST_TO_FUNCTION = {'read_block':       interface.read_block,
                       'read_transaction': interface.read_transaction,
                       'add_transaction':  interface.store_transaction,
                       'add_block':        interface.store_block,
                       'reply':            None
                       }


def init_node():
    running = [True]
    running_connections = []
    successful_connections = []
    failed_connections = []
    mailbox = []

    request_to_function = REQUEST_TO_FUNCTION.copy()
    request_to_function['reply'] = interface.mailbox_handler(mailbox)

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
                        function = REQUEST_TO_FUNCTION.get(reply.pop('request_type'))
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

    def send(message, connection_id=None, requires_answer=False):
        if connection_id is None:
            for connection in running_connections:
                connection.send(message)
        else:
            running_connections[connection_id].send(message)
        if not requires_answer:
            return
        while not mailbox:
            time.sleep(1e-2)
        return mailbox.pop(0)

    return online, add_connection, send


def interface():
    online, add_connection, send = init_node()

    def start():
        online(True)

    def stop():
        online(False)

    def add_peers(peer_list):
        for peer in peer_list:
            add_connection(peer)
