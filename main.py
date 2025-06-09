import socket

HOST = "localhost"
PORT = 8888
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

            conn.sendall(data)
        print("user disconnected")
