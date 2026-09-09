import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class HomeAssistantAppRuntimeTests(unittest.TestCase):
    def test_ingress_streams_large_apk_uploads(self):
        config = (ROOT / "home_assistant_app" / "config.yaml").read_text(
            encoding="utf-8"
        )
        self.assertIn("ingress_stream: true", config)

    def test_oauth_browser_stays_within_small_home_assistant_memory_budgets(self):
        browser = (ROOT / "home_assistant_app" / "oauth-browser.sh").read_text(
            encoding="utf-8"
        )
        runtime = (ROOT / "home_assistant_app" / "run.sh").read_text(encoding="utf-8")
        for flag in (
            "--disable-gpu",
            "--disable-extensions",
            "--disable-background-networking",
            "--single-process",
            "--no-zygote",
            "--js-flags=--max-old-space-size=64",
            "--app=https://accounts.google.com/EmbeddedSetup",
        ):
            self.assertIn(flag, browser)
        self.assertIn("1024x640x16", runtime)


if __name__ == "__main__":
    unittest.main()
