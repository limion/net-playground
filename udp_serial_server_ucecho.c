#include <stdio.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <unistd.h>
#include <ctype.h>
#include <arpa/inet.h>

#define INET_PROTOCOL 0
#define PORT 8080
#define MAX_CLIENTS 5

void handle_request(int server_socket)
{
    struct sockaddr_in client_addr;
    unsigned int client_addr_size = sizeof(client_addr);
    char buffer[1024];
    int bytes_received;

    bytes_received = recvfrom(server_socket, buffer, sizeof(buffer), 0, (struct sockaddr *)&client_addr, &client_addr_size);
    buffer[bytes_received - 1] = '\0';

    char response[bytes_received];
    for (int i = 0; i < bytes_received; i++)
    {
        response[i] = toupper(buffer[i]);
    }

    printf("%s from %s\n", buffer, inet_ntoa(client_addr.sin_addr));

    sendto(server_socket, response, sizeof(response), 0, (struct sockaddr *)&client_addr, client_addr_size);
}

int main()
{
    int server_socket = socket(AF_INET, SOCK_DGRAM, INET_PROTOCOL);
    if (server_socket == -1)
    {
        printf("Socket creation failed\n");
        return 1;
    }

    struct sockaddr_in server_addr;
    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(PORT);
    server_addr.sin_addr.s_addr = INADDR_ANY;

    int bind_status = bind(server_socket, (struct sockaddr *)&server_addr, sizeof(server_addr));
    if (bind_status == -1)
    {
        printf("Socket binding failed\n");
        return 1;
    }

    printf("Server is binded on port %d\n", PORT);

    for (;;)
    {
        handle_request(server_socket);
    }

    return 0;
}