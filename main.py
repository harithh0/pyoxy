import logging
import socket
import threading
from time import sleep

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s:\n%(message)s",
)


class ProxyServer:

    def __init__(self, host="0.0.0.0", port=2222):
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((host, port))
        self.server_socket.listen()

    def start(self):
        while True:
            conn, add = self.server_socket.accept()
            print(f"connected from {add}")
            threading.Thread(target=self.handle_client, args=(conn, )).start()

    def handle_https(self, data, client_connection):
        print("https request")
        decoded_split_data = data.decode().split()
        host = decoded_split_data[4].split(":")[0]

        try:
            target_socket = socket.create_connection((host, 443))
            client_connection.sendall(
                b"HTTP/1.1 200 Connection Established\r\n\r\n")
        except Exception as e:
            client_connection.sendall(b"HTTP/1.1 502 Bad Gateway\r\n\r\n")
            client_connection.close()
            return

        self.tunnel(client_connection, target_socket)

        # NOTE: https proxy http request will send CONNECT request, we must respond with 'Connection Established' message | CONNECT tells the proxy: “Open a tunnel”

    def tunnel(self, source, dest):
        print(source.recv(4096).decode())
        # def forward(src, dst):
        #     try:
        #         while True:
        #             data = src.recv(4096)
        #
        #             if not data:
        #                 break
        #             dst.sendall(data)
        #     except Exception:
        #         pass
        #     finally:
        #         src.close()
        #         dst.close()
        #
        # threading.Thread(target=forward, args=(source, dest)).start()
        # threading.Thread(target=forward, args=(dest, source)).start()

    def handle_http(self, data, client_connection):
        other_headers = data.split(b"\r\n")[2:]  # only gets the other headers
        logging.debug(other_headers)

        # "".join insures that previous CRLF's are removed and that we are adding them to the end of each header including the last header per HTTP protocl
        # also removing Proxy-Connection header (we will set that as Connection: close header to make it more simple for now)
        other_headers_formated = "".join([
            header_line.decode() + "\r\n" for header_line in other_headers
            if "Proxy-Connection:" not in header_line.decode()
        ])
        logging.debug(other_headers_formated)
        method = data.decode().split()[0]
        print(data.decode().split())
        url = data.decode().split()[1]
        print("url", url)
        protocol = url.split(":")[0]
        print("protocol", protocol)
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

        # application layer data here, since the data passed gives those bytes structure, rules, and purpose
        # "A protocol becomes Layer 7 (TCP/IP Layer 5) when your app understands it as structured communication between two endpoints"

        # first line must change from proxy request to http server request and then we add the other headers that where sent from proxy
        proxy_http_request = f"{method} {path} HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\n{other_headers_formated}"
        print("here")
        print(proxy_http_request)
        # for all other headers, etc.. copy them from curl request
        target_socket.sendall(proxy_http_request.encode())

        # updates by stream
        while True:
            chunk = target_socket.recv(4096)
            if not chunk:  # if empty (it will return False so, not false -> true and it will break)
                break
            else:
                # send recieved chunk back to client
                client_connection.sendall(chunk)

        # logging.debug(host, method, url, protocol)

        # pretty sure when using curl it will automatically end the connection after recieving what it needs
        # closes connection (FIN, ACK, etc) -- since using Connection: close header we will be closing the connection without waiting for more reponses from client
        client_connection.close()
        return

    def handle_client(self, client_connection):
        data = client_connection.recv(1024)
        if not data:  # if len of data sent is 0 -> means use disconnected
            return
        print("user sent: {}".format(data.decode()))
        # TODO: first check if its valid HTTP request

        # sleep(1000)
        decoded_split_data = data.decode().split()
        if decoded_split_data[0] == "CONNECT" and decoded_split_data[1][
                -3:] == "443":
            # https
            # response = b"HTTP/1.1 403 Forbidden\r\nConnection: close\r\n\r\n"
            # client_connection.sendall(response)

            # client_connection.close()
            self.handle_https(data, client_connection)
        else:
            self.handle_http(data, client_connection)


if __name__ == "__main__":
    http_proxy = ProxyServer()
    http_proxy.start()
