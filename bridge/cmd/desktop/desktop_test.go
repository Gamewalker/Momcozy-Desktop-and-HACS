package desktop

import (
	"context"
	"encoding/json"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

func fixture(t *testing.T, dir, name, port string) {
	t.Helper()
	data := map[string]string{"port": port, "camera-name": name}
	for _, key := range []string{"signing-key", "sid", "ecode", "partner", "app-key", "device-id", "camera-id"} {
		data[key] = "TEST-SECRET"
	}
	b, _ := json.Marshal(data)
	if err := os.WriteFile(filepath.Join(dir, "bridge-"+name+".private.json"), b, 0600); err != nil {
		t.Fatal(err)
	}
}
func TestLoadCameras(t *testing.T) {
	dir := t.TempDir()
	fixture(t, dir, "bm04_1", "18554")
	fixture(t, dir, "bm04_2", "18555")
	cams, err := loadCameras(dir)
	if err != nil || len(cams) != 2 {
		t.Fatalf("load: %v count %d", err, len(cams))
	}
	fixture(t, dir, "bm04_2", "18554")
	if _, err := loadCameras(dir); err == nil {
		t.Fatal("duplicate port accepted")
	}
}
func TestManifestTraversal(t *testing.T) {
	dir := t.TempDir()
	os.WriteFile(filepath.Join(dir, "cameras.private.json"), []byte(`["../secret.json"]`), 0600)
	if _, err := loadCameras(dir); err == nil {
		t.Fatal("path traversal accepted")
	}
}
func TestMalformedConfigDoesNotLeak(t *testing.T) {
	dir := t.TempDir()
	os.WriteFile(filepath.Join(dir, "bridge-1.private.json"), []byte(`{"password":"TEST-SECRET"`), 0600)
	_, err := loadCameras(dir)
	if err == nil || strings.Contains(err.Error(), "TEST-SECRET") {
		t.Fatal("malformed input leaked or accepted")
	}
}
func TestWaitReadyDetectsExitAndCancellation(t *testing.T) {
	done := make(chan error, 1)
	done <- nil
	c := &child{done: done}
	if err := waitReady(context.Background(), c, "127.0.0.1", 1, time.Second); err == nil {
		t.Fatal("exit ignored")
	}
	ctx, cancel := context.WithCancel(context.Background())
	cancel()
	if err := waitReady(ctx, &child{done: make(chan error)}, "127.0.0.1", 1, time.Second); err != context.Canceled {
		t.Fatalf("cancel: %v", err)
	}
}
func TestSupervisorStopsOnlyItsChild(t *testing.T) {
	if os.Getenv("MOMCOZY_TEST_CHILD") == "1" {
		time.Sleep(time.Minute)
		os.Exit(0)
	}
	cmd := exec.Command(os.Args[0], "-test.run=TestSupervisorStopsOnlyItsChild")
	cmd.Env = append(os.Environ(), "MOMCOZY_TEST_CHILD=1")
	configureChild(cmd)
	if err := cmd.Start(); err != nil {
		t.Fatal(err)
	}
	log, err := os.CreateTemp(t.TempDir(), "log")
	if err != nil {
		t.Fatal(err)
	}
	c := &child{cmd: cmd, done: make(chan error, 1), log: log}
	go func() { c.done <- cmd.Wait(); close(c.done) }()
	c.stop()
	if cmd.ProcessState == nil {
		t.Fatal("child not reaped")
	}
	c.stop()
}
func TestAuthenticatedViewerRequiresManualPlayer(t *testing.T) {
	dir := t.TempDir()
	fixture(t, dir, "bm04_1", "18554")
	p := filepath.Join(dir, "bridge-bm04_1.private.json")
	b, _ := os.ReadFile(p)
	var config map[string]string
	json.Unmarshal(b, &config)
	config["rtsp-user"] = "private-user"
	config["rtsp-password"] = "TEST-SECRET"
	b, _ = json.Marshal(config)
	os.WriteFile(p, b, 0600)
	var output strings.Builder
	err := run(context.Background(), dir, false, 0, &output)
	if err == nil || !strings.Contains(err.Error(), "--no-player") || strings.Contains(err.Error(), "TEST-SECRET") {
		t.Fatalf("authentication guard: %v", err)
	}
}
func TestProtectRuntimeDirectory(t *testing.T) {
	dir := t.TempDir()
	if err := protectDirectory(dir); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(dir, "probe"), []byte("test"), 0600); err != nil {
		t.Fatal(err)
	}
}
