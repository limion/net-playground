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

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <arpa/inet.h>
#include <sys/types.h>
#include <netinet/in.h>
#include <sys/select.h>

#define REQUEST_FLAGS 0
#define INET_PROTOCOL 0
#define PORT 53
#define FIELD_SIZE 2
#define BUFFER_SIZE 2048
#define RESPONSE_FLAGS 0

struct dns_header_flags
{
  unsigned int rcode : 4;
  unsigned int z : 3;
  unsigned int ra : 1;
  unsigned int rd : 1;
  unsigned int tc : 1;
  unsigned int aa : 1;
  unsigned int opcode : 4;
  unsigned int qr : 1;
};
struct dns_header
{
  unsigned short message_id;
  unsigned short flags;
  unsigned short qd_count;
  unsigned short an_count;
  unsigned short ns_count;
  unsigned short as_count;
};

struct dns_question
{
  char *qname;
  unsigned short qtype;
  unsigned short qclass;
};

struct dns_resource_record
{
  unsigned short offset;
  unsigned short type;
  unsigned short class;
  unsigned int ttl;
  unsigned short rd_length;
  // Let's assume it's the A type record
  char ip_addr[4];
};

static short
get_qname_len(char *host)
{
  // For the correct hostname the length of the qname is:
  return (short)(strlen(host) + 2);
}

static char *hostname_to_qname(char *host)
{
  short qname_len = get_qname_len(host);
  char *qname = calloc(qname_len, 1);
  char *pos = qname;
  // Because strtok changes the original string let's work with the local copy
  char host_copy[strlen(host)];
  strcpy(host_copy, host);
  char *token = strtok(host_copy, ".");
  while (token)
  {
    *pos++ = strlen(token);
    strcpy(pos, token);
    pos += strlen(token);
    token = strtok(NULL, ".");
  }
  *pos = 0;
  if (strlen(qname) + 1 < qname_len)
  {
    return NULL;
  }
  return qname;
}

static void hydrate_dns_header(struct dns_header *header)
{
  struct dns_header_flags *flags = (struct dns_header_flags *)&header->flags;
  header->message_id = 1;
  flags->qr = 0;
  flags->opcode = 0;
  flags->aa = 0;
  flags->tc = 0;
  flags->rd = 1;
  flags->ra = 0;
  flags->z = 0;
  flags->rcode = 0;
  header->flags = *(unsigned short *)flags;
  header->qd_count = 1;
  header->an_count = 0;
  header->ns_count = 0;
  header->as_count = 0;
}

static void flip_dns_header(struct dns_header *header)
{
  header->message_id = htons(header->message_id);
  header->flags = htons(header->flags);
  header->qd_count = htons(header->qd_count);
  header->an_count = htons(header->an_count);
  header->ns_count = htons(header->ns_count);
  header->as_count = htons(header->as_count);
}

static void hydrate_message(char *message, char *qname)
{
  // We can do direct mapping of the dns_header into the message because struct dns_header will be aligned without gaps
  struct dns_header *header = (struct dns_header *)message;
  hydrate_dns_header(header);
  flip_dns_header(header);

  char *question_start = message + sizeof(struct dns_header);
  strcpy(question_start, qname);
  short *pos = (short *)(question_start + strlen(qname) + 1);
  *pos++ = htons(1); // QTYPE
  *pos++ = htons(1); // QCLASS
}

static void extract_header(struct dns_header *header)
{
  header->message_id = ntohs(header->message_id);
  header->flags = ntohs(header->flags);
  header->qd_count = ntohs(header->qd_count);
  header->an_count = ntohs(header->an_count);
  header->ns_count = ntohs(header->ns_count);
  header->as_count = ntohs(header->as_count);
}

static void extract_question(struct dns_question *question, char *start_pos)
{
  short qname_len = strlen(start_pos);
  question->qname = malloc(qname_len - 1);
  char *section_pos = start_pos;
  char *qname_pos = question->qname;
  while (section_pos < start_pos + qname_len)
  {
    if (qname_pos > question->qname)
    {
      *qname_pos++ = '.';
    }
    memcpy(qname_pos, section_pos + 1, *section_pos);
    qname_pos += *section_pos;
    section_pos += *section_pos + 1;
  }
  *qname_pos = 0;
  unsigned short *pos = (unsigned short *)(section_pos + 1);
  question->qtype = ntohs(*pos++);
  question->qclass = ntohs(*pos);
}

