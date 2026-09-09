package setupwizard

import (
	"archive/zip"
	"bytes"
	"context"
	"encoding/json"
	"mime/multipart"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
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

func TestPageOffersOnlyGooglePlayAndAPKUpload(t *testing.T) {
	s := &server{token: "abc", origin: "http://127.0.0.1:12345", dataDir: t.TempDir()}
	r := httptest.NewRequest(http.MethodGet, s.origin+"/abc/", nil)
	w := httptest.NewRecorder()
	s.ServeHTTP(w, r)
	body := w.Body.String()
	for _, removed := range []string{`value="android"`, `value="cached"`, `value="signing"`, `value="config"`} {
		if strings.Contains(body, removed) {
			t.Fatalf("obsolete setup method remains in page: %s", removed)
		}
	}
	for _, removed := range []string{`id="playEmail"`, `id="playToken"`, "AAS-Token"} {
		if strings.Contains(body, removed) {
			t.Fatalf("manual token login remains in page: %s", removed)
		}
	}
	for _, required := range []string{`value="play"`, `value="apks"`, `id="oauth-browser"`, `id="baseApk" type="file"`, `id="arm64Apk" type="file"`, `setup_busy`, `command:'cancel'`} {
		if !strings.Contains(body, required) {
			t.Fatalf("required setup control missing: %s", required)
		}
	}
}

func TestOAuthBrowserRequiresHomeAssistantIngress(t *testing.T) {
	proxied := false
	s := &server{
		token: "secret", appMode: true, dataDir: t.TempDir(),
		oauthProxy: http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			proxied = true
			_, _ = w.Write([]byte("browser"))
		}),
	}
	r := httptest.NewRequest(http.MethodGet, "http://app/oauth-browser/vnc.html", nil)
	r.RemoteAddr = "172.30.32.2:1234"
	w := httptest.NewRecorder()
	s.ServeHTTP(w, r)
	if w.Code != http.StatusOK || w.Body.String() != "browser" || !proxied {
		t.Fatalf("authenticated Ingress did not reach OAuth browser: %d %q", w.Code, w.Body.String())
	}

	proxied = false
	r = httptest.NewRequest(http.MethodGet, "http://app/oauth-browser/vnc.html", nil)
	r.RemoteAddr = "172.30.33.4:1234"
	w = httptest.NewRecorder()
	s.ServeHTTP(w, r)
	if w.Code != http.StatusForbidden || proxied {
		t.Fatalf("non-Ingress request reached OAuth browser: %d", w.Code)
	}
}

func TestAPKUploadRequiresBothFiles(t *testing.T) {
	helperDir := t.TempDir()
	helper := filepath.Join(helperDir, "helper")
	if err := os.WriteFile(helper, []byte("#!/bin/sh\nprintf '{\"ok\":true,\"prepared\":true}'\n"), 0o700); err != nil {
		t.Fatal(err)
	}
	s := &server{token: "secret", origin: "http://127.0.0.1:12345", dataDir: t.TempDir(), helper: helper}

	upload := func(includeArm64 bool) *httptest.ResponseRecorder {
		var body bytes.Buffer
		form := multipart.NewWriter(&body)
		_ = form.WriteField("dataDir", s.dataDir)
		base, _ := form.CreateFormFile("baseApk", "base.apk")
		_, _ = base.Write([]byte("base fixture"))
		if includeArm64 {
			arm64, _ := form.CreateFormFile("arm64Apk", "split_config.arm64_v8a.apk")
			_, _ = arm64.Write([]byte("arm64 fixture"))
		}
		_ = form.Close()
		r := httptest.NewRequest(http.MethodPost, s.origin+"/secret/upload", &body)
		r.Header.Set("Origin", s.origin)
		r.Header.Set("X-Setup-Token", s.token)
		r.Header.Set("Content-Type", form.FormDataContentType())
		w := httptest.NewRecorder()
		s.ServeHTTP(w, r)
		return w
	}

	if w := upload(false); w.Code != http.StatusOK || !strings.Contains(w.Body.String(), `"error":"apk_missing"`) {
		t.Fatalf("missing ARM64 APK was not rejected: %d %s", w.Code, w.Body.String())
	}
	if w := upload(true); w.Code != http.StatusOK || !strings.Contains(w.Body.String(), `"prepared":true`) {
		t.Fatalf("complete APK upload failed: %d %s", w.Code, w.Body.String())
	}
}

