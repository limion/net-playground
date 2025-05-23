package main

import (
	"errors"
	"flag"
	"fmt"
	"io"
	"log"
	"math"
	"net/http"
	"os"
	"strconv"
	"strings"
	"sync"
	"time"
)
	
func doRequest(client *http.Client,  url string, headers []header, method string, body string) (int, error) {
	req, err := http.NewRequest(strings.ToUpper(method), url, strings.NewReader(body))
	if err != nil {
		log.Panic(err)
	}
	for _, h := range headers {
		req.Header.Add(h.key, h.value)
	}
	resp, err := client.Do(req)
	if err != nil {
		log.Panic(err)
	}
	io.Copy(io.Discard, resp.Body) //reads the entire body to EOF, clearing the TCP stream.
	defer resp.Body.Close()
	if (resp.StatusCode != http.StatusOK) {
		return -1, errors.New(strconv.Itoa(resp.StatusCode))
	}
	if resp.Header["Content-Length"] == nil || len(resp.Header["Content-Length"]) == 0 {
		return -1, errors.New("Wrong Content-Length header")
	}
	contentLength, err := strconv.Atoi(resp.Header["Content-Length"][0])
	if err != nil || contentLength <= 0 {
		return -1, errors.New("Wrong Content-Length header")
	}
	return contentLength, nil
}

func formatBytes(bytes int) string {
	const unit = 1024
	if bytes < unit {
		return fmt.Sprintf("%d B", bytes)
	}
	div, exp := unit, 0
	for n := bytes / unit; n >= unit; n /= unit {
		div *= unit
		exp++
	}
	return fmt.Sprintf("%.1f %cB", float64(bytes)/float64(div), "KMGTPE"[exp])
}

type headerFlagList []string

func (h *headerFlagList) String() string {
	return strings.Join(*h, ", ")
}

func (h *headerFlagList) Set(value string) error {
	*h = append(*h, value)
	return nil
}

type header struct {
	key string
	value string
}

func main() {

	var headerFlags headerFlagList
	var headers []header

    concurrentRequestsPtr := flag.Int("concurrent_requests", 10, "number of concurrent requests")
    totalRequestsPtr := flag.Int("total_requests", 1000, "total number of requests to be made")
    methodPtr := flag.String("method", "get", "request method")
	flag.Var(&headerFlags, "header", "HTTP headers (K=V) to include in the request (can be specified multiple times)")
    bodyPtr := flag.String("data", "", "body to send in the request")

	// Override the usage output
	flag.Usage = func() {
		fmt.Fprintf(flag.CommandLine.Output(),
			"Usage: %s [flags] url\n\nFlags:\n", os.Args[0])
		flag.PrintDefaults()
	}

    flag.Parse()

	if len(flag.Args()) < 1 {
		flag.Usage()
		os.Exit(1)
	}

	url := flag.Arg(0)

    fmt.Println("concurrent_requests:", *concurrentRequestsPtr)
    fmt.Println("total_requests:", *totalRequestsPtr)
    fmt.Println("url:", url)
    fmt.Println("method:",*methodPtr)
	if (len(headerFlags) > 0) {
		fmt.Println("headers:")
		for _, h := range headerFlags {
			parts := strings.Split(h, "=")
			if len(parts) != 2 {
				fmt.Println("Invalid header format. Use K=V")
				os.Exit(1)
			}
			key := strings.TrimSpace(parts[0])
			value := strings.TrimSpace(parts[1])
			if key == "" || value == "" {
				fmt.Println("Invalid header format. Use K=V")
				os.Exit(1)
			}
			headers = append(headers, header{key: key, value: value})
			fmt.Println(" -", h)
		}
	}
	if (len(*bodyPtr) > 0) {
		fmt.Println("body:", *bodyPtr)
	}

	var tr *http.Transport = &http.Transport{
		MaxIdleConns:        100,
		MaxConnsPerHost:     *concurrentRequestsPtr,
		IdleConnTimeout:     60 * time.Second,
		DisableKeepAlives:   false,
		WriteBufferSize:     8 * 1024, // Reduce buffer size not to exhaust memory
		ReadBufferSize:      8 * 1024, 
	}
	
	var client *http.Client = &http.Client{Transport: tr}

	type Result struct {
		success bool
		time time.Duration
		contentLength  int
		err error
	}
	
	var success []Result
	var failure []Result

	results := make(chan Result, *totalRequestsPtr)
	sem := make(chan struct{}, *concurrentRequestsPtr)

	var wg sync.WaitGroup

	startTime := time.Now()

	for range *totalRequestsPtr {
		wg.Add(1)
		sem <- struct{}{}

		go func() {
            defer wg.Done()
			defer func() { <-sem }()

			startTime := time.Now()
			contentLength, err := doRequest(client, url, headers, *methodPtr, *bodyPtr)
			if err != nil {
				results <- Result{success: false, err: err}
			} else {
				results <- Result{success: true, time: time.Since(startTime), contentLength: contentLength}
			}
        }()
	}

	wg.Wait()

	workingTime := time.Since(startTime)

	fmt.Println("All requests completed.")
	close(results)

	for res := range results {
		if res.success {
			success = append(success, res)
		} else {
			failure = append(failure, res)
		}
	}

	// Statistics
	fmt.Println("Total requests:", len(success)+len(failure))
	fmt.Println("Successful requests:", len(success))
	fmt.Println("Failed requests:", len(failure))
	fmt.Println("Success rate:", float64(len(success))/float64(len(success)+len(failure))*100, "%")
	fmt.Println("Failure rate:", float64(len(failure))/float64(len(success)+len(failure))*100, "%")
	var totalTime time.Duration
	for _, result := range success {
		totalTime += result.time
	}
	fmt.Println("Average request time: ", func() time.Duration {
		if len(success) == 0 {
			return 0
		}
		return (totalTime / time.Duration(len(success)))
	}(),
	)
	fmt.Println("Minimum request time:", func() time.Duration {
		if len(success) == 0 {
			return 0
		}
		min := time.Duration(1<<63 - 1) // = math.MaxInt64
		for _, result := range success {
			if result.time < min {
				min = result.time
			}
		}
		return min
	}(),
	)
	fmt.Println("Maximum request time:", func() time.Duration {
		if len(success) == 0 {
			return 0
		}
		max := 0 * time.Second
		for _, result := range success {
			if result.time > max {
				max = result.time
			}
		}
		return max
	}(),
	)
	fmt.Println("Total time:", workingTime)
	fmt.Println("Requests per second:", func() float64 {
		if workingTime == 0 {
			return 0
		}
		return math.Round(float64(len(success)) / workingTime.Seconds())
	}(),
	)	
	var totalContentLength int
	for _, result := range success {
		totalContentLength += result.contentLength
	}
	fmt.Println("Average content length:", formatBytes(func() int {
		if len(success) == 0 {
			return 0
		}
		return totalContentLength / len(success)
	}()),
	)
	fmt.Println("Minimum content length:", formatBytes(func() int {
		if len(success) == 0 {
			return 0
		}
		min := 1<<63 - 1
		for _, result := range success {
			if result.contentLength < min {
				min = result.contentLength
			}
		}
		return min
	}()),
	)
	fmt.Println("Maximum content length:", formatBytes(func() int {
		if len(success) == 0 {
			return 0
		}
		max := 0
		for _, result := range success {
			if result.contentLength > max {
				max = result.contentLength
			}
		}
		return max
	}()),
	)
	fmt.Println("Total content length:", formatBytes(totalContentLength))
}