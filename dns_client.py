"""
Simple DNS client for learning purposes.
Let's implement the Question for the A record

The top level format of message is divided
into 5 sections (some of which are empty in certain cases) shown below:
+---------------------+
|        Header       |
+---------------------+
|       Question      | the question for the name server
+---------------------+
|        Answer       | RRs answering the question
+---------------------+
|      Authority      | RRs pointing toward an authority
+---------------------+
|      Additional     | RRs holding additional information
+---------------------+

The header contains the following fields:
                               1  1  1  1  1  1
 0  1  2  3  4  5  6  7  8  9  0  1  2  3  4  5
+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
|                      ID                       |
+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
|QR|   Opcode  |AA|TC|RD|RA|   Z    |   RCODE   |
+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
|                    QDCOUNT                    |
+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
|                    ANCOUNT                    |
+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
|                    NSCOUNT                    |
+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
|                    ARCOUNT                    |
+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+

Question section format
                                1  1  1  1  1  1
  0  1  2  3  4  5  6  7  8  9  0  1  2  3  4  5
+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
|                                               |
/                     QNAME                     /
/                                               /
+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
|                     QTYPE                     |
+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
|                     QCLASS                    |
+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+

Resource record format:
                                1  1  1  1  1  1
  0  1  2  3  4  5  6  7  8  9  0  1  2  3  4  5
+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
|                                               |
/                                               /
/                      NAME                     /
|                                               |
+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
|                      TYPE                     |
+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
|                     CLASS                     |
+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
|                      TTL                      |
|                                               |
+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
|                   RDLENGTH                    |
+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--|
/                     RDATA                     /
/                                               /
+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+

In order to reduce the size of messages, the domain system utilizes a
compression scheme which eliminates the repetition of domain names in a
message.  In this scheme, an entire domain name or a list of labels at
the end of a domain name is replaced with a pointer to a prior occurance
of the same name.

The pointer takes the form of a two octet sequence:

+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+
| 1  1|                OFFSET                   |
+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+--+

The OFFSET field specifies an offset from
the start of the message (i.e., the first octet of the ID field in the
domain header).
"""
import sys
import socket
import struct
from select import select


def calculate_qname(domain: str):
    labels = domain.split(".")
    return (
        b"".join(
            map(lambda label: len(label).to_bytes(1, "big") + label.encode(), labels)
        )
        + b"\x00"
    )


def make_dns_request_message(host: str):
    message_id = b"\x00\x01"
    query_with_only_reqursion_desired = b"\x01\x00"
    qd_count = b"\x00\x01"
    an_count = b"\x00\x00"
    ns_count = b"\x00\x00"
    ar_count = b"\x00\x00"
    type_A = b"\x00\x01"
    class_IN = b"\x00\x01"
    return (
        message_id
        + query_with_only_reqursion_desired
        + qd_count
        + an_count
        + ns_count
        + ar_count
        + calculate_qname(host)
        + type_A
        + class_IN
    )


def extract_header(msg: bytes):
    p = struct.unpack("!HHHHHH", msg[:12])
    codes = p[1]
    return {
        "message_id": p[0],
        "flags": {
            "qr": (codes >> 15) & 0x0001,
            "opcode": (codes >> 11) & 0x000F,
            "aa": (codes >> 10) & 0x0001,
            "tc": (codes >> 9) & 0x0001,
            "rd": (codes >> 8) & 0x0001,
            "ra": (codes >> 7) & 0x0001,
            "z": (codes >> 4) & 0x0007,
            "rcode": codes & 0x000F,
        },
        "qd_count": p[2],
        "an_count": p[3],
        "ns_count": p[4],
        "ar_count": p[5],
    }


def extract_question(msg: bytes):
    buf = msg[12:]
    labels = []
    length = 0
    cur = 0
    lab_counter = 0
    len_counter = 0
    while cur < len(buf):
        if buf[cur] == 0:
            break
        if length == 0:
            length = buf[cur]
        else:
            len_counter += 1
            if len(labels) > lab_counter:
                labels[lab_counter] = labels[lab_counter] + chr(buf[cur])
            else:
                labels.append(chr(buf[cur]))
            if len_counter == length:
                length = 0
                lab_counter += 1
        cur += 1

    return {
        "name": ".".join(labels),
        "type": struct.unpack("!H", buf[cur + 1 : cur + 3])[0],
        "class": struct.unpack("!H", buf[cur + 3 : cur + 5])[0],
        "answer_offset": cur + 5,
    }


def extract_resource_record(msg: bytes, offset: int):
    p = struct.unpack("!HHHIH", msg[offset : offset + 12])
    return {
        "offset": p[0] & 0x3FFF,
        "type": p[1],
        "class": p[2],
        "ttl (seconds)": p[3],
        "rd_length": p[4],
        "ip": ".".join([str(byte) for byte in msg[offset + 12 : offset + 12 + p[4]]]),
    }


def lookup(host: str, ns_addr: str, timeout: int):
    client_socket = socket.socket(type=socket.SOCK_DGRAM)

    dns_request = make_dns_request_message(host)
    client_socket.sendto(dns_request, (ns_addr, 53))

    r, w, e = select([client_socket], [], [], timeout)
    if len(r) == 0:
        # timeout
        print("Request timeout")
        sys.exit()

    dns_response, (address, port) = client_socket.recvfrom(512)
    print(f"\nGot {len(dns_response)} bytes from {address}:{port}")
    header_section = extract_header(dns_response)
    print(f"Header: {header_section}")
    question_section = extract_question(dns_response)
    print("Question:", question_section)
    for i in range(0, header_section["an_count"]):
        offset = 12 + question_section["answer_offset"] + i * 16
        print(f"Answer: {extract_resource_record(dns_response, offset)}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-nsip",
        "--nameserver_ip",
        dest="ns_addr",
        required=True,
        type=str,
        help="ip address of the nameserver",
    )
    parser.add_argument(
        "-t",
        "--timeout",
        dest="timeout",
        type=int,
        default=1,
        help="timeout in seconds",
    )
    parser.add_argument("host")
    ns = parser.parse_args()
    lookup(**ns.__dict__)
