#include <stdio.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <unistd.h>
#include <ctype.h>
#include <arpa/inet.h>
#include <pthread.h>
#include <string.h>

#define INET_PROTOCOL 0
#define PORT 8080
#define MAX_CLIENTS 5

struct handle_request_args
{
    int tid;
    int server_socket;
    char *buffer;
    struct sockaddr_in *client_addr;
    unsigned int client_addr_size;
};

void *handle_request(void *raw_args)
{
    struct handle_request_args *args = (struct handle_request_args *)raw_args;
    int bytes_received = strlen(args->buffer);
    char response[bytes_received];
    for (int i = 0; i < bytes_received; i++)
    {
        response[i] = toupper(args->buffer[i]);
    }

    printf("(thread: #%d) %s from %s\n", args->tid, args->buffer, inet_ntoa(args->client_addr->sin_addr));

    sendto(args->server_socket, response, sizeof(response), 0, (struct sockaddr *)args->client_addr, args->client_addr_size);

    pthread_exit(NULL);
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

    struct sockaddr_in client_addr;
    unsigned int client_addr_size = sizeof(client_addr);
    char buffer[1024];
    int bytes_received, tid = 0;

    for (;;)
    {
        bytes_received = recvfrom(server_socket, buffer, sizeof(buffer), 0, (struct sockaddr *)&client_addr, &client_addr_size);
        buffer[bytes_received - 1] = '\0'; // replace \n with \0
        pthread_t thread;
        struct handle_request_args args = {tid++, server_socket, buffer, &client_addr, client_addr_size};
        int status = pthread_create(&thread, NULL, handle_request, (void *)&args);
        if (status != 0)
        {
            printf("Oops. pthread_create returned error code %d\n", status);
            return 1;
        }
    }

    return 0;
}