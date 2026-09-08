//go:build !windows

package rtsp

import "syscall"

// reuseAddrControl sets SO_REUSEADDR on the listening socket so the bridge can
// re-bind its fixed port immediately after a restart, even while connections
// from the previous instance linger in TIME_WAIT. Without it the add-on crashes
// with "address already in use" on restart (issue #43).
func reuseAddrControl(network, address string, c syscall.RawConn) error {
	var sockErr error
	if err := c.Control(func(fd uintptr) {
		sockErr = syscall.SetsockoptInt(int(fd), syscall.SOL_SOCKET, syscall.SO_REUSEADDR, 1)
	}); err != nil {
		return err
	}
	return sockErr
}
