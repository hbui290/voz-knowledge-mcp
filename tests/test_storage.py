import tempfile
import unittest
from pathlib import Path

from voz_knowledge_mcp.models import ParsedPost, ThreadPage
from voz_knowledge_mcp.storage import ArchiveStore


class ArchiveStoreTest(unittest.TestCase):
    def test_upserts_thread_posts_assets_and_searches_without_duplicates(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = ArchiveStore(Path(tmp) / "archive.sqlite")
            page = ThreadPage(
                url="https://voz.vn/t/sample.123/",
                title="Content Creator",
                page_count=1,
                posts=[
                    ParsedPost(
                        post_id="1001",
                        username="Dương Pi",
                        timestamp="2026-01-18T08:30:00+0700",
                        body_text="Làm content creator không reup với YouTube.",
                        quotes=[],
                        links=["https://example.com/course"],
                        images=["https://voz.vn/data/attachments/1/1234-image.png"],
                    )
                ],
            )

            first = store.save_thread_page(page, source_mode="public")
            second = store.save_thread_page(page, source_mode="public")
            results = store.search_archive("youtube")
            assets = store.list_assets("https://voz.vn/t/sample.123/")

            self.assertEqual(first["posts_saved"], 1)
            self.assertEqual(second["posts_saved"], 1)
            self.assertEqual(store.count_posts("https://voz.vn/t/sample.123/"), 1)
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["post_id"], "1001")
            self.assertEqual({asset["asset_type"] for asset in assets}, {"link", "image"})

    def test_search_archive_defaults_to_50_results(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = ArchiveStore(Path(tmp) / "archive.sqlite")
            page = ThreadPage(
                url="https://voz.vn/t/sample.123/",
                title="YouTube Reup",
                page_count=1,
                posts=[
                    ParsedPost(
                        post_id=str(1000 + index),
                        username="tester",
                        timestamp=f"2026-01-01T00:{index:02d}:00+0700",
                        body_text=f"youtube reup post {index}",
                    )
                    for index in range(60)
                ],
            )
            store.save_thread_page(page, source_mode="public")

            self.assertEqual(len(store.search_archive("youtube")), 50)


if __name__ == "__main__":
    unittest.main()
