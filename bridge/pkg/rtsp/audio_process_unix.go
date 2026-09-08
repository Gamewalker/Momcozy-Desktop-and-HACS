//go:build !windows

package rtsp

import "os/exec"

func configureAudioProcess(cmd *exec.Cmd)              {}
func attachAudioProcess(cmd *exec.Cmd) (func(), error) { return func() {}, nil }
