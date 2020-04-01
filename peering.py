import socket
import threading
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


socket.setdefaulttimeout(10)


class Peer:
    def __init__(self, ip, port, log_file='p2p.log'):
        self.ip = ip
        self.port = port
        self.routes = {'compare': self.compare_listener}
        self.iterator = {}
        self.log_file = open(log_file, 'a')
        self.connections = []

    def compare_listener(self, init_item, iterator_name, skip, **kwargs):
        connection_item = init_item
        iterator = self.iterator[iterator_name]()
        connection = self.connections.pop(-1)
        for _ in range(int(skip)):
            next(iterator)
        while True:
            try:
                item = next(iterator)
            except StopIteration:
                connection.sendall(0)
                break
            except RuntimeError:
                connection.sendall(0)
                break
            connection.sendall(utils.dumps(int(connection_item == item)))
            connection_item = receive_all(connection)
            if connection_item is None:
                break
        return None

    def compare(self, context, ip):
        target = context['target']
        iterator = context['iterator']
        iterator_name = context['iterator_name']
        skip = context['skip']
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.connect((ip, self.port))
                sock.sendall(utils.dumps({'request_type':  'compare',
                                          'init_item':     next(iterator),
                                          'iterator_name': iterator_name,
                                          'skip':          skip
                                          }))

                i = 0
                while receive_all(sock) != target:
                    try:
                        sock.sendall(utils.dumps(next(iterator)))
                    except RuntimeError:
                        break
                    except StopIteration:
                        break
                    i += 1
            except socket.timeout:
                return None
            except ConnectionError:
                return None
        return i

    def handle_request(self, host_ip, connection, active_connections):
        try:
            result = receive_all(connection)
            self.connections.append(connection)
            request_type = result.pop('request_type')
            result['ip'] = host_ip
            value = self.routes[request_type](**result)
            if value is not None:
                value = utils.dumps(value)
                connection.sendall(value)
            if active_connections is not None:
                active_connections.add(host_ip)
        except Exception as exc:
            import traceback
            traceback.print_exc()
            self.log_file.write(
                    ' '.join(['Exception of type', exc.__class__.__name__,
                              'occured at', str(int(time.time())),
                              '(unix timestamp) containing', str(exc),
                              'as data\n']))

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
                    threading.Thread(target=self.handle_request,
                                     args=(host_ip, connection, active_connections)
                                     ).start()
                except socket.timeout:
                    pass
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
