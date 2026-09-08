//go:build !windows

package desktop

import (
	"os"
	"os/exec"
	"syscall"
)

func configureChild(cmd *exec.Cmd)       { cmd.SysProcAttr = &syscall.SysProcAttr{Setpgid: true} }
func interruptChild(cmd *exec.Cmd)       { cmd.Process.Signal(syscall.SIGTERM) }
func protectDirectory(path string) error { return os.Chmod(path, 0700) }
