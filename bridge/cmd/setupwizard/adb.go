package setupwizard

import (
	"archive/zip"
	"context"
	"errors"
	"io"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"time"
)

func adbName() string {
	if runtime.GOOS == "windows" {
		return "adb.exe"
	}
	return "adb"
}
func findAdb(dir string) string {
	if p, err := exec.LookPath("adb"); err == nil {
		return p
	}
	p := filepath.Join(dir, "tools", "platform-tools", adbName())
	if info, err := os.Stat(p); err == nil && !info.IsDir() {
		return p
	}
	return ""
}

// Google distributes desktop platform-tools separately; no vendor APK or SDK
// signing material is included. Linux ARM64 users can select distro-provided adb.
func installAdb(ctx context.Context, dir string) map[string]any {
	fail := func(message string) map[string]any { return map[string]any{"ok": false, "message": message} }
	if runtime.GOOS == "linux" && runtime.GOARCH != "amd64" {
		return fail("Install adb from your Linux distribution and select its path.")
	}
	platform := runtime.GOOS
	if platform != "windows" && platform != "darwin" && platform != "linux" {
		return fail("Automatic Android tools download is unavailable on this platform.")
	}
	dir, err := filepath.Abs(dir)
	if err != nil {
		return fail("Invalid configuration directory.")
	}
	if p := findAdb(dir); p != "" {
		return map[string]any{"ok": true, "adbPath": p}
	}
	toolsDir := filepath.Join(dir, "tools")
	if os.MkdirAll(toolsDir, 0700) != nil {
		return fail("Cannot create the tools directory.")
	}
	stage, err := os.MkdirTemp(toolsDir, ".download-")
	if err != nil {
		return fail("Cannot create download directory.")
	}
	defer os.RemoveAll(stage)
	ctx, cancel := context.WithTimeout(ctx, 5*time.Minute)
	defer cancel()
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, "https://dl.google.com/android/repository/platform-tools-latest-"+platform+".zip", nil)
	if err != nil {
		return fail("Cannot prepare Android tools download.")
	}
	client := &http.Client{CheckRedirect: func(r *http.Request, via []*http.Request) error {
		if len(via) > 3 || r.URL.Scheme != "https" || r.URL.Host != "dl.google.com" {
			return errors.New("unexpected download redirect")
		}
		return nil
	}}
	response, err := client.Do(req)
	if err != nil {
		return fail("Android tools download failed. Check your Internet connection.")
	}
	defer response.Body.Close()
	if response.StatusCode != 200 {
		return fail("Google did not return the Android tools archive.")
	}
	archive := filepath.Join(stage, "tools.zip")
	file, err := os.OpenFile(archive, os.O_CREATE|os.O_EXCL|os.O_WRONLY, 0600)
	if err != nil {
		return fail("Cannot save Android tools.")
	}
	n, err := io.Copy(file, io.LimitReader(response.Body, (256<<20)+1))
	closeErr := file.Close()
	if err != nil || closeErr != nil || n > 256<<20 {
		return fail("Android tools download was incomplete or too large.")
	}
	if extractTools(archive, stage) != nil {
		return fail("Android tools archive validation failed.")
	}
	extracted := filepath.Join(stage, "platform-tools")
	info, err := os.Stat(filepath.Join(extracted, adbName()))
	if err != nil || info.IsDir() {
		return fail("Android tools archive has no adb executable.")
	}
	destination := filepath.Join(toolsDir, "platform-tools")
	if os.Rename(extracted, destination) != nil {
		return fail("Cannot install Android tools; check the destination folder.")
	}
	return map[string]any{"ok": true, "adbPath": filepath.Join(destination, adbName())}
}

func extractTools(archive, destination string) error {
	reader, err := zip.OpenReader(archive)
	if err != nil {
		return err
	}
	defer reader.Close()
	var total uint64
	for _, entry := range reader.File {
		name := entry.Name
		if strings.Contains(name, "\\") || !strings.HasPrefix(name, "platform-tools/") || strings.Contains(name, ":") || entry.Mode()&os.ModeSymlink != 0 {
			return errors.New("unsafe archive path")
		}
		clean := filepath.Clean(filepath.FromSlash(name))
		if clean != "platform-tools" && !strings.HasPrefix(clean, "platform-tools"+string(os.PathSeparator)) {
			return errors.New("unsafe archive path")
		}
		total += entry.UncompressedSize64
		if total > 512<<20 {
			return errors.New("archive too large")
		}
		target := filepath.Join(destination, clean)
		if entry.FileInfo().IsDir() {
			if err := os.MkdirAll(target, 0700); err != nil {
				return err
			}
			continue
		}
		if err := os.MkdirAll(filepath.Dir(target), 0700); err != nil {
			return err
		}
		source, err := entry.Open()
		if err != nil {
			return err
		}
		mode := os.FileMode(0600)
		if entry.Mode()&0111 != 0 || filepath.Base(target) == "adb" {
			mode = 0700
		}
		output, err := os.OpenFile(target, os.O_WRONLY|os.O_CREATE|os.O_EXCL, mode)
		if err != nil {
			source.Close()
			return err
		}
		n, copyErr := io.Copy(output, io.LimitReader(source, int64(entry.UncompressedSize64)+1))
		source.Close()
		closeErr := output.Close()
		if copyErr != nil {
			return copyErr
		}
		if closeErr != nil {
			return closeErr
		}
		if uint64(n) != entry.UncompressedSize64 {
			return errors.New("archive size mismatch")
		}
	}
	return nil
}
