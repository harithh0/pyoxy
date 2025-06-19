import socket

HOST = "localhost"
# PORT = 8888
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
            host = url.split(":")[1].split("/")[2]  # 0, 1 -> are '/' '/'
            target_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            target_socket.connect((host, 80))
            proxy_http_request = f"{method} / HTTP/1.1 \r\nHost: {host}\r\n\r\n"  # \r\n (CRLF) is -> moving cursor to the beginning (\r) and starting new line (required by HTTP spec)
            # print(proxy_http_request)
            target_socket.sendall(proxy_http_request.encode())
            target_socket_response = target_socket.recv(4096)
            print(target_socket_response.decode())
            # print(host, method, url, protocol)
        print("user disconnected")