func TestBusyAPKPreparationCanBeCancelledAndRetried(t *testing.T) {
	helperDir := t.TempDir()
	marker := filepath.Join(helperDir, "first-started")
	helper := filepath.Join(helperDir, "helper")
	script := "#!/bin/sh\n" +
		"if [ ! -e '" + marker + "' ]; then\n" +
		"  : > '" + marker + "'\n" +
		"  while :; do sleep 1; done\n" +
		"fi\n" +
		"printf '{\"ok\":true,\"prepared\":true}'\n"
	if err := os.WriteFile(helper, []byte(script), 0o700); err != nil {
		t.Fatal(err)
	}
	s := &server{token: "secret", origin: "http://127.0.0.1:12345", dataDir: t.TempDir(), helper: helper}

	upload := func() *httptest.ResponseRecorder {
		var body bytes.Buffer
		form := multipart.NewWriter(&body)
		base, _ := form.CreateFormFile("baseApk", "base.apk")
		_, _ = base.Write([]byte("base fixture"))
		arm64, _ := form.CreateFormFile("arm64Apk", "split_config.arm64_v8a.apk")
		_, _ = arm64.Write([]byte("arm64 fixture"))
		_ = form.Close()
		r := httptest.NewRequest(http.MethodPost, s.origin+"/secret/upload", &body)
		r.Header.Set("Origin", s.origin)
		r.Header.Set("X-Setup-Token", s.token)
		r.Header.Set("Content-Type", form.FormDataContentType())
		w := httptest.NewRecorder()
		s.ServeHTTP(w, r)
		return w
	}

	firstDone := make(chan *httptest.ResponseRecorder, 1)
	go func() { firstDone <- upload() }()
	deadline := time.Now().Add(2 * time.Second)
	for {
		if _, err := os.Stat(marker); err == nil {
			break
		}
		if time.Now().After(deadline) {
			t.Fatal("blocking helper did not start")
		}
		time.Sleep(10 * time.Millisecond)
	}

	cancelRequest := httptest.NewRequest(http.MethodPost, s.origin+"/secret/api", strings.NewReader(`{"command":"cancel"}`))
	cancelRequest.Header.Set("Origin", s.origin)
	cancelRequest.Header.Set("X-Setup-Token", s.token)
	cancelRequest.Header.Set("Content-Type", "application/json")
	cancelResponse := httptest.NewRecorder()
	s.ServeHTTP(cancelResponse, cancelRequest)
	if cancelResponse.Code != http.StatusOK || !strings.Contains(cancelResponse.Body.String(), `"ok":true`) {
		t.Fatalf("active preparation could not be cancelled: %d %s", cancelResponse.Code, cancelResponse.Body.String())
	}

	select {
	case <-firstDone:
	case <-time.After(2 * time.Second):
		t.Fatal("cancelled preparation did not stop")
	}
	if retry := upload(); retry.Code != http.StatusOK || !strings.Contains(retry.Body.String(), `"prepared":true`) {
		t.Fatalf("retry after cancellation failed: %d %s", retry.Code, retry.Body.String())
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

func TestHelperJSONErrorSurvivesNonzeroExit(t *testing.T) {
	helper := filepath.Join(t.TempDir(), "helper")
	script := "#!/bin/sh\nprintf '{\"ok\":false,\"error\":\"play_auth\",\"message\":\"Google rejected the completed sign-in.\"}'\nexit 1\n"
	if err := os.WriteFile(helper, []byte(script), 0o700); err != nil {
		t.Fatal(err)
	}
	result := invokeHelper(context.Background(), helper, map[string]any{"command": "preparePlay"})
	if result["error"] != "play_auth" || result["message"] != "Google rejected the completed sign-in." {
		t.Fatalf("helper error was replaced by a generic process error: %#v", result)
	}
}

func TestKilledHelperReportsTerminationInsteadOfGenericSetupFailure(t *testing.T) {
	helper := filepath.Join(t.TempDir(), "helper")
	if err := os.WriteFile(helper, []byte("#!/bin/sh\nkill -KILL $$\n"), 0o700); err != nil {
		t.Fatal(err)
	}
	result := invokeHelper(context.Background(), helper, map[string]any{"command": "preparePlay"})
	if result["error"] != "helper_terminated" {
		t.Fatalf("terminated helper was not identified: %#v", result)
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
