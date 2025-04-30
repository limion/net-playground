package main

import (
	"errors"
	"flag"
	"fmt"
	"log"
	"net/http"
	"os"
	"strconv"
	"sync"
	"time"
)
	
type SuccessResult struct {
    time time.Duration
    contentLength  int
}

var success []SuccessResult
var failure []error

var tr *http.Transport = &http.Transport{
	MaxIdleConns:        1000,
	MaxConnsPerHost:     1000,
	IdleConnTimeout:     90 * time.Second,
	DisableKeepAlives:   false,
	WriteBufferSize:     8 * 1024, // Reduce buffer size not to exhaust memory
	ReadBufferSize:      8 * 1024, 
}

var client *http.Client = &http.Client{Transport: tr}

func doRequest(url string) (int, error) {
	resp, err := client.Get(url)
	if err != nil {
		log.Panic(err)
	}
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

func worker(workerId int, url string, jobs chan int) {
	for range jobs {
		startTime := time.Now()
		contentLength, err := doRequest(url)
		if err != nil {
			failure = append(failure, err)
		} else {
			success = append(success, SuccessResult{time: time.Since(startTime), contentLength: contentLength})
		}
	}
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

func main() {

    conreqPtr := flag.Int("concurrent_requests", 10, "number of concurrent requests")
    totalRequestsPtr := flag.Int("total_requests", 1000, "total number of requests to be made")

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

    fmt.Println("concurrent_requests:", *conreqPtr)
    fmt.Println("total_requests:", *totalRequestsPtr)
    fmt.Println("url:", url)

	jobs := make(chan int, *totalRequestsPtr)

	var wg sync.WaitGroup

	for i := 0; i < *conreqPtr; i++ {
		wg.Add(1)
		go func() {
            defer wg.Done()
            worker(i, url, jobs)
        }()
	}

	startTime := time.Now()

	for i := 0; i < *totalRequestsPtr; i++ {
		jobs <- i
	}
	close(jobs)

	wg.Wait()

	workingTime := time.Since(startTime)

	fmt.Println("All requests completed.")

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