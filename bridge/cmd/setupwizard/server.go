// Package setupwizard serves the first-run UI on an ephemeral loopback port.
package setupwizard

import (
	"bytes"
	"context"
	"crypto/rand"
	_ "embed"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"html/template"
	"io"
	"net"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"sync"
	"time"

	"avent-webrtc-bridge/cmd/desktop"
	"github.com/spf13/cobra"
)

//go:embed ui.html
var page string

type server struct {
	token, origin, helper, dataDir string
	busy                           sync.Mutex
	cancel                         context.CancelFunc
	readyDir, readyMode            string
	launch                         bool
}

func helperPath() string {
	exe, _ := os.Executable()
	name := "momcozy-setup-helper"
	if runtime.GOOS == "windows" {
		name += ".exe"
	}
	return filepath.Join(filepath.Dir(exe), "setup-helper", name)
}

func NewCommand() *cobra.Command {
	home, _ := os.UserHomeDir()
	dir := os.Getenv("MOMCOZY_DATA_DIR")
	if dir == "" {
		dir = filepath.Join(home, ".momcozy-desktop")
	}
	var helper string
	var noBrowser bool
	c := &cobra.Command{Use: "setup", Short: "Open the local first-time camera setup assistant", Args: cobra.NoArgs,
		RunE: func(c *cobra.Command, args []string) error {
			if helper == "" {
				helper = helperPath()
			}
			dir, err := filepath.Abs(dir)
			if err != nil {
				return err
			}
			helper, err = filepath.Abs(helper)
			if err != nil {
				return err
			}
			return run(c.Context(), helper, dir, noBrowser, c.OutOrStdout())
		}}
	c.Flags().StringVar(&dir, "data-dir", dir, "Private configuration directory")
	c.Flags().StringVar(&helper, "helper", "", "Setup helper executable (normally bundled)")
	c.Flags().BoolVar(&noBrowser, "no-browser", false, "Print the local setup URL without opening a browser")
	return c
}

func run(parent context.Context, helper, dataDir string, noBrowser bool, out io.Writer) error {
	listener, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		return err
	}
	defer listener.Close()
	nonce := make([]byte, 32)
	if _, err = rand.Read(nonce); err != nil {
		return err
	}
	ctx, cancel := context.WithTimeout(parent, 30*time.Minute)
	defer cancel()
	s := &server{token: hex.EncodeToString(nonce), origin: "http://" + listener.Addr().String(), helper: helper, dataDir: dataDir, cancel: cancel}
	httpServer := &http.Server{Handler: s, BaseContext: func(net.Listener) context.Context { return ctx }, ReadHeaderTimeout: 5 * time.Second, ReadTimeout: 15 * time.Second, IdleTimeout: 30 * time.Second}
	done := make(chan error, 1)
	go func() { done <- httpServer.Serve(listener) }()
	url := s.origin + "/" + s.token + "/"
	fmt.Fprintln(out, "Open camera setup:", url)
	if !noBrowser {
		if err := openBrowser(url); err != nil {
			fmt.Fprintln(out, "Open the URL above in your browser.")
		}
	}
	select {
	case <-ctx.Done():
	case err = <-done:
		if !errors.Is(err, http.ErrServerClosed) {
			return err
		}
	}
	shutdown, stop := context.WithTimeout(context.Background(), 2*time.Second)
	defer stop()
	err = httpServer.Shutdown(shutdown)
	s.busy.Lock()
	launch, readyDir, readyMode := s.launch, s.readyDir, s.readyMode
	s.busy.Unlock()
	if launch {
		c := desktop.NewCommand()
		args := []string{"--data-dir", readyDir}
		if readyMode == "ha" {
			args = append(args, "--no-player")
		}
		c.SetArgs(args)
		c.SetOut(out)
		c.SetErr(out)
		return c.ExecuteContext(parent)
	}
	return err
}

