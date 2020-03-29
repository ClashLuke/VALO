import socket
import time

import jsonpickle


def receive_all(connection, buffer_size=2 ** 10):
    result = []
    while True:
        data = connection.recv(buffer_size)
        result.append(data)
        if len(data) < buffer_size:
            break
    result = b''.join(result).decode()
    return jsonpickle.loads(result)


class Peer:
    def __init__(self, ip, port, log_file='p2p.log'):
        self.ip = ip
        self.port = port
        self.routes = {}
        self.known_ips = set()
        self.log_file = open(log_file, 'a')

    def listen(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind((self.ip, self.port))
            sock.listen()
            while True:
                try:
                    connection, (host_ip, _) = sock.accept()
                    self.known_ips.add(host_ip)
                    result = receive_all(connection)
                    request_type = result.pop('request_type')
                    value = self.routes[request_type](**result)
                    value = jsonpickle.dumps(value).encode()
                    connection.sendall(value)
                except Exception as exc:
                    self.log_file.write(
                            ' '.join(['Exception of type', exc.__class__.__name__,
                                      'occured at', str(int(time.time())),
                                      '(unix timestamp) containing', str(exc),
                                      'as data\n']))

    def send(self, message, ip):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((ip, self.port))
            sock.sendall(jsonpickle.dumps(message).encode())
            return receive_all(sock)

    def register_routes(self, routes: dict):
        self.routes.update(routes)
