package main

import (
	"encoding/json"
	"fmt"
	"github.com/rs/zerolog"
	"os"
	"strings"

	"avent-webrtc-bridge/cmd"
	"avent-webrtc-bridge/pkg/core"
)

const VERSION = "0.0.6"

func main() {
	core.InitLogger()
	core.Logger = core.Logger.Level(zerolog.InfoLevel)
	if len(os.Args) == 2 && !strings.HasPrefix(os.Args[1], "-") {
		data, err := os.ReadFile(os.Args[1])
		if err != nil {
			fmt.Println("Cannot read local bridge configuration")
			os.Exit(1)
		}
		var flags map[string]string
		if json.Unmarshal(data, &flags) != nil {
			fmt.Println("Invalid bridge configuration")
			os.Exit(1)
		}
		os.Args = []string{os.Args[0], "direct"}
		for k, v := range flags {
			os.Args = append(os.Args, "--"+k, v)
		}
	}

	if err := cmd.Execute(VERSION); err != nil {
		fmt.Println("Command execution failed")
		os.Exit(1)
	}
}
