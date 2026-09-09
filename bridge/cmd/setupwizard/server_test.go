package setupwizard

import (
	"archive/zip"
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestFirstRunPreservesExistingConfigurations(t *testing.T) {
	dir := t.TempDir()
	if commandForDir(dir) != "setup" {
		t.Fatal("fresh directory should open setup")
	}
	path := filepath.Join(dir, "bridge-1.private.json")
	os.WriteFile(path, []byte("damaged"), 0600)
	if commandForDir(dir) != "desktop" {
		t.Fatal("must not replace a damaged existing configuration")
	}
	os.Remove(path)
	os.WriteFile(filepath.Join(dir, "cameras.private.json"), []byte("[]"), 0600)
	if commandForDir(dir) != "desktop" {
		t.Fatal("manifest must preserve desktop validation")
	}
}
func TestBrowserBoundary(t *testing.T) {
	s := &server{token: "secret", origin: "http://127.0.0.1:12345", dataDir: t.TempDir(), cancel: func() {}}
	for _, tc := range []struct {
		name, host, origin, token string
		want                      int
	}{
		{"valid", "127.0.0.1:12345", s.origin, s.token, 200},
		{"rebind", "attacker.example:12345", s.origin, s.token, 403},
		{"crossOrigin", "127.0.0.1:12345", "https://attacker.example", s.token, 403},
		{"missingOrigin", "127.0.0.1:12345", "", s.token, 403},
		{"missingToken", "127.0.0.1:12345", s.origin, "", 403},
	} {
		t.Run(tc.name, func(t *testing.T) {
			r := httptest.NewRequest(http.MethodPost, s.origin+"/secret/api", strings.NewReader(`{"command":"close"}`))
			r.Host = tc.host
			r.Header.Set("Origin", tc.origin)
			r.Header.Set("X-Setup-Token", tc.token)
			r.Header.Set("Content-Type", "application/json")
			w := httptest.NewRecorder()
			s.ServeHTTP(w, r)
			if w.Code != tc.want {
				t.Fatalf("got %d", w.Code)
			}
		})
	}
}
func TestPageEscapesPrivateDirectory(t *testing.T) {
	s := &server{token: "abc", origin: "http://127.0.0.1:12345", dataDir: `C:\a"><script>bad()</script>`}
	r := httptest.NewRequest("GET", s.origin+"/abc/", nil)
	w := httptest.NewRecorder()
	s.ServeHTTP(w, r)
	if w.Code != 200 || strings.Contains(w.Body.String(), "<script>bad()") || !strings.Contains(w.Body.String(), `const token="abc"`) {
		t.Fatal("template context escaping failed")
	}
}
func TestAppModeRequiresIngressAndToken(t *testing.T) {
	s := &server{token: "secret", appMode: true, dataDir: t.TempDir(), parent: context.Background(), out: os.Stdout}
	for _, tc := range []struct {
		name, remote, token string
		want                int
	}{
		{"ingress page", "172.30.32.2:1234", "", 200},
		{"other container", "172.30.33.4:1234", "", 403},
		{"ingress missing token", "172.30.32.2:1234", "", 403},
		{"ingress api", "172.30.32.2:1234", "secret", 200},
	} {
		t.Run(tc.name, func(t *testing.T) {
			method, path, body := http.MethodGet, "/", ""
			if strings.Contains(tc.name, "token") || strings.Contains(tc.name, "api") {
				method, path, body = http.MethodPost, "/api", `{"command":"status"}`
			}
			r := httptest.NewRequest(method, "http://app"+path, strings.NewReader(body))
			r.RemoteAddr = tc.remote
			r.Header.Set("X-Setup-Token", tc.token)
			if method == http.MethodPost {
				r.Header.Set("Content-Type", "application/json")
			}
			w := httptest.NewRecorder()
			s.ServeHTTP(w, r)
			if w.Code != tc.want {
				t.Fatalf("got %d, want %d", w.Code, tc.want)
			}
		})
	}
}

func TestCameraStatusReturnsOnlyLocalRTSPConnection(t *testing.T) {
	dir := t.TempDir()
	os.WriteFile(filepath.Join(dir, "cameras.private.json"), []byte(`["bridge-1.private.json"]`), 0o600)
	os.WriteFile(filepath.Join(dir, "bridge-1.private.json"), []byte(`{
		"camera-name":"bm04_1", "port":"19554", "rtsp-user":"homeassistant",
		"rtsp-password":"private-rtsp-password", "sid":"cloud-secret"
	}`), 0o600)
	cameras, err := cameraStatus(dir)
	if err != nil || len(cameras) != 1 {
		t.Fatalf("cameraStatus: %v, %+v", err, cameras)
	}
	encoded, _ := json.Marshal(cameras)
	if !strings.Contains(string(encoded), "private-rtsp-password") || strings.Contains(string(encoded), "cloud-secret") {
		t.Fatalf("unexpected status payload: %s", encoded)
	}
}
func TestHelperFailureDoesNotExposePath(t *testing.T) {
	result := invokeHelper(context.Background(), filepath.Join(t.TempDir(), "private-secret.exe"), nil)
	data, _ := json.Marshal(result)
	if strings.Contains(string(data), "private-secret") {
		t.Fatal("leaked private path")
	}
	if result["error"] != "helper_missing" {
		t.Fatal(result)
	}
}
func TestRejectArchiveTraversal(t *testing.T) {
	for _, name := range []string{"platform-tools/../../escape", `platform-tools\..\escape`, "/platform-tools/adb", "platform-tools/a:stream"} {
		t.Run(name, func(t *testing.T) {
			dir := t.TempDir()
			archive := filepath.Join(dir, "a.zip")
			f, _ := os.Create(archive)
			z := zip.NewWriter(f)
			w, _ := z.Create(name)
			w.Write([]byte("x"))
			z.Close()
			f.Close()
			if extractTools(archive, filepath.Join(dir, "out")) == nil {
				t.Fatal("accepted unsafe path")
			}
		})
	}
}
func TestExtractTools(t *testing.T) {
	dir := t.TempDir()
	archive := filepath.Join(dir, "a.zip")
	f, _ := os.Create(archive)
	z := zip.NewWriter(f)
	w, _ := z.Create("platform-tools/adb")
	w.Write([]byte("test"))
	z.Close()
	f.Close()
	out := filepath.Join(dir, "out")
	if err := extractTools(archive, out); err != nil {
		t.Fatal(err)
	}
	b, err := os.ReadFile(filepath.Join(out, "platform-tools", "adb"))
	if err != nil || string(b) != "test" {
		t.Fatal("valid tools extraction failed")
	}
}
