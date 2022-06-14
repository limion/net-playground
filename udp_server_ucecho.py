import asyncio


class EchoServerProtocol:
    def __init__(self):
        self.transport = None

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        print(f"{data.decode()} from {addr}")
        self.transport.sendto(data.decode().upper().encode(), addr)


async def server(ip: str, port: int):
    loop = asyncio.get_running_loop()
    transport, protocol = await loop.create_datagram_endpoint(
        EchoServerProtocol,
        local_addr=(ip, port),
    )
    while True:
        await asyncio.sleep(0)


if __name__ == "__main__":
    import argparse
    import sys
    import socket

    parser = argparse.ArgumentParser()
    parser.add_argument("host")
    parser.add_argument("port")
    ns = parser.parse_args()
    args = ns.__dict__
    try:
        ip_addr = socket.gethostbyname(args["host"])
    except socket.gaierror:
        print("Unknown host: ", args["host"])
        sys.exit(1)
    asyncio.run(server(ip_addr, args["port"]))
