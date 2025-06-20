import ipaddress
import logging
import socket
import subprocess
import threading
import urllib.parse
from time import sleep

# Logger for console only
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s:\n%(message)s",
)

# Logger for file only
file_logger = logging.getLogger("file_logger")
file_logger.setLevel(logging.INFO)
file_handler = logging.FileHandler("requests.log")
file_handler.setLevel(logging.INFO)
file_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
file_handler.setFormatter(file_formatter)
file_logger.addHandler(file_handler)
file_logger.propagate = False


class ProxyServer:

    def __init__(self, host="127.0.0.1", port=2222):
        self.host = host
        self.port = port
        self.ipv = (socket.AF_INET
                    if isinstance(ipaddress.ip_address(host),
                                  ipaddress.IPv4Address) else socket.AF_INET6)
        self.server_socket = socket.socket(self.ipv, socket.SOCK_STREAM)
        self.server_socket.bind((host, port))
        self.server_socket.listen()

    def start(self):
        while True:
            conn, addr = self.server_socket.accept()
            self.ip_format = self.get_ip_format(addr[0])
            if self.ip_format is not None:
                threading.Thread(target=self.handle_client,
                                 args=(conn, )).start()
            else:
                self.send_error_response(conn, 500,
                                         "Error resolving IP address format")
                conn.close()

    def get_ip_format(self, ip_address):
        ip_obj = ipaddress.ip_address(ip_address)
        if isinstance(ip_obj, ipaddress.IPv4Address):
            return socket.AF_INET
        elif isinstance(ip_obj, ipaddress.IPv6Address):
            return socket.AF_INET6
        else:
            return None

    def handle_https(self, data, client_connection):
        print("https request")
        decoded_split_data = data.decode().split()
        host = decoded_split_data[4].split(":")[0]

        file_logger.info(f"HTTPS {client_connection.getpeername()} -> {host}")

        # NOTE: https proxy http request will send CONNECT request, we must respond with 'Connection Established' message | CONNECT tells the proxy: “Open a tunnel”
        try:
            target_socket = socket.socket(self.ip_format, socket.SOCK_STREAM)
            target_socket.connect((host, 443))
            # target_socket = socket.create_connection((host, 443))
            client_connection.sendall(
                b"HTTP/1.1 200 Connection Established\r\n\r\n")
            # At this point, the client starts a TLS handshake over the now-open tunnel.
            # now the client is ready to send data to target
            # the proxy will just relay the encrypted bytes between the two connections
        except Exception as e:
            # checks if the exception is of type socket.gaierror instead of comparing instance to class with ==
            if isinstance(e, socket.gaierror):
                result = subprocess.run(
                    ["ping", "-c", "1", "1.1.1.1"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                # means we have internet access but not resolving target
                if result.returncode == 0:
                    self.send_error_response(
                        client_connection,
                        500,
                        "Proxy can't connect to server: Likely target server does not support IPV6",
                    )

                # no internet access (by not being able to ping 1.1.1.1)
                else:
                    self.send_error_response(
                        client_connection,
                        500,
                        "Proxy server internet connection to target failed",
                    )
            else:
                self.send_error_response(client_connection, 502, "Bad Gateway")
            client_connection.close()
            return

        # no need to edit headers, strip out Proxy-Connectionn etc..
        self.tunnel(client_connection, target_socket)

    # bidirectional data forwarding
    def tunnel(self, source, dest):
        # starts sending and recieving encrypted data between client and target
        def forward(src, dst):
            try:
                while True:
                    data = src.recv(4096)
                    if not data:
                        break
                    dst.sendall(data)
            except Exception:
                # TODO: should log errors
                pass
            finally:
                """
                if using this:
                # src.close()
                # dst.close()
                Then if we close the socket in one direction (Thread-A), the other direction (Thread-B) may still be actively transferring data — so closing the socket
                there breaks the tunnel prematurely. So instead we just 
                """
                # Avoid prematurely closing the entire tunnel
                try:
                    src.shutdown(
                        socket.SHUT_RD
                    )  # SHUT_RD tells the OS we're done reading (no more recv())
                except Exception:
                    pass
                try:
                    dst.shutdown(
                        socket.SHUT_WR
                    )  # SHUT_WR tells the OS we're done writing (sends FIN to the remote peer)
                except Exception:
                    pass

        """
        - recieves data from src and sends to dest unitl everything is recieved, then it will recv from dest and send it to src until everything is recieved
        - This creates a full-duplex TCP channel, as 
        """
        # client → proxy → server
        threading.Thread(target=forward, args=(source, dest)).start()
        # server → proxy → client
        threading.Thread(target=forward, args=(dest, source)).start()

    def send_error_response(self,
                            client_connection,
                            status_code=500,
                            message="Internal Server Error"):
        body = f"{status_code} {message}\n"
        response = (f"HTTP/1.1 {status_code} {message}\r\n"
                    "Content-Type: text/plain\r\n"
                    f"Content-Length: {len(body)}\r\n"
                    "Connection: close\r\n"
                    "\r\n"
                    f"{body}")
        client_connection.sendall(response.encode())
        client_connection.close()

    def handle_http(self, data, client_connection):
        other_headers = data.split(b"\r\n")[2:]  # only gets the other headers

        # .split(CRLF) will seperate them by the CRLF and keep the last 2 empty, so when we do '+ \r\n', it will add to the last 2 as well hence why we dont need an extra '+ \r\n' at the end of the final
        # we are adding them to the end of each header including the last header per HTTP protocol
        # it will be like this when we split it: [..., ..., b'', b''] (the end CRLF's)
        # also removing Proxy-Connection header (we will set that as Connection: close header to make it more simple for now)
        other_headers_formated = "".join([
            header_line.decode() + "\r\n" for header_line in other_headers
            if "Proxy-Connection:" not in header_line.decode()
        ])
        # remove the extra CRLF
        other_headers_formated = other_headers_formated[:len(
            other_headers_formated) - 2]

        # logging.debug(other_headers_formated)

        method = data.decode().split()[0]
        url = data.decode().split()[1]
        url_data = urllib.parse.urlparse(url)
        host = url_data.netloc
        path = url_data.path
        target_socket = socket.socket(self.ip_format, socket.SOCK_STREAM)
        file_logger.info(f"HTTP {client_connection.getpeername()} -> {host}")
        try:
            target_socket.connect((host, 80))
        except socket.gaierror:
            self.send_error_response(
                client_connection,
                500,
                "Proxy server internet connection to target failed",
            )
            return
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

        # logging.debug(proxy_http_request)

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
        # TODO: Add chunking here to avoid missing extra data
        data = client_connection.recv(4096)
        if not data:  # if len of data sent is 0 -> means use disconnected
            return
        # TODO: first check if its valid HTTP request

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
