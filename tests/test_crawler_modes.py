import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from voz_knowledge_mcp.crawler import VozCrawler
from voz_knowledge_mcp.models import ParsedPost, ThreadPage
from voz_knowledge_mcp.storage import ArchiveStore


class VozCrawlerModesTest(unittest.TestCase):
    def test_auto_uses_public_then_browser_without_cookie_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            crawler = VozCrawler(ArchiveStore(Path(tmp) / "archive.sqlite"), Path(tmp) / "archive")

            self.assertEqual(crawler._resolve_modes("auto"), ["public", "browser"])

    def test_auto_reads_public_then_uses_browser_when_browser_succeeds(self):
        with tempfile.TemporaryDirectory() as tmp:
            crawler = VozCrawler(ArchiveStore(Path(tmp) / "archive.sqlite"), Path(tmp) / "archive")
            calls = []

            def fake_crawl(url, mode, max_pages):
                calls.append(mode)
                return [
                    ThreadPage(
                        url=url,
                        title=f"{mode} title",
                        page_count=1,
                        posts=[
                            ParsedPost(
                                post_id="1",
                                username=mode,
                                timestamp="2026-01-01T00:00:00+0700",
                                body_text=f"{mode} body",
                            )
                        ],
                    )
                ]

            with patch.object(crawler, "_crawl_with_mode", side_effect=fake_crawl):
                result = crawler.read_thread("https://voz.vn/t/sample.123/", mode="auto", max_pages=1)

            self.assertEqual(calls, ["public", "browser"])
            self.assertEqual(result["source_mode"], "browser")
            self.assertEqual(result["title"], "browser title")

    def test_auto_keeps_public_when_browser_fails_after_public_succeeds(self):
        with tempfile.TemporaryDirectory() as tmp:
            crawler = VozCrawler(ArchiveStore(Path(tmp) / "archive.sqlite"), Path(tmp) / "archive")

            def fake_crawl(url, mode, max_pages):
                if mode == "browser":
                    raise RuntimeError("browser unavailable")
                return [
                    ThreadPage(
                        url=url,
                        title="public title",
                        page_count=1,
                        posts=[
                            ParsedPost(
                                post_id="1",
                                username="public",
                                timestamp="2026-01-01T00:00:00+0700",
                                body_text="public body",
                            )
                        ],
                    )
                ]

            with patch.object(crawler, "_crawl_with_mode", side_effect=fake_crawl):
                result = crawler.read_thread("https://voz.vn/t/sample.123/", mode="auto", max_pages=1)

            self.assertEqual(result["source_mode"], "public")
            self.assertIn("browser_fallback_error", result)

    def test_cookie_mode_is_not_supported(self):
        with tempfile.TemporaryDirectory() as tmp:
            crawler = VozCrawler(ArchiveStore(Path(tmp) / "archive.sqlite"), Path(tmp) / "archive")

            with self.assertRaisesRegex(ValueError, "Unknown crawl mode"):
                crawler._crawl_with_mode("https://voz.vn/t/sample.123/", "cookie", max_pages=1)

    def test_chrome_mode_alias_is_not_supported(self):
        with tempfile.TemporaryDirectory() as tmp:
            crawler = VozCrawler(ArchiveStore(Path(tmp) / "archive.sqlite"), Path(tmp) / "archive")

            with self.assertRaisesRegex(ValueError, "Unknown crawl mode"):
                crawler._crawl_with_mode("https://voz.vn/t/sample.123/", "chrome", max_pages=1)

    def test_browser_cdp_urls_preserve_priority(self):
        with tempfile.TemporaryDirectory() as tmp:
            crawler = VozCrawler(ArchiveStore(Path(tmp) / "archive.sqlite"), Path(tmp) / "archive")
            env = {
                "VOZ_BROWSER_CDP_URLS": "http://127.0.0.1:9222, http://127.0.0.1:9224",
                "VOZ_CHROME_CDP_URL": "http://127.0.0.1:9223",
                "VOZ_BRAVE_CDP_URL": "http://127.0.0.1:9222",
                "VOZ_EDGE_CDP_URL": "http://127.0.0.1:9225",
                "VOZ_CHROMIUM_CDP_URL": "http://127.0.0.1:9226",
                "VOZ_ARC_CDP_URL": "http://127.0.0.1:9227",
                "VOZ_VIVALDI_CDP_URL": "http://127.0.0.1:9228",
                "VOZ_OPERA_CDP_URL": "http://127.0.0.1:9229",
                "VOZ_COCCOC_CDP_URL": "http://127.0.0.1:9230",
                "VOZ_BROWSER_CDP_URL": "http://127.0.0.1:9231",
            }

            with patch.dict("os.environ", env, clear=True):
                self.assertEqual(
                    crawler._browser_cdp_urls(),
                    [
                        "http://127.0.0.1:9222",
                        "http://127.0.0.1:9224",
                        "http://127.0.0.1:9223",
                        "http://127.0.0.1:9225",
                        "http://127.0.0.1:9226",
                        "http://127.0.0.1:9227",
                        "http://127.0.0.1:9228",
                        "http://127.0.0.1:9229",
                        "http://127.0.0.1:9230",
                        "http://127.0.0.1:9231",
                    ],
                )


if __name__ == "__main__":
    unittest.main()
