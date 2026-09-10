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
	"net/http/httputil"
	"net/url"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strconv"
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
	state                          sync.Mutex
	operation                      sync.Mutex
	operationCancel                context.CancelFunc
	operationDone                  chan struct{}
	cancel                         context.CancelFunc
	readyDir, readyMode            string
	launch                         bool
	appMode, bridgeRunning         bool
	parent                         context.Context
	bridgeCancel                   context.CancelFunc
	bridgeDone                     chan struct{}
	oauthProxy                     http.Handler
	out                            io.Writer
}

type pageData struct {
	Token, DataDir      string
	AppMode, Configured bool
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
	httpServer := &http.Server{Handler: s, BaseContext: func(net.Listener) context.Context { return ctx }, ReadHeaderTimeout: 5 * time.Second, ReadTimeout: 20 * time.Minute, IdleTimeout: 30 * time.Second}
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
	s.state.Lock()
	launch, readyDir, readyMode := s.launch, s.readyDir, s.readyMode
	s.state.Unlock()
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
	if s.appMode {
		remote, _, err := net.SplitHostPort(r.RemoteAddr)
		if err != nil || remote != "172.30.32.2" {
			http.Error(w, "Ingress access required", http.StatusForbidden)
			return
		}
	}
	if s.appMode && strings.HasPrefix(r.URL.Path, "/oauth-browser/") {
		if r.Method != http.MethodGet || s.oauthProxy == nil {
			http.Error(w, "OAuth browser unavailable", http.StatusServiceUnavailable)
			return
		}
		s.oauthProxy.ServeHTTP(w, r)
		return
	}
	frameAncestors := "'none'"
	if s.appMode {
		frameAncestors = "'self'"
	}
	w.Header().Set("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'self'; img-src 'self'; frame-src 'self'; base-uri 'none'; frame-ancestors "+frameAncestors+"; form-action 'none'")
	if !s.appMode && r.Host != strings.TrimPrefix(s.origin, "http://") {
		http.Error(w, "Invalid host", http.StatusForbidden)
		return
	}
	base := "/" + s.token + "/"
	if s.appMode {
		base = "/"
	}
	if r.URL.Path == base && r.Method == http.MethodGet {
		w.Header().Set("Content-Type", "text/html; charset=utf-8")
		t := template.Must(template.New("setup").Parse(page))
		s.state.Lock()
		configured := s.readyDir != ""
		s.state.Unlock()
		_ = t.Execute(w, pageData{Token: s.token, DataDir: s.dataDir, AppMode: s.appMode, Configured: configured})
		return
	}
	isAPI := r.URL.Path == base+"api"
	isUpload := r.URL.Path == base+"upload"
	if !isAPI && !isUpload {
		http.NotFound(w, r)
		return
	}
	if r.Method != http.MethodPost {
		http.Error(w, "POST required", 405)
		return
	}
	if (!s.appMode && r.Header.Get("Origin") != s.origin) || r.Header.Get("X-Setup-Token") != s.token {
		http.Error(w, "Invalid setup request", 403)
		return
	}
	contentType := r.Header.Get("Content-Type")
	if (isAPI && !strings.HasPrefix(contentType, "application/json")) || (isUpload && !strings.HasPrefix(contentType, "multipart/form-data")) {
		http.Error(w, "Invalid setup request", 403)
		return
	}
	if isUpload {
		ctx, finish, ok := s.beginOperation(r.Context())
		if !ok {
			writeBusy(w)
			return
		}
		defer finish()
		s.handleAPKUpload(ctx, w, r)
		return
	}
	r.Body = http.MaxBytesReader(w, r.Body, 1<<20)
	var input map[string]any
	if json.NewDecoder(r.Body).Decode(&input) != nil || input == nil {
		http.Error(w, "Invalid JSON", 400)
		return
	}
	command, _ := input["command"].(string)
	if command == "cancel" {
		cancelled := s.cancelOperation(r.Context())
		writeJSON(w, map[string]any{"ok": true, "cancelled": cancelled})
		return
	}
	ctx, finish, ok := s.beginOperation(r.Context())
	if !ok {
		writeBusy(w)
		return
	}
	defer finish()
	if command == "status" && s.appMode {
		cameras, err := cameraStatus(s.dataDir)
		if err != nil {
			writeJSON(w, map[string]any{"ok": false, "error": "invalid_config", "message": err.Error()})
			return
		}
		s.state.Lock()
		running := s.bridgeRunning
		s.state.Unlock()
		writeJSON(w, map[string]any{"ok": true, "running": running, "cameras": cameras})
		return
	}
	if command == "regenerateCredentials" && s.appMode {
		if err := s.stopBridgeAndWait(ctx); err != nil {
			writeJSON(w, map[string]any{"ok": false, "error": "bridge_stop", "message": "Die laufende Bridge konnte nicht rechtzeitig beendet werden."})
			return
		}
		cameras, err := regenerateRTSPCredentials(s.dataDir)
		if err != nil {
			_ = s.startBridge()
			writeJSON(w, map[string]any{"ok": false, "error": "credentials_update", "message": "Die RTSP-Zugangsdaten konnten nicht neu erzeugt werden."})
			return
		}
		if err := s.startBridge(); err != nil {
			writeJSON(w, map[string]any{"ok": false, "error": "bridge_start", "message": "Die Zugangsdaten wurden erneuert, aber die Bridge konnte nicht gestartet werden."})
			return
		}
		writeJSON(w, map[string]any{"ok": true, "running": true, "cameras": cameras})
		return
	}
	if command == "close" {
		if s.appMode {
			writeJSON(w, map[string]any{"ok": false, "message": "Stop the app from Home Assistant."})
			return
		}
		writeJSON(w, map[string]any{"ok": true})
		go s.cancel()
		return
	}
	if command == "launch" {
		s.state.Lock()
		if s.readyDir == "" {
			s.state.Unlock()
			writeJSON(w, map[string]any{"ok": false, "message": "Complete setup first."})
			return
		}
		if s.appMode {
			s.state.Unlock()
			if err := s.startBridge(); err != nil {
				writeJSON(w, map[string]any{"ok": false, "message": err.Error()})
				return
			}
			writeJSON(w, map[string]any{"ok": true})
			return
		}
		s.launch = true
		s.state.Unlock()
		writeJSON(w, map[string]any{"ok": true})
		go s.cancel()
		return
	}
	if s.appMode {
		input["dataDir"] = s.dataDir
		input["appCacheDir"] = filepath.Join(s.dataDir, "app-cache")
		input["targetMode"] = "ha"
		input["audioFormat"] = "aac"
		input["ffmpegPath"] = "/usr/bin/ffmpeg"
		input["basePort"] = 19554
		input["addonMode"] = true
	} else if dir, ok := input["dataDir"].(string); !ok || strings.TrimSpace(dir) == "" {
		input["dataDir"] = s.dataDir
	}
	switch command {
	case "preparePlay", "configure":
	default:
		http.Error(w, "Unknown action", 400)
		return
	}
	s.state.Lock()
	hadConfiguration := s.readyDir != ""
	s.state.Unlock()
	result := invokeHelper(ctx, s.helper, input)
	if ok, _ := result["ok"].(bool); ok && command == "configure" {
		s.state.Lock()
		s.readyDir, _ = result["dataDir"].(string)
		s.readyMode, _ = input["targetMode"].(string)
		s.state.Unlock()
		if s.appMode && hadConfiguration {
			if err := s.stopBridgeAndWait(ctx); err == nil {
				_ = s.startBridge()
			}
		}
	}
	writeJSON(w, result)
}

