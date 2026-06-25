import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from voz_knowledge_mcp.browser_cdp import BrowserCdpManager


class BrowserCdpManagerTest(unittest.TestCase):
    def test_configured_urls_win_before_auto_launch_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager = BrowserCdpManager(Path(tmp))
            env = {
                "VOZ_BROWSER_CDP_URLS": "http://127.0.0.1:9001,http://127.0.0.1:9002",
                "VOZ_CHROME_CDP_URL": "http://127.0.0.1:9003",
            }

            with patch.dict("os.environ", env, clear=True), patch.object(manager, "_is_installed", return_value=True):
                self.assertEqual(
                    manager.cdp_urls(auto_launch=False),
                    [
                        "http://127.0.0.1:9001",
                        "http://127.0.0.1:9002",
                        "http://127.0.0.1:9003",
                    ],
                )

    def test_auto_launch_adds_installed_browser_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager = BrowserCdpManager(Path(tmp))

            def is_installed(spec):
                return spec.name in {"chrome", "brave"}

            with patch.dict("os.environ", {}, clear=True), patch.object(manager, "_is_installed", side_effect=is_installed), patch.object(manager, "_launch", return_value=True):
                self.assertEqual(
                    manager.cdp_urls(auto_launch=True),
                    ["http://127.0.0.1:9223", "http://127.0.0.1:9222"],
                )

    def test_auto_launch_can_be_disabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager = BrowserCdpManager(Path(tmp))

            with patch.dict("os.environ", {"VOZ_AUTO_LAUNCH_BROWSERS": "0"}, clear=True), patch.object(manager, "_is_installed", return_value=True):
                self.assertEqual(manager.cdp_urls(auto_launch=True), [])


if __name__ == "__main__":
    unittest.main()
