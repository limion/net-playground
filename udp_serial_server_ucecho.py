from socket import socket, SOCK_DGRAM


def handle_request(server_socket: socket):
    data, addr = server_socket.recvfrom(1024)
    text = data.decode()
    print(f"{text} from {addr}")
    server_socket.sendto(text.upper().encode(), addr)


def server(host: str, port: int):
    server_socket = socket(type=SOCK_DGRAM)
    server_socket.bind((host, port))
    while True:
        handle_request(server_socket)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("host")
    parser.add_argument("port", type=int)
    ns = parser.parse_args()
    server(**ns.__dict__)