func newOAuthBrowserProxy() http.Handler {
	target := &url.URL{Scheme: "http", Host: "127.0.0.1:6080"}
	proxy := httputil.NewSingleHostReverseProxy(target)
	director := proxy.Director
	proxy.Director = func(r *http.Request) {
		director(r)
		r.URL.Path = strings.TrimPrefix(r.URL.Path, "/oauth-browser")
		if r.URL.Path == "" {
			r.URL.Path = "/"
		}
		r.Host = target.Host
	}
	proxy.ErrorHandler = func(w http.ResponseWriter, _ *http.Request, _ error) {
		http.Error(w, "OAuth browser unavailable", http.StatusServiceUnavailable)
	}
	return proxy
}

const maxAPKUploadBytes int64 = 1024 * 1024 * 1024

func writeBusy(w http.ResponseWriter) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusConflict)
	_ = json.NewEncoder(w).Encode(map[string]any{
		"ok": false, "error": "setup_busy",
		"message": "Another setup operation is still running.",
	})
}

func (s *server) beginOperation(parent context.Context) (context.Context, func(), bool) {
	s.operation.Lock()
	defer s.operation.Unlock()
	if s.operationDone != nil {
		return nil, nil, false
	}
	ctx, cancel := context.WithTimeout(parent, 20*time.Minute)
	done := make(chan struct{})
	s.operationCancel = cancel
	s.operationDone = done
	finish := func() {
		cancel()
		s.operation.Lock()
		if s.operationDone == done {
			s.operationCancel = nil
			s.operationDone = nil
			close(done)
		}
		s.operation.Unlock()
	}
	return ctx, finish, true
}

