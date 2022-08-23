from socket import SOCK_STREAM, socket


def handle_request(server_socket: socket):
    connection_socket, addr = server_socket.accept()
    data = connection_socket.recv(1024)
    text = data.decode()
    print(f"{text} from {addr}")
    connection_socket.send(text.upper().encode())
    connection_socket.close()


def server(host: str, port: int):
    server_socket = socket(type=SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(1)
    while True:
        handle_request(server_socket)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("host")
    parser.add_argument("port", type=int)
    ns = parser.parse_args()
    server(**ns.__dict__)