static void extract_resource_record(struct dns_resource_record *record, char *source)
{
  unsigned short *pos = (unsigned short *)source;
  record->offset = ntohs(*pos++) & 0x3FFF;
  record->type = ntohs(*pos++);
  record->class = ntohs(*pos++);
  record->ttl = ntohl(*(unsigned int *)pos);
  pos += 2;
  record->rd_length = ntohs(*pos++);
  struct in_addr addr = {*(unsigned int *)pos};
  strcpy(record->ip_addr, inet_ntoa(addr));
}

int main(int argc, char *argv[])
{
  if (argc < 3)
  {
    printf("Usage: %s nameserver_ip host\n", argv[0]);
    exit(0);
  }

  int client_socket;
  struct sockaddr_in server_addr;
  char *target_host = argv[2];
  char *resolver_ip = argv[1];

  char *qname = hostname_to_qname(target_host);
  if (qname == NULL)
  {
    printf("Wrong hostname\n");
    exit(0);
  }

  client_socket = socket(AF_INET, SOCK_DGRAM, INET_PROTOCOL);

  server_addr.sin_family = AF_INET;
  server_addr.sin_addr.s_addr = inet_addr(resolver_ip);
  server_addr.sin_port = htons(PORT);

  short message_len = sizeof(struct dns_header) + strlen(qname) + 1 + 2 * FIELD_SIZE;
  char *message = malloc(message_len);
  hydrate_message(message, qname);

  if (sendto(client_socket, message, message_len, REQUEST_FLAGS, (struct sockaddr *)&server_addr, sizeof(server_addr)) < 0)
  {
    perror("Error sending message");
    exit(0);
  }
  free(qname);
  free(message);

  fd_set rfds;
  FD_ZERO(&rfds);
  FD_SET(client_socket, &rfds);
  struct timeval tv = {5, 0}; // 5 seconds timeout
  int sel_ret = select(client_socket + 1, &rfds, NULL, NULL, &tv);
  if (sel_ret < 0)
  {
    perror("Error in select()");
    exit(0);
  }
  if (sel_ret == 0)
  {
    printf("Request timeout\n");
    exit(0);
  }

  char *response = calloc(BUFFER_SIZE, 1);
  short response_len = recvfrom(client_socket, response, BUFFER_SIZE, RESPONSE_FLAGS, NULL, NULL);

  printf("Got %d bytes\n", response_len);

  struct dns_header *header = (struct dns_header *)response;
  flip_dns_header(header);

  struct dns_header_flags *flags = (struct dns_header_flags *)&header->flags;
  printf("Header:\n");
  printf("\tmessage_id: %d\n", header->message_id);
  printf("\tflags:\n");
  printf("\t\tqr: %d\n", flags->qr);
  printf("\t\topcode: %d\n", flags->opcode);
  printf("\t\taa: %d\n", flags->aa);
  printf("\t\ttc: %d\n", flags->tc);
  printf("\t\trd: %d\n", flags->rd);
  printf("\t\tra: %d\n", flags->ra);
  printf("\t\tz: %d\n", flags->z);
  printf("\t\trcode: %d\n", flags->rcode);
  printf("\tqd_count: %d\n", header->qd_count);
  printf("\tan_count: %d\n", header->an_count);
  printf("\tns_count: %d\n", header->ns_count);
  printf("\tas_count: %d\n", header->as_count);

  struct dns_question question;
  extract_question(&question, response + sizeof(struct dns_header));
  printf("Question:\n");
  printf("\tqname: %s\n", question.qname);
  printf("\tqtype: %d\n", question.qtype);
  printf("\tqclass: %d\n", question.qclass);

  struct dns_resource_record record;
  char *source;
  for (int i = 0; i < header->an_count; i++)
  {
    source = response + sizeof(struct dns_header) + get_qname_len(question.qname) + 2 * FIELD_SIZE + i * 16;
    extract_resource_record(&record, source);
    printf("Answer:\n");
    printf("\toffset: %d\n", record.offset);
    printf("\ttype: %d\n", record.type);
    printf("\tclass: %d\n", record.class);
    printf("\tttl (seconds): %d\n", record.ttl);
    printf("\trd_length: %d\n", record.rd_length);
    printf("\tip: %s\n", record.ip_addr);
  }

  // free(question.qname);
  free(response);

  return 0;
}