func (s *server) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Cache-Control", "no-store")
	w.Header().Set("X-Content-Type-Options", "nosniff")
	w.Header().Set("Referrer-Policy", "no-referrer")
	w.Header().Set("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'self'; img-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'")
	if r.Host != strings.TrimPrefix(s.origin, "http://") {
		http.Error(w, "Invalid host", http.StatusForbidden)
		return
	}
	base := "/" + s.token + "/"
	if r.URL.Path == base && r.Method == http.MethodGet {
		w.Header().Set("Content-Type", "text/html; charset=utf-8")
		t := template.Must(template.New("setup").Parse(page))
		_ = t.Execute(w, struct{ Token, DataDir string }{s.token, s.dataDir})
		return
	}
	if r.URL.Path != base+"api" {
		http.NotFound(w, r)
		return
	}
	if r.Method != http.MethodPost {
		http.Error(w, "POST required", 405)
		return
	}
	if r.Header.Get("Origin") != s.origin || r.Header.Get("X-Setup-Token") != s.token || !strings.HasPrefix(r.Header.Get("Content-Type"), "application/json") {
		http.Error(w, "Invalid setup request", 403)
		return
	}
	if !s.busy.TryLock() {
		http.Error(w, "Setup is busy", 409)
		return
	}
	defer s.busy.Unlock()
	r.Body = http.MaxBytesReader(w, r.Body, 1<<20)
	var input map[string]any
	if json.NewDecoder(r.Body).Decode(&input) != nil || input == nil {
		http.Error(w, "Invalid JSON", 400)
		return
	}
	command, _ := input["command"].(string)
	if command == "close" {
		writeJSON(w, map[string]any{"ok": true})
		go s.cancel()
		return
	}
	if command == "launch" {
		if s.readyDir == "" {
			writeJSON(w, map[string]any{"ok": false, "message": "Complete setup first."})
			return
		}
		s.launch = true
		writeJSON(w, map[string]any{"ok": true})
		go s.cancel()
		return
	}
	if dir, ok := input["dataDir"].(string); !ok || strings.TrimSpace(dir) == "" {
		input["dataDir"] = s.dataDir
	}
	if command == "installAdb" {
		writeJSON(w, installAdb(r.Context(), input["dataDir"].(string)))
		return
	}
	switch command {
	case "discover", "prepareAndroid", "prepareApks", "preparePlay", "prepareCached", "importSigning", "importConfig", "configure":
	default:
		http.Error(w, "Unknown action", 400)
		return
	}
	if command == "discover" || command == "prepareAndroid" {
		if path, _ := input["adbPath"].(string); path == "" {
			input["adbPath"] = findAdb(input["dataDir"].(string))
		}
	}
	ctx, cancel := context.WithTimeout(r.Context(), 20*time.Minute)
	defer cancel()
	result := invokeHelper(ctx, s.helper, input)
	if ok, _ := result["ok"].(bool); ok && (command == "configure" || command == "importConfig") {
		s.readyDir, _ = result["dataDir"].(string)
		s.readyMode, _ = input["targetMode"].(string)
	}
	writeJSON(w, result)
}

func writeJSON(w http.ResponseWriter, value any) {
	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(value)
}

type limitedBuffer struct {
	bytes.Buffer
	overflow bool
}

func (b *limitedBuffer) Write(p []byte) (int, error) {
	if b.Len()+len(p) > 1<<20 {
		b.overflow = true
		return 0, errors.New("helper output limit")
	}
	return b.Buffer.Write(p)
}

func invokeHelper(ctx context.Context, path string, input map[string]any) map[string]any {
	fail := func(code, message string) map[string]any {
		return map[string]any{"ok": false, "error": code, "message": message}
	}
	if _, err := os.Stat(path); err != nil {
		return fail("helper_missing", "The setup helper is missing. Extract the complete setup bundle, including its setup-helper folder.")
	}
	payload, err := json.Marshal(input)
	if err != nil {
		return fail("invalid_request", "Invalid setup request.")
	}
	process := exec.CommandContext(ctx, path)
	process.WaitDelay = 2 * time.Second
	configureHelper(process)
	process.Stdin = bytes.NewReader(payload)
	var output limitedBuffer
	process.Stdout = &output
	process.Stderr = io.Discard
	if process.Start() != nil {
		return fail("helper_failed", "The setup helper could not start.")
	}
	cleanup, err := attachHelper(process)
	if err != nil {
		_ = process.Process.Kill()
		_ = process.Wait()
		return fail("helper_failed", "Cannot supervise the setup helper.")
	}
	defer cleanup()
	if process.Wait() != nil || output.overflow {
		return fail("helper_failed", "Setup could not finish. Check your files, app version and connection.")
	}
	var result map[string]any
	if json.Unmarshal(output.Bytes(), &result) != nil {
		return fail("helper_failed", "The setup helper returned an invalid response.")
	}
	return result
}
