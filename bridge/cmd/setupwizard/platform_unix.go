//go:build !windows

package setupwizard

import (
	"os/exec"
	"runtime"
	"syscall"
)

func configureHelper(c *exec.Cmd) { c.SysProcAttr = &syscall.SysProcAttr{Setpgid: true} }
func attachHelper(c *exec.Cmd) (func(), error) {
	return func() { _ = syscall.Kill(-c.Process.Pid, syscall.SIGKILL) }, nil
}
func openBrowser(url string) error {
	command := "xdg-open"
	if runtime.GOOS == "darwin" {
		command = "open"
	}
	return exec.Command(command, url).Run()
}
