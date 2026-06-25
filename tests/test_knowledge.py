import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from voz_knowledge_mcp.crawler import VozCrawler
from voz_knowledge_mcp.knowledge import (
    clean_links,
    classify_topics,
    is_noise_post,
)
from voz_knowledge_mcp.models import ParsedPost, ThreadPage
from voz_knowledge_mcp.storage import ArchiveStore


class KnowledgeProcessingTest(unittest.TestCase):
    def test_clean_links_removes_forum_noise_but_keeps_real_resources(self):
        cleaned = clean_links(
            [
                "https://voz.vn/goto/post?id=123",
                "https://voz.vn/u/975385/",
                "https://data.voz.vn/styles/next/xenforo/smilies/popopo/beauty.png",
                "data:image/gif;base64,AAAA",
                "https://voz.vn/attachments/file-webp.123/",
                "https://voz.vn/t/hoi-tao-anh-ai.1196613/post-40467635",
                "https://youtube.com/@example",
                "https://www.reddit.com/r/PartneredYoutube/comments/abc",
                "https://www.facebook.com/share/r/abc/",
                "https://vt.tiktok.com/abc/",
                "https://t.me/example",
            ],
            ["https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/72x72/1f602.png"],
        )

        useful = {item["url"] for item in cleaned["useful"]}
        removed = {item["url"] for item in cleaned["removed"]}

        self.assertIn("https://voz.vn/attachments/file-webp.123/", useful)
        self.assertIn("https://voz.vn/t/hoi-tao-anh-ai.1196613/post-40467635", useful)
        self.assertIn("https://youtube.com/@example", useful)
        self.assertIn("https://www.reddit.com/r/PartneredYoutube/comments/abc", useful)
        self.assertIn("https://www.facebook.com/share/r/abc/", useful)
        self.assertIn("https://vt.tiktok.com/abc/", useful)
        self.assertIn("https://t.me/example", useful)
        self.assertIn("https://voz.vn/goto/post?id=123", removed)
        self.assertIn("https://voz.vn/u/975385/", removed)
        self.assertIn("data:image/gif;base64,AAAA", removed)

    def test_noise_filter_keeps_short_real_questions(self):
        self.assertEqual(is_noise_post({"body_text": "đánh dấu"})[0], True)
        self.assertEqual(is_noise_post({"body_text": "Dạ e cám ơn bác"})[0], True)
        self.assertEqual(is_noise_post({"body_text": "Content dùng AI hay sao bác"})[0], False)
        self.assertEqual(is_noise_post({"body_text": "Bao nhiêu follow thì bật đc fb reel ạ"})[0], False)

    def test_classify_topics_covers_core_thread_families(self):
        self.assertIn("facebook_reels", classify_topics({"body_text": "reels rpm page facebook view us"}))
        self.assertIn("ai_policy", classify_topics({"body_text": "AI voice bị NDKTT nội dung sử dụng lại"}))
        self.assertIn("affiliate", classify_topics({"body_text": "gắn giỏ shopee amazon affiliate"}))
        self.assertIn("copyright_music", classify_topics({"body_text": "public domain nhạc cover suno bản quyền"}))

    def test_search_archive_grouped_groups_matching_posts(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = ArchiveStore(Path(tmp) / "archive.sqlite")
            store.save_thread_page(
                ThreadPage(
                    url="https://voz.vn/t/sample.123/",
                    title="Content Creator",
                    page_count=1,
                    posts=[
                        ParsedPost("1", "a", "2026-01-01T00:00:00+0700", "affiliate shopee gắn giỏ"),
                        ParsedPost("2", "b", "2026-01-01T00:01:00+0700", "affiliate amazon market us"),
                        ParsedPost("3", "c", "2026-01-01T00:02:00+0700", "youtube affiliate review"),
                    ],
                ),
                source_mode="public",
            )

            grouped = store.search_archive_grouped("affiliate", limit_per_group=2)

            self.assertEqual(grouped["query"], "affiliate")
            self.assertGreaterEqual(grouped["total_matches"], 3)
            self.assertIn("affiliate", grouped["groups"])
            self.assertLessEqual(len(grouped["groups"]["affiliate"]["posts"]), 2)

    def test_build_thread_packet_and_topic_digest_use_full_thread(self):
        with tempfile.TemporaryDirectory() as tmp:
            crawler = VozCrawler(ArchiveStore(Path(tmp) / "archive.sqlite"), Path(tmp) / "archive")

            def fake_crawl(url, mode, max_pages):
                return [
                    ThreadPage(
                        url=url,
                        title="Content Creator",
                        page_count=1,
                        posts=[
                            ParsedPost("1", "hropro", "2026-01-01T00:00:00+0700", "đánh dấu"),
                            ParsedPost("2", "hropro", "2026-01-01T00:01:00+0700", "AI voice dễ NDKTT nội dung sử dụng lại", links=["https://www.reddit.com/r/PartneredYoutube/comments/abc"]),
                            ParsedPost("3", "user", "2026-01-01T00:02:00+0700", "facebook reels rpm view US nhiệm vụ", images=["https://voz.vn/attachments/a.webp.123/"]),
                            ParsedPost("4", "user", "2026-01-01T00:03:00+0700", "affiliate shopee gắn giỏ link comment ít click"),
                        ],
                    )
                ]

            with patch.object(crawler, "_crawl_with_mode", side_effect=fake_crawl):
                packet = crawler.build_thread_packet("https://voz.vn/t/sample.123/", mode="public")
                digest = crawler.topic_digest("https://voz.vn/t/sample.123/", "affiliate", mode="public")

            self.assertEqual(packet["total_posts"], 4)
            self.assertEqual(packet["clean_posts"], 3)
            self.assertIn("packet_path", packet)
            self.assertTrue(Path(packet["packet_path"]).exists())
            self.assertIn("ai_policy", packet["topic_clusters"])
            self.assertIn("facebook_reels", packet["topic_clusters"])
            self.assertEqual(digest["topic"], "affiliate")
            self.assertEqual(digest["matching_posts"], 1)
            self.assertEqual(digest["posts"][0]["post_id"], "4")


if __name__ == "__main__":
    unittest.main()
