import socket
import asyncio
import time
import random


def uppercased_echo_successful(request_message, response_message):
    return request_message.decode().upper().encode() == response_message


class EchoClientProtocol:
    def __init__(self, message, on_con_lost):
        self.message = message
        self.on_con_lost = on_con_lost
        self.transport = None
        self.result = None

    def connection_made(self, transport):
        self.transport = transport
        self.transport.sendto(self.message)

    def datagram_received(self, data, attr):
        self.result = uppercased_echo_successful(self.message, data)
        self.transport.close()

    def error_received(self, exc):
        """Let's not rely on this method because UDP is unreliable by definition.
        To be able to close the socket let's use wait_for(on_con_lost) with timeout"""
        self.result = exc
        self.transport.close()

    def connection_lost(self, exc):
        if not self.on_con_lost.cancelled():
            self.on_con_lost.set_result(True)


async def echo_client(message, addr, timeout):
    loop = asyncio.get_running_loop()
    on_con_lost = loop.create_future()
    transport, protocol = await loop.create_datagram_endpoint(
        lambda: EchoClientProtocol(message, on_con_lost),
        remote_addr=addr,
    )
    try:
        await asyncio.wait_for(on_con_lost, timeout)
    except asyncio.TimeoutError:
        protocol.result = "Timeout"
    finally:
        transport.close()
    return protocol.result


async def put_task_in_queue(payload, q: asyncio.Queue):
    await q.put(payload)


async def fill_queue(iterable, q: asyncio.Queue):
    for item in iterable:
        await put_task_in_queue(item, q)


async def consume_task_from_queue(q, addr, timeout, verbose, result_tuple):
    while True:
        payload = await q.get()
        time_start = time.perf_counter()
        result = await echo_client(payload.encode(), addr, timeout)
        time_finish = time.perf_counter()
        (success, fail, error) = result_tuple
        match result:
            case True:
                success.append(time_finish - time_start)
            case False:
                fail.append(time_finish - time_start)
            case exc:
                error.append(time_finish - time_start)
                if verbose:
                    print(exc)

        q.task_done()  # required by q.join() to unblock


def consume_queue(q, addr, consumers, timeout, verbose, result_tuple):
    return [
        asyncio.create_task(
            consume_task_from_queue(q, addr, timeout, verbose, result_tuple)
        )
        for i in range(consumers)
    ]


def random_string():
    alphabet = "qwertyuiopasdfghjklzxcvbnm"
    alphabetlen = len(alphabet)
    strlen = random.randint(10, 80)
    string = ""
    while len(string) < strlen:
        letter_idx = random.randint(0, alphabetlen - 1)
        string += alphabet[letter_idx]
    return string


def tasks_generator(tasks_number):
    for i in range(tasks_number):
        yield f"{i} - {random_string()}"


async def main(
    result_tuple,
    ip: str,
    port: int,
    requests: int,
    concurrency: int,
    timeout: int,
    verbose: bool,
):
    q = asyncio.Queue(concurrency)
    messages = tasks_generator(requests)
    fill_queue_task = asyncio.create_task(fill_queue(messages, q))
    consumers = consume_queue(
        q,
        (ip, port),
        concurrency,
        timeout,
        verbose,
        result_tuple,
    )
    await fill_queue_task
    # Prevent main() from finish until all tasks are done
    await q.join()
    # cancel consumers task (break infinite "while True")
    for consumer in consumers:
        consumer.cancel()


if __name__ == "__main__":
    import argparse
    import sys

    random.seed(444)
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-r",
        "--total_requests",
        dest="nreq",
        type=int,
        default=1000,
        help="total number of echo requests to be made",
    )
    parser.add_argument(
        "-c",
        "--concurrent_requests",
        dest="ncon",
        type=int,
        default=10,
        help="number of concurrent requests",
    )
    parser.add_argument(
        "-t",
        "--timeout",
        dest="tmt",
        type=float,
        default=1,
        help="client timeout in seconds",
    )
    parser.add_argument(
        "-v",
        action="store_true",
        dest="verbose",
        help="show errors",
    )
    parser.add_argument("host")
    parser.add_argument("port")
    ns = parser.parse_args()
    args = ns.__dict__
    try:
        ip_addr = socket.gethostbyname(args["host"])
    except socket.gaierror:
        print("Unknown host: ", args["host"])
        sys.exit(1)

    params = {
        "requests": args["nreq"] if args["nreq"] > 0 else 1000,
        # concurrency is limited by the number of sockets available for the process. See "ulimit -n"
        "concurrency": args["ncon"]
        if args["ncon"] > 0 and args["ncon"] <= 250
        else 100,
        "timeout": args["tmt"] if args["tmt"] > 0 else 1,
        "verbose": args["verbose"],
        "ip": ip_addr,
        "port": args["port"],
    }
    results = ([], [], [])
    print(
        f"""Host: {args["host"]}({ip_addr})
Requests: {params['requests']}
Concurrency: {params['concurrency']}
Timeout: {params['timeout']} sec"""
    )
    start_time = time.perf_counter()
    asyncio.run(main(results, **params))
    duration = time.perf_counter() - start_time
    (success, fail, error) = results
    print(f"\nDone in {duration} seconds")
    print(f"Performance: {(len(success) + len(fail) + len(error)) / duration} req/sec")
    print("Successful responses: ", len(success))
    print("Failed responses: ", len(fail))
    print("Responses with error: ", len(error))
    if len(success) > 0:
        print(f"Average successful response time: {sum(success)/len(success)} seconds")
    if len(fail) > 0:
        print(f"Average failed response time: {sum(fail)/len(fail)} seconds")
    if len(error) > 0:
        print(f"Average error response time: {sum(error)/len(error)} seconds")
