package setupwizard

import (
	"os"
	"path/filepath"
)

func defaultDataDir() string {
	if dir := os.Getenv("MOMCOZY_DATA_DIR"); dir != "" {
		return dir
	}
	home, _ := os.UserHomeDir()
	return filepath.Join(home, ".momcozy-desktop")
}

// Existing or damaged configurations stay in desktop mode, preserving its
// validation error rather than silently starting a replacement setup.
func DefaultCommand() string { return commandForDir(defaultDataDir()) }
func commandForDir(dir string) string {
	if _, err := os.Stat(filepath.Join(dir, "cameras.private.json")); !os.IsNotExist(err) {
		return "desktop"
	}
	files, err := filepath.Glob(filepath.Join(dir, "bridge-*.private.json"))
	if err != nil || len(files) > 0 {
		return "desktop"
	}
	return "setup"
}
