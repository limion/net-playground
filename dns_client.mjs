/**
Simple DNS client for learning purposes.
Let's implement the Question for the A record
It works correctly only with the Answers of the A type

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

Question section format:
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
*/

import dgram from "node:dgram";
import { Buffer } from "node:buffer";

function calculateQname(hostname) {
  const labels = hostname.split(".");
  return Buffer.concat([
    ...labels.map((label) =>
      Buffer.concat([Buffer.from([label.length]), Buffer.from(label, "ascii")])
    ),
    Buffer.from([0]),
  ]);
}

function createMessage(hostname) {
  const message_id = [0, 2];
  const query_with_only_reqursion_desired = [0b00000001, 0b00000000];
  const qd_count = [0, 1];
  const an_count = [0, 0];
  const ns_count = [0, 0];
  const ar_count = [0, 0];
  const type_A = [0, 1];
  const class_IN = [0, 1];
  return Buffer.concat([
    Buffer.from(message_id),
    Buffer.from(query_with_only_reqursion_desired),
    Buffer.from(qd_count),
    Buffer.from(an_count),
    Buffer.from(ns_count),
    Buffer.from(ar_count),
    calculateQname(hostname),
    Buffer.from(type_A),
    Buffer.from(class_IN),
  ]);
}

function extractHeader(msg) {
  const codes = msg.readUInt16BE(2);
  return {
    messageId: msg.readUInt16BE(0),
    flags: {
      qr: (codes >> 15) & 0x0001,
      opcode: (codes >> 11) & 0x000f,
      aa: (codes >> 10) & 0x0001,
      tc: (codes >> 9) & 0x0001,
      rd: (codes >> 8) & 0x0001,
      ra: (codes >> 7) & 0x0001,
      z: (codes >> 4) & 0x0007,
      rcode: codes & 0x000f,
    },
    qdCount: msg.readUInt16BE(4),
    anCount: msg.readUInt16BE(6),
    nsCount: msg.readUInt16BE(8),
    arCount: msg.readUInt16BE(10),
  };
}

function extractQuestion(msg) {
  const buf = msg.subarray(12);
  const labels = [];
  let len = 0;
  let cur = 0;
  let labCounter = 0;
  let lenCounter = 0;
  while (cur < buf.length) {
    if (buf[cur] === 0) {
      break;
    }
    if (len === 0) {
      len = buf[cur];
    } else {
      lenCounter++;
      labels[labCounter] =
        (labels[labCounter] || "") + String.fromCharCode(buf[cur]);
      if (lenCounter === len) {
        len = 0;
        labCounter++;
      }
    }
    cur++;
  }
  return {
    name: labels.join("."),
    type: buf.readUInt16BE(cur + 1),
    class: buf.readUInt16BE(cur + 3),
    answerOffset: cur + 5,
  };
}

function extractResourceRecord(msg, offset) {
  const buf = msg.subarray(offset);
  const rdLength = buf.readUInt16BE(10);
  return {
    offset: buf.readUInt16BE(0) & 0x3fff,
    type: buf.readUInt16BE(2),
    class: buf.readUInt16BE(4),
    "ttl (seconds)": buf.readUInt32BE(6),
    rdLength,
    ip: buf
      .subarray(12, 12 + rdLength)
      .map((byte) => byte.toString(10))
      .join("."),
  };
}

const [ns_ip, hostname] = process.argv.slice(2);
if (!ns_ip || !hostname) {
  console.log(
    `Usage: ${process.argv[0]} ${process.argv[1]} nameserver_addr host`
  );
  process.exit();
}

let timeout;

const socket = dgram.createSocket("udp4");
socket.on("error", (err) => {
  console.log(`Got error:\n${err}`);
  socket.close();
});
socket.on("message", (msg, rinfo) => {
  clearTimeout(timeout);
  console.log(`Got ${rinfo.size} bytes from ${rinfo.address}:${rinfo.port}`);
  const headerSection = extractHeader(msg);
  console.log("Header:", headerSection);
  const questionSection = extractQuestion(msg);
  console.log("Question:", questionSection);
  for (let i = 0; i < headerSection.anCount; i++) {
    const offset = 12 + questionSection.answerOffset + i * 16;
    console.log("Answer:", extractResourceRecord(msg, offset));
  }
  socket.close();
});

socket.send(createMessage(hostname), 53, ns_ip, (err) => {
  if (err) {
    console.log("Error while sending a message", err);
    socket.close();
  }
  timeout = setTimeout(() => {
    console.log("Request timeout");
    socket.close();
  }, 2000);
});