func (s *server) cancelOperation(ctx context.Context) bool {
	s.operation.Lock()
	cancel, done := s.operationCancel, s.operationDone
	s.operation.Unlock()
	if cancel == nil || done == nil {
		return false
	}
	cancel()
	select {
	case <-done:
		return true
	case <-ctx.Done():
		return false
	}
}

func (s *server) handleAPKUpload(ctx context.Context, w http.ResponseWriter, r *http.Request) {
	fail := func(code, message string) {
		writeJSON(w, map[string]any{"ok": false, "error": code, "message": message})
	}
	r.Body = http.MaxBytesReader(w, r.Body, maxAPKUploadBytes)
	bodyDone := make(chan struct{})
	defer close(bodyDone)
	go func() {
		select {
		case <-ctx.Done():
			_ = r.Body.Close()
		case <-bodyDone:
		}
	}()
	reader, err := r.MultipartReader()
	if err != nil {
		fail("apk_upload", "The APK upload could not be read.")
		return
	}
	uploadDir, err := os.MkdirTemp("", "momcozy-apk-upload-")
	if err != nil {
		fail("apk_upload", "The APK upload could not be stored temporarily.")
		return
	}
	defer os.RemoveAll(uploadDir)
	_ = os.Chmod(uploadDir, 0o700)

	input := map[string]any{"command": "prepareApks", "allowFallback": false}
	uploaded := map[string]string{}
	for {
		part, nextErr := reader.NextPart()
		if errors.Is(nextErr, io.EOF) {
			break
		}
		if nextErr != nil {
			fail("apk_upload", "The APK upload was interrupted.")
			return
		}
		name := part.FormName()
		if (name == "baseApk" || name == "arm64Apk") && part.FileName() != "" {
			if _, exists := uploaded[name]; exists {
				part.Close()
				fail("apk_upload", "Each APK may only be uploaded once.")
				return
			}
			path := filepath.Join(uploadDir, name+".apk")
			file, createErr := os.OpenFile(path, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0o600)
			if createErr != nil {
				part.Close()
				fail("apk_upload", "The APK upload could not be stored temporarily.")
				return
			}
			written, copyErr := io.Copy(file, part)
			closeErr := file.Close()
			part.Close()
			if copyErr != nil || closeErr != nil || written == 0 {
				fail("apk_upload", "Both APK files must be complete and non-empty.")
				return
			}
			uploaded[name] = path
			continue
		}
		value, readErr := io.ReadAll(io.LimitReader(part, 4097))
		part.Close()
		if readErr != nil || len(value) > 4096 {
			fail("invalid_request", "An upload field is invalid.")
			return
		}
		if name == "dataDir" {
			input[name] = strings.TrimSpace(string(value))
		} else if name == "replaceExisting" {
			input[name] = strings.TrimSpace(string(value)) == "true"
		}
	}
	if uploaded["baseApk"] == "" || uploaded["arm64Apk"] == "" {
		fail("apk_missing", "Select both the base APK and the ARM64 APK.")
		return
	}
	dataDir, _ := input["dataDir"].(string)
	if s.appMode || dataDir == "" {
		dataDir = s.dataDir
	}
	input["dataDir"] = dataDir
	input["appCacheDir"] = filepath.Join(dataDir, "app-cache")
	input["baseApk"] = uploaded["baseApk"]
	input["arm64Apk"] = uploaded["arm64Apk"]

	writeJSON(w, invokeHelper(ctx, s.helper, input))
}

