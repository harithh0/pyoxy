import logging
import socket

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s:\n%(message)s",
)

HOST = "localhost"
# PORT = 8810
PORT = 8889
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.bind((HOST, PORT))
    s.listen()
    # while True:
    conn, add = s.accept()
    with conn:
        print(f"connected from {add}")
        while True:
            data = conn.recv(1024)
            if not data:  # if len of data sent is 0 -> means use disconnected
                break
            print("user sent: {}".format(data.decode()))

            method = data.decode().split()[0]
            url = data.decode().split()[1]
            protocol = url.split(":")[0]
            # host = url.split(":")[1].split("/")[2]  # 0, 1 -> are '/' '/'
            host = data.decode().split()[4]
            path = url.split(
                f"{host}"
            )[1]  # WARNING: change this, what if user has the host name inside path
            # print(path)
            target_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            target_socket.connect((host, 80))

            # NOTE:
            """
            \r\n (CRLF) is -> moving cursor to the beginning (\r) and starting new line (required by HTTP spec)
                - We can actually see the raw response if we do curl --trace (look at the .. in the response header and the hex that corresponds to it 0d and 0a)
                    these both translate to \r\n ~intresting
            """
            proxy_http_request = (
                f"{method} {path} HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\n\r\n"
            )
            # print(proxy_http_request)
            target_socket.sendall(proxy_http_request.encode())

            # updates by stream
            while True:
                chunk = target_socket.recv(4096)
                if not chunk:  # if empty (it will return False so, not false -> true and it will break)
                    break
                else:
                    conn.sendall(chunk)
                    print(chunk)

            # send recieved response back to client

            # print(host, method, url, protocol)
            s.shutdown(socket.SHUT_WR)  # sends FIN
        # print("user disconnected")
