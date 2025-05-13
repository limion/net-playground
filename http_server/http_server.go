package main

import (
	"flag"
	"fmt"
	"net/http"
	"os"
	"strconv"
)


func main() {
    portPtr := flag.Int("port", 8080, "port number")

	// Override the usage output
	flag.Usage = func() {
		fmt.Fprintf(flag.CommandLine.Output(),
			"Usage: %s [flags] path_to_index_html\n\nFlags:\n", os.Args[0])
		flag.PrintDefaults()
	}

	flag.Parse()

	if len(flag.Args()) < 1 {
		flag.Usage()
		os.Exit(1)
	}

	pathToIndexHtml := flag.Arg(0)

	fmt.Println("port:", *portPtr)
	fmt.Println("index.html:", pathToIndexHtml)

	hello := func (w http.ResponseWriter, req *http.Request) {
		http.ServeFile(w, req, pathToIndexHtml)
	}

    http.HandleFunc("GET /{$}", hello)
	err := http.ListenAndServe(":"+strconv.Itoa(*portPtr), nil)
	if err != nil {
		fmt.Println("Server error:", err)
	}
}