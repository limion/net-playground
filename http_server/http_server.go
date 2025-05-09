package main

import (
	"flag"
	"fmt"
	"net/http"
	"strconv"
)

func hello(w http.ResponseWriter, req *http.Request) {
    fmt.Fprintf(w, "hello\n")
}

func main() {
    portPtr := flag.Int("port", 8080, "port number")
	flag.Parse()

	fmt.Println("port:", *portPtr)

    http.HandleFunc("GET /{$}", hello)
	err := http.ListenAndServe(":"+strconv.Itoa(*portPtr), nil)
	if err != nil {
		fmt.Println("Server error:", err)
	}
}