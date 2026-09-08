// Package desktop supervises local camera bridges without a Python runtime.
package desktop

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net"
	"os"
	"os/exec"
	"os/signal"
	"path/filepath"
	"regexp"
	"strconv"
	"syscall"
	"time"

	"github.com/spf13/cobra"
)

type camera struct {
	config, name, host string
	authenticated      bool
	port               int
}

var cameraName = regexp.MustCompile(`^bm04_[0-9]+$`)

func loadCameras(dir string) ([]camera, error) {
	dir, err := filepath.Abs(dir)
	if err != nil {
		return nil, errors.New("invalid data directory")
	}
	if resolved, e := filepath.EvalSymlinks(dir); e == nil {
		dir = resolved
	}
	var names []string
	data, err := os.ReadFile(filepath.Join(dir, "cameras.private.json"))
	if err == nil {
		if json.Unmarshal(data, &names) != nil {
			return nil, errors.New("invalid camera manifest")
		}
	} else if os.IsNotExist(err) {
		matches, _ := filepath.Glob(filepath.Join(dir, "bridge-*.private.json"))
		for _, p := range matches {
			names = append(names, filepath.Base(p))
		}
	} else {
		return nil, errors.New("cannot read camera manifest")
	}
	if len(names) == 0 {
		return nil, errors.New("no cameras configured; follow docs/BINARIES.md to prepare or import your private configuration")
	}
	result := []camera{}
	ports := map[int]bool{}
	seen := map[string]bool{}
	for _, name := range names {
		if filepath.Base(name) != name || filepath.Ext(name) != ".json" {
			return nil, errors.New("camera configurations must be JSON files inside the data directory")
		}
		path := filepath.Join(dir, name)
		resolved, err := filepath.EvalSymlinks(path)
		if err != nil || filepath.Dir(resolved) != dir {
			return nil, errors.New("camera configuration missing or outside the data directory")
		}
		contents, err := os.ReadFile(path)
		if err != nil {
			return nil, errors.New("cannot read camera configuration")
		}
		var config map[string]string
		if json.Unmarshal(contents, &config) != nil {
			return nil, errors.New("invalid camera configuration")
		}
		port, err := strconv.Atoi(config["port"])
		if err != nil || port < 1024 || port > 65535 || ports[port] || !cameraName.MatchString(config["camera-name"]) || seen[config["camera-name"]] {
			return nil, errors.New("camera names must be unique bm04_N values and ports unique between 1024 and 65535")
		}
		for _, key := range []string{"signing-key", "sid", "ecode", "partner", "app-key", "device-id", "camera-id"} {
			if config[key] == "" {
				return nil, errors.New("incomplete private configuration; renew the account configuration")
			}
		}
		ports[port] = true
		seen[config["camera-name"]] = true
		result = append(result, camera{config: path, name: config["camera-name"], host: config["listen-host"], authenticated: config["rtsp-user"] != "" || config["rtsp-password"] != "", port: port})
	}
	return result, nil
}

func findPlayer() string {
	candidates := []string{filepath.Join(os.Getenv("ProgramFiles"), "VideoLAN", "VLC", "vlc.exe"), filepath.Join(os.Getenv("ProgramFiles(x86)"), "VideoLAN", "VLC", "vlc.exe"), "/Applications/VLC.app/Contents/MacOS/VLC"}
	for _, p := range candidates {
		if info, err := os.Stat(p); err == nil && !info.IsDir() {
			return p
		}
	}
	p, _ := exec.LookPath("vlc")
	return p
}
func portReady(host string, port int) bool {
	if host == "" || host == "0.0.0.0" {
		host = "127.0.0.1"
	}
	if host == "::" {
		host = "::1"
	}
	c, e := net.DialTimeout("tcp", net.JoinHostPort(host, strconv.Itoa(port)), 200*time.Millisecond)
	if e != nil {
		return false
	}
	c.Close()
	return true
}

type child struct {
	cmd  *exec.Cmd
	done chan error
	log  *os.File
}