func (s *server) startBridge() error {
	s.state.Lock()
	if s.bridgeRunning {
		s.state.Unlock()
		return nil
	}
	if s.readyDir == "" {
		s.state.Unlock()
		return errors.New("complete setup first")
	}
	ctx, cancel := context.WithCancel(s.parent)
	dir := s.readyDir
	done := make(chan struct{})
	s.bridgeCancel = cancel
	s.bridgeDone = done
	s.bridgeRunning = true
	s.state.Unlock()

	c := desktop.NewCommand()
	c.SetArgs([]string{"--data-dir", dir, "--no-player"})
	c.SetOut(s.out)
	c.SetErr(s.out)
	go func() {
		defer close(done)
		err := c.ExecuteContext(ctx)
		s.state.Lock()
		s.bridgeRunning = false
		s.bridgeCancel = nil
		if s.bridgeDone == done {
			s.bridgeDone = nil
		}
		s.state.Unlock()
		if err != nil && ctx.Err() == nil {
			fmt.Fprintln(s.out, "Home Assistant app bridge:", err)
		}
	}()
	return nil
}

func (s *server) stopBridge() {
	s.state.Lock()
	cancel := s.bridgeCancel
	s.state.Unlock()
	if cancel != nil {
		cancel()
	}
}

func (s *server) stopBridgeAndWait(ctx context.Context) error {
	s.state.Lock()
	cancel, done := s.bridgeCancel, s.bridgeDone
	s.state.Unlock()
	if cancel == nil || done == nil {
		return nil
	}
	cancel()
	select {
	case <-done:
		return nil
	case <-ctx.Done():
		return ctx.Err()
	}
}

type privateCameraConfig struct {
	name   string
	config map[string]string
}

func loadPrivateCameraConfigs(dir string) (string, []privateCameraConfig, error) {
	root, err := filepath.Abs(dir)
	if err != nil {
		return "", nil, errors.New("invalid private configuration directory")
	}
	manifest, err := os.ReadFile(filepath.Join(root, "cameras.private.json"))
	if err != nil {
		return "", nil, errors.New("camera configuration is not ready")
	}
	var names []string
	if json.Unmarshal(manifest, &names) != nil || len(names) == 0 {
		return "", nil, errors.New("camera manifest is invalid")
	}
	configs := make([]privateCameraConfig, 0, len(names))
	seen := make(map[string]bool, len(names))
	for _, name := range names {
		if filepath.Base(name) != name || !strings.HasPrefix(name, "bridge-") || !strings.HasSuffix(name, ".private.json") || seen[name] {
			return "", nil, errors.New("camera manifest is invalid")
		}
		seen[name] = true
		contents, err := os.ReadFile(filepath.Join(root, name))
		if err != nil {
			return "", nil, errors.New("camera configuration is incomplete")
		}
		var config map[string]string
		if json.Unmarshal(contents, &config) != nil {
			return "", nil, errors.New("camera configuration is invalid")
		}
		port, err := strconv.Atoi(config["port"])
		if err != nil || port < 1024 || port > 65535 || config["camera-name"] == "" || config["rtsp-user"] == "" || config["rtsp-password"] == "" {
			return "", nil, errors.New("camera configuration is incomplete")
		}
		configs = append(configs, privateCameraConfig{name: name, config: config})
	}
	return root, configs, nil
}

