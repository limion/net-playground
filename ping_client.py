"""
Simple ping client for learning purposes

Ping utility is implemented using the ICMP echo request
and echo reply messages.
The ICMP packet is encapsulated in an IPv4 packet.
ICMP packets have an 8-byte header and variable-sized data section.
The first 4 bytes of the header have fixed format,
while the last 4 bytes depend on the type/code of that ICMP packet.

Echo or Echo Reply Message
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|     Type      |     Code      |          Checksum             |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|           Identifier          |        Sequence Number        |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|     Data ...
+-+-+-+-+-

Thanx to https://github.com/satoshi03/pings
"""
import sys
import socket
import struct

ICMP_ECHO_TYPE = 8
ICMP_ECHO_CODE = 0


def checksum(payload):
    """
    Internet Checksum
    """
    # Calculate number of two byte steps
    int_steps = (int(len(payload) / 2)) * 2
    result_sum = 0
    step = 0
    # Calculate the sum of two byte integers taking the endiannes of the host into account
    lo_byte = 0
    hi_byte = 0
    while step < int_steps:
        if sys.byteorder == "little":
            [lo_byte, hi_byte] = [payload[step], payload[step + 1]]
        else:
            [hi_byte, lo_byte] = [payload[step], payload[step + 1]]
        number = hi_byte * 256 + lo_byte
        result_sum += number
        step += 2
    # Handle the last byte if the length of the payload is odd
    if int_steps < len(payload):
        number = payload[-1]
        result_sum += number
    # Cut off all the carries and add them to the resulting sum (the result has to be 2 bytes)
    carries = result_sum >> 16
    sum_without_carries = result_sum & 0xFFFF
    result_sum = sum_without_carries + carries
    # Add carries again if we got any
    result_sum = (result_sum >> 16) + (result_sum & 0xFFFF)
    # Take the 1's complement of the final sum (flip the bits)
    complement = ~result_sum
    # Cut the result to 16 bits, because we do calculation on a system that has more than 16 bits
    # and it means we got a negative integer as a result
    complement &= 0xFFFF
    # Convert two byte int from the host format to the network format (big-endian)
    return socket.htons(complement)


def make_packet():
    packet_id = 0
    seq_number = 0
    # For computing the checksum , the checksum field should be zero.
    header_without_checksum = struct.pack(
        "!BBHHH", ICMP_ECHO_TYPE, ICMP_ECHO_CODE, 0, packet_id, seq_number
    )
    data = bytearray("Glory to Ukraine!".encode("ascii"))
    resulting_checksum = checksum(header_without_checksum + data)
    header = struct.pack(
        "!BBHHH",
        ICMP_ECHO_TYPE,
        ICMP_ECHO_CODE,
        resulting_checksum,
        packet_id,
        seq_number,
    )
    return header + data


def extract_icmp_header_and_data(packet):
    """
    Parse icmp packet header to dict and return it along with data part
    """
    p = struct.unpack("!BBHHH", packet[:8])

    icmp_header = {}
    icmp_header["type"] = p[0]
    icmp_header["code"] = p[1]
    icmp_header["checksum"] = p[2]
    icmp_header["packet_id"] = p[3]
    icmp_header["sequence"] = p[4]
    return [icmp_header, packet[8:]]


def extract_ip_header_and_data(packet):
    """
    Parse ip packet header to dict and return it along with data part
    """
    p = struct.unpack("!BBHHHBBHII", packet[:20])

    ip_header = {}
    ip_header["version"] = p[0]
    ip_header["type"] = p[1]
    ip_header["length"] = p[2]
    ip_header["id"] = p[3]
    ip_header["flags"] = p[4]
    ip_header["ttl"] = p[5]
    ip_header["protocol"] = p[6]
    ip_header["checksum"] = p[7]
    ip_header["src_ip"] = p[8]
    return [ip_header, packet[20:]]


def ping(host):
    try:
        ip_addr = socket.gethostbyname(host)
    except socket.gaierror:
        print("Can't resolve host: ", host)
        return

    try:
        client_socket = socket.socket(
            socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP
        )
    except socket.error as err:
        etype, evalue, etb = sys.exc_info()
        if err.errno == 1:
            # Operation not permitted
            msg = (
                str(evalue)
                + """ - ICMP messages can only be send from
            processes running as root."""
            )
        else:
            msg = str(evalue)
        print(msg)
        return

    icmp_packet = make_packet()
    print(f"Sending ICMP echo request to {host} ({ip_addr})")
    [icmp_request_header, icmp_request_data] = extract_icmp_header_and_data(icmp_packet)
    print("ICMP Header:\n", icmp_request_header)
    print("ICMP Data:\n", icmp_request_data)
    client_socket.sendto(icmp_packet, (ip_addr, 0))
    # As a response we get a whole IP packet, because of socket.SOCK_RAW
    ip_packet, (address, port) = client_socket.recvfrom(2048)
    print(f"\nResponse from {address}")
    [ip_header, ip_data] = extract_ip_header_and_data(ip_packet)
    print("IP Header:\n", ip_header)
    [icmp_header, icmp_data] = extract_icmp_header_and_data(ip_data)
    print("ICMP Header:\n", icmp_header)
    print("ICMP Data:\n", icmp_data)
    if icmp_request_data == icmp_data:
        print("\nSUCCESS!")
    else:
        print("\nFAILED")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("host")
    ns = parser.parse_args()
    ping(**ns.__dict__)
