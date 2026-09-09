package setupwizard

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"errors"
	"fmt"
	"io"
	"net"
	"net/http"
	"os"
	"os/signal"
	"path/filepath"
	"syscall"
	"time"

	"github.com/spf13/cobra"
)

// NewAppCommand serves the setup assistant through Home Assistant Ingress and
// keeps supervising the configured RTSP bridge after first-time setup.
func NewAppCommand() *cobra.Command {
	var dataDir, helper, listen string
	c := &cobra.Command{
		Use:   "app",
		Short: "Run as a Home Assistant app with an Ingress setup page",
		Args:  cobra.NoArgs,
		RunE: func(c *cobra.Command, args []string) error {
			if helper == "" {
				helper = helperPath()
			}
			absoluteData, err := filepath.Abs(dataDir)
			if err != nil {
				return errors.New("invalid data directory")
			}
			absoluteHelper, err := filepath.Abs(helper)
			if err != nil {
				return errors.New("invalid helper path")
			}
			return runApp(c.Context(), absoluteHelper, absoluteData, listen, c.OutOrStdout())
		},
	}
	c.Flags().StringVar(&dataDir, "data-dir", "/data/momcozy", "Private persistent configuration directory")
	c.Flags().StringVar(&helper, "helper", "", "Setup helper executable")
	c.Flags().StringVar(&listen, "listen", "0.0.0.0:8099", "Ingress listen address")
	return c
}

func runApp(parent context.Context, helper, dataDir, listen string, out io.Writer) error {
	listener, err := net.Listen("tcp", listen)
	if err != nil {
		return fmt.Errorf("start Ingress setup server: %w", err)
	}
	defer listener.Close()
	if err := os.MkdirAll(dataDir, 0o700); err != nil {
		return errors.New("cannot create private app data directory")
	}
	if err := os.Chmod(dataDir, 0o700); err != nil {
		return errors.New("cannot protect private app data directory")
	}
	nonce := make([]byte, 32)
	if _, err := rand.Read(nonce); err != nil {
		return err
	}
	ctx, stop := signal.NotifyContext(parent, os.Interrupt, syscall.SIGTERM)
	defer stop()
	s := &server{
		token: hex.EncodeToString(nonce), origin: "http://" + listener.Addr().String(),
		helper: helper, dataDir: dataDir, appMode: true, parent: ctx, out: out,
		cancel: stop, oauthProxy: newOAuthBrowserProxy(),
	}
	if commandForDir(dataDir) == "desktop" {
		s.readyDir = dataDir
		s.readyMode = "ha"
		if err := s.startBridge(); err != nil {
			return err
		}
	}
	httpServer := &http.Server{
		Handler: s, BaseContext: func(net.Listener) context.Context { return ctx },
		ReadHeaderTimeout: 5 * time.Second, ReadTimeout: 20 * time.Minute, IdleTimeout: 30 * time.Second,
	}
	done := make(chan error, 1)
	go func() { done <- httpServer.Serve(listener) }()
	fmt.Fprintln(out, "Home Assistant Ingress setup is ready on", listener.Addr())
	select {
	case <-ctx.Done():
	case err = <-done:
		if !errors.Is(err, http.ErrServerClosed) {
			return err
		}
	}
	s.stopBridge()
	shutdown, cancel := context.WithTimeout(context.Background(), 3*time.Second)
	defer cancel()
	return httpServer.Shutdown(shutdown)
}