func regenerateRTSPCredentials(dir string) ([]map[string]any, error) {
	root, configs, err := loadPrivateCameraConfigs(dir)
	if err != nil {
		return nil, err
	}
	stage, err := os.MkdirTemp(root, ".rtsp-credentials-")
	if err != nil {
		return nil, errors.New("cannot stage RTSP credentials")
	}
	defer os.RemoveAll(stage)
	if err := os.Chmod(stage, 0o700); err != nil {
		return nil, errors.New("cannot protect staged RTSP credentials")
	}
	for _, item := range configs {
		secret := make([]byte, 24)
		if _, err := rand.Read(secret); err != nil {
			return nil, errors.New("cannot generate RTSP credentials")
		}
		item.config["rtsp-user"] = "homeassistant"
		item.config["rtsp-password"] = hex.EncodeToString(secret)
		encoded, err := json.Marshal(item.config)
		if err != nil {
			return nil, errors.New("cannot encode RTSP credentials")
		}
		if err := os.WriteFile(filepath.Join(stage, item.name), encoded, 0o600); err != nil {
			return nil, errors.New("cannot stage RTSP credentials")
		}
	}
	for _, item := range configs {
		if err := os.Rename(filepath.Join(stage, item.name), filepath.Join(root, item.name)); err != nil {
			return nil, errors.New("cannot publish RTSP credentials")
		}
	}
	return cameraStatus(root)
}

func cameraStatus(dir string) ([]map[string]any, error) {
	_, configs, err := loadPrivateCameraConfigs(dir)
	if err != nil {
		return nil, err
	}
	result := make([]map[string]any, 0, len(configs))
	for _, item := range configs {
		config := item.config
		port, _ := strconv.Atoi(config["port"])
		result = append(result, map[string]any{
			"name": config["camera-name"], "path": config["camera-name"], "port": port,
			"username": config["rtsp-user"], "password": config["rtsp-password"],
		})
	}
	return result, nil
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
	waitErr := process.Wait()
	if !output.overflow {
		var result map[string]any
		if json.Unmarshal(output.Bytes(), &result) == nil {
			return result
		}
	}
	if waitErr != nil {
		fmt.Fprintln(os.Stderr, "Momcozy setup helper ended unexpectedly:", waitErr)
		if errors.Is(ctx.Err(), context.DeadlineExceeded) {
			return fail("helper_timeout", "The setup helper timed out before it could return an error.")
		}
		if errors.Is(ctx.Err(), context.Canceled) {
			return fail("helper_cancelled", "The setup operation was cancelled.")
		}
		var exitErr *exec.ExitError
		if errors.As(waitErr, &exitErr) && exitErr.ExitCode() < 0 {
			return fail("helper_terminated", "The setup helper was terminated unexpectedly, usually because the system ran out of memory. Check the Home Assistant app log.")
		}
		return fail("helper_failed", "The setup helper stopped before it could return an error. Check the Home Assistant app log.")
	}
	if output.overflow {
		return fail("helper_failed", "The setup helper returned too much diagnostic output. Check the Home Assistant app log.")
	}
	var result map[string]any
	if json.Unmarshal(output.Bytes(), &result) != nil {
		return fail("helper_failed", "The setup helper returned an invalid response.")
	}
	return result
}
