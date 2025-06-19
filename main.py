import logging
import socket
import threading

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s:\n%(message)s",
)

HOST = "localhost"
# PORT = 8810
PORT = 8889


class ProxyServer:

    def __init__(self, host="localhost", port=8888):
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((HOST, PORT))
        self.server_socket.listen()

    def start(self):
        while True:
            conn, add = self.server_socket.accept()
            print(f"connected from {add}")
            threading.Thread(target=self.handle_client, args=(conn, )).start()

    def handle_client(self, client_connection):
        data = client_connection.recv(1024)
        if not data:  # if len of data sent is 0 -> means use disconnected
            return
        print("user sent: {}".format(data.decode()))

        method = data.decode().split()[0]
        url = data.decode().split()[1]
        protocol = url.split(":")[0]
        host = data.decode().split()[4]
        path = url.split(
            f"{host}"
        )[1]  # WARNING: change this, what if user has the host name inside path
        target_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            target_socket.connect((host, 80))
        except socket.gaierror:
            print(
                "Proxy Server Network connection down, can't connect to target"
            )
            exit(-1)
        # NOTE:
        """
            \r\n (CRLF) is -> moving cursor to the beginning (\r) and starting new line (required by HTTP spec)
                - We can actually see the raw response if we do curl --trace (look at the .. in the response header and the hex that corresponds to it 0d and 0a)
                    these both translate to \r\n ~intresting
            """
        proxy_http_request = f"{method} {path} HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\n\r\n"  # first line must change from proxy request to http server request

        # for all other headers, etc.. copy them from curl request
        target_socket.sendall(proxy_http_request.encode())

        # updates by stream
        while True:
            chunk = target_socket.recv(4096)
            if not chunk:  # if empty (it will return False so, not false -> true and it will break)
                break
            else:
                client_connection.sendall(chunk)
                print(chunk.decode())

        # send recieved response back to client

        # logging.debug(host, method, url, protocol)
        self.server_socket.shutdown(socket.SHUT_WR)  # sends FIN


if __name__ == "__main__":
    http_proxy = ProxyServer()
    http_proxy.start()
