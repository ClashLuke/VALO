import socket
import time

import utils


def receive_all(connection, buffer_size=2 ** 10):
    result = []
    while True:
        try:
            data = connection.recv(buffer_size)
        except socket.timeout:
            break
        result.append(data)
        if len(data) < buffer_size:
            break
    result = b''.join(result)
    return utils.loads(result)


socket.setdefaulttimeout(1)


class Peer:
    def __init__(self, ip, port, log_file='p2p.log'):
        self.ip = ip
        self.port = port
        self.routes = {'compare': self.compare_listener}
        self.iterator = {}
        self.log_file = open(log_file, 'a')
        self.connection = None

    def compare_listener(self, init_item, iterator_name, skip, **kwargs):
        connection_item = init_item
        iterator = self.iterator[iterator_name]()
        for _ in range(skip):
            iterator()
        for item in iterator:
            self.connection.sendall(bytes(int(connection_item == item)))
            connection_item = receive_all(self.connection)
            if connection_item is None:
                break
        return None

    def compare(self, context, ip):
        target = context['target']
        iterator = context['iterator']
        iterator_name = context['iterator_name']
        skip = context['iterator_name']
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.connect((ip, self.port))
                sock.sendall(utils.dumps({'request_type':  'compare',
                                          'init_item':     next(iterator),
                                          'iterator_name': iterator_name,
                                          'skip':          skip
                                          }))

                if int.from_bytes(sock.recv(4), 'little') != target:
                    return 0
                for i, item in enumerate(1, iterator):
                    sock.sendall(item)
                    if int.from_bytes(sock.recv(4), 'little') != target:
                        break
            except socket.timeout:
                return None
            except ConnectionError:
                return None
        return i

    def listen(self, active_connections: set = None):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            while True:
                try:
                    sock.bind((self.ip, self.port))
                except OSError:
                    time.sleep(1)
                else:
                    break
            sock.listen()
            while True:
                try:
                    connection, (host_ip, _) = sock.accept()
                    result = receive_all(connection)
                    self.connection = connection
                    request_type = result.pop('request_type')
                    result['ip'] = host_ip
                    value = self.routes[request_type](**result)
                    if value is not None:
                        value = utils.dumps(value)
                        connection.sendall(value)
                    if active_connections is not None:
                        active_connections.add(host_ip)
                except Exception as exc:
                    self.log_file.write(
                            ' '.join(['Exception of type', exc.__class__.__name__,
                                      'occured at', str(int(time.time())),
                                      '(unix timestamp) containing', str(exc),
                                      'as data\n']))

    def send(self, message, ip):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.connect((ip, self.port))
                sock.sendall(utils.dumps(message))
                value = receive_all(sock)
            except socket.timeout:
                return None
            except ConnectionError:
                return None
            if isinstance(value, dict):
                value['ip'] = ip
            return value

    def register_routes(self, routes: dict):
        self.routes.update(routes)
