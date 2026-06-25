from pathlib import Path
import unittest

from voz_knowledge_mcp.parser import VozParser


FIXTURE = Path(__file__).parent / "fixtures" / "voz_thread_page.html"


class VozParserTest(unittest.TestCase):
    def test_parses_thread_title_page_count_and_posts(self):
        page = VozParser().parse_thread_page(FIXTURE.read_text(encoding="utf-8"), "https://voz.vn/t/sample.123/")

        self.assertEqual(page.title, "Dành cho anh em làm Content Creator trên mọi nền tảng (No Reup)")
        self.assertEqual(page.page_count, 3)
        self.assertEqual(len(page.posts), 2)

        first = page.posts[0]
        self.assertEqual(first.post_id, "1001")
        self.assertEqual(first.username, "Dương Pi")
        self.assertEqual(first.timestamp, "2026-01-18T08:30:00+0700")
        self.assertIn("Chia sẻ cách làm content creator không reup.", first.body_text)
        self.assertNotIn("Quote này không nên lẫn vào body chính.", first.body_text)
        self.assertEqual(first.quotes, ["Quote này không nên lẫn vào body chính."])
        self.assertIn("https://example.com/course", first.links)
        self.assertIn("https://voz.vn/data/attachments/1/1234-image.png", first.images)

    def test_normalizes_obfuscated_telegram_links_in_text(self):
        page = VozParser().parse_thread_page(FIXTURE.read_text(encoding="utf-8"), "https://voz.vn/t/sample.123/")

        second = page.posts[1]
        self.assertIn("https://t.me/nghien_trick", second.links)


if __name__ == "__main__":
    unittest.main()