func startChild(exe string, cam camera, dir string) (*child, error) {
	runtimeDir := filepath.Join(dir, "runtime", cam.name)
	if os.MkdirAll(runtimeDir, 0700) != nil || protectDirectory(filepath.Dir(runtimeDir)) != nil || protectDirectory(runtimeDir) != nil {
		return nil, errors.New("cannot create private runtime directory")
	}
	log, err := os.OpenFile(filepath.Join(runtimeDir, "bridge.log"), os.O_CREATE|os.O_TRUNC|os.O_WRONLY, 0600)
	if err != nil {
		return nil, errors.New("cannot create private bridge log")
	}
	if err = log.Chmod(0600); err != nil {
		log.Close()
		return nil, errors.New("cannot protect private bridge log")
	}
	cmd := exec.Command(exe, cam.config)
	cmd.Dir = runtimeDir
	cmd.Stdout = log
	cmd.Stderr = log
	configureChild(cmd)
	if cmd.Start() != nil {
		log.Close()
		return nil, errors.New("cannot start camera bridge")
	}
	c := &child{cmd: cmd, done: make(chan error, 1), log: log}
	go func() { c.done <- cmd.Wait(); close(c.done) }()
	return c, nil
}
func (c *child) stop() {
	defer c.log.Close()
	select {
	case <-c.done:
		return
	default:
	}
	interruptChild(c.cmd)
	select {
	case <-c.done:
	case <-time.After(3 * time.Second):
		c.cmd.Process.Kill()
		<-c.done
	}
}
func waitReady(ctx context.Context, c *child, host string, port int, timeout time.Duration) error {
	timer := time.NewTimer(timeout)
	defer timer.Stop()
	ticker := time.NewTicker(150 * time.Millisecond)
	defer ticker.Stop()
	for {
		select {
		case <-ctx.Done():
			return ctx.Err()
		case <-c.done:
			return errors.New("camera bridge exited; renew the session or inspect private logs")
		case <-timer.C:
			return errors.New("camera startup timed out; inspect private logs")
		case <-ticker.C:
			if portReady(host, port) {
				return nil
			}
		}
	}
}
func run(ctx context.Context, dir string, noPlayer bool, seconds time.Duration, out io.Writer) error {
	cameras, err := loadCameras(dir)
	if err != nil {
		return err
	}
	for _, cam := range cameras {
		if !noPlayer && (cam.authenticated || (cam.host != "" && cam.host != "127.0.0.1" && cam.host != "::1")) {
			return errors.New("authenticated or LAN configurations require --no-player; enter RTSP credentials directly in your player")
		}
	}
	player := ""
	if !noPlayer {
		player = findPlayer()
		if player == "" {
			return errors.New("install VLC or use --no-player")
		}
	}
	for _, cam := range cameras {
		if portReady(cam.host, cam.port) {
			return fmt.Errorf("local port %d is in use; stop the other viewer first", cam.port)
		}
	}
	exe, err := os.Executable()
	if err != nil {
		return errors.New("cannot locate viewer executable")
	}
	children := []*child{}
	defer func() {
		for _, c := range children {
			c.stop()
		}
	}()
	for _, cam := range cameras {
		c, err := startChild(exe, cam, dir)
		if err != nil {
			return err
		}
		children = append(children, c)
		if err = waitReady(ctx, c, cam.host, cam.port, 45*time.Second); err != nil {
			if ctx.Err() != nil {
				return nil
			}
			return err
		}
		host := cam.host
		if host == "" || host == "0.0.0.0" {
			host = "127.0.0.1"
		}
		if host == "::" {
			host = "::1"
		}
		url := fmt.Sprintf("rtsp://%s/%s", net.JoinHostPort(host, strconv.Itoa(cam.port)), cam.name)
		fmt.Fprintf(out, "%s: %s\n", cam.name, url)
		if player != "" {
			p := exec.Command(player, "--no-one-instance", "--rtsp-tcp", "--network-caching=500", "--meta-title="+cam.name, url)
			if p.Start() != nil {
				return errors.New("cannot launch VLC; try --no-player")
			}
			go p.Wait()
		}
	}
	fmt.Fprintln(out, "Viewer running. Keep this window open; Ctrl+C stops the camera connections.")
	if seconds > 0 {
		var cancel context.CancelFunc
		ctx, cancel = context.WithTimeout(ctx, seconds)
		defer cancel()
	}
	ticker := time.NewTicker(500 * time.Millisecond)
	defer ticker.Stop()
	for {
		select {
		case <-ctx.Done():
			return nil
		case <-ticker.C:
			for _, c := range children {
				select {
				case <-c.done:
					return errors.New("a camera bridge stopped; inspect private logs and refresh the session if needed")
				default:
				}
			}
		}
	}
}

func NewCommand() *cobra.Command {
	home, _ := os.UserHomeDir()
	dir := os.Getenv("MOMCOZY_DATA_DIR")
	if dir == "" {
		dir = filepath.Join(home, ".momcozy-desktop")
	}
	var noPlayer bool
	var seconds int
	cmd := &cobra.Command{Use: "desktop", Short: "Open configured cameras in VLC (no Python required)", Args: cobra.NoArgs, RunE: func(cmd *cobra.Command, args []string) error {
		if seconds < 0 {
			return errors.New("--seconds cannot be negative")
		}
		absolute, err := filepath.Abs(dir)
		if err != nil {
			return errors.New("invalid data directory")
		}
		ctx, stop := signal.NotifyContext(cmd.Context(), os.Interrupt, syscall.SIGTERM)
		defer stop()
		err = run(ctx, absolute, noPlayer, time.Duration(seconds)*time.Second, cmd.OutOrStdout())
		if err != nil {
			fmt.Fprintln(cmd.ErrOrStderr(), "Desktop:", err)
		}
		return err
	}}
	cmd.Flags().StringVar(&dir, "data-dir", dir, "Private configuration directory")
	cmd.Flags().BoolVar(&noPlayer, "no-player", false, "Serve RTSP without launching VLC")
	cmd.Flags().IntVar(&seconds, "seconds", 0, "Stop after N seconds once cameras are ready (0: until Ctrl+C)")
	return cmd
}
