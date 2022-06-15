from socketserver import ThreadingUDPServer, BaseRequestHandler
import threading


class ThreadedUDPRequestHandler(BaseRequestHandler):
    def handle(self):
        data = self.request[0].strip()
        socket = self.request[1]
        text = str(data, "ascii")
        cur_thread = threading.current_thread()
        print(f"{text} from {self.client_address}, thread {cur_thread.name}")
        socket.sendto(text.upper().encode(), self.client_address)


def server(host: str, port: int):
    serv = ThreadingUDPServer((host, port), ThreadedUDPRequestHandler)
    serv.serve_forever()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("host")
    parser.add_argument("port", type=int)
    ns = parser.parse_args()
    server(**ns.__dict__)
