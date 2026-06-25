import json
import os
import time
from pathlib import Path
from typing import Dict, Iterable, List, Optional
from urllib.parse import urljoin

import requests

from .browser_cdp import BrowserCdpManager
from .models import ThreadPage
from .parser import VozParser
from .storage import ArchiveStore


class VozCrawlerError(RuntimeError):
    pass


class VozCrawler:
    def __init__(
        self,
        store: ArchiveStore,
        archive_dir: Path,
        delay_seconds: float = 0.7,
        timeout_seconds: int = 20,
    ):
        self.store = store
        self.archive_dir = Path(archive_dir)
        self.cdp_manager = BrowserCdpManager(self.archive_dir)
        self.delay_seconds = delay_seconds
        self.timeout_seconds = timeout_seconds
        self.parser = VozParser()
        self.raw_dir = self.archive_dir / "raw"
        self.json_dir = self.archive_dir / "json"
        self.markdown_dir = self.archive_dir / "markdown"
        for directory in (self.raw_dir, self.json_dir, self.markdown_dir):
            directory.mkdir(parents=True, exist_ok=True)

    def read_thread(self, url: str, mode: str = "auto", max_pages: Optional[int] = None) -> Dict:
        if mode == "auto":
            return self._read_thread_auto(url, max_pages=max_pages)

        modes = self._resolve_modes(mode)
        last_error = None
        for candidate in modes:
            try:
                pages = self._crawl_with_mode(url, candidate, max_pages)
                if self._looks_complete(pages):
                    return self._persist(url, pages, candidate)
                last_error = VozCrawlerError(f"{candidate} mode returned no posts")
            except Exception as exc:  # Keep fallback modes available.
                last_error = exc
        raise VozCrawlerError(str(last_error) if last_error else "Unable to crawl thread")

    def _read_thread_auto(self, url: str, max_pages: Optional[int]) -> Dict:
        public_result = None
        public_error = None
        try:
            public_pages = self._crawl_with_mode(url, "public", max_pages)
            if self._looks_complete(public_pages):
                public_result = self._persist(url, public_pages, "public")
            else:
                public_error = VozCrawlerError("public mode returned no posts")
        except Exception as exc:
            public_error = exc

        try:
            browser_pages = self._crawl_with_mode(url, "browser", max_pages)
            if self._looks_complete(browser_pages):
                result = self._persist(url, browser_pages, "browser")
                if public_error:
                    result["public_fallback_error"] = str(public_error)
                return result
            browser_error = VozCrawlerError("browser mode returned no posts")
        except Exception as exc:
            browser_error = exc

        if public_result:
            public_result["browser_fallback_error"] = str(browser_error)
            return public_result
        raise VozCrawlerError(str(browser_error or public_error or "Unable to crawl thread"))

    def crawl_threads(self, urls: Iterable[str], mode: str = "auto", max_pages: Optional[int] = None) -> List[Dict]:
        results = []
        for url in urls:
            try:
                results.append(self.read_thread(url, mode=mode, max_pages=max_pages))
            except Exception as exc:
                results.append({"url": url, "ok": False, "error": str(exc)})
        return results

    def extract_links(self, url: str, mode: str = "auto") -> Dict:
        result = self.read_thread(url, mode=mode)
        assets = self.store.list_assets(result["thread_url"])
        return {"thread_url": result["thread_url"], "assets": assets}

    def summarize_thread(self, url: str, mode: str = "auto") -> Dict:
        result = self.read_thread(url, mode=mode)
        posts = self.store.get_thread_posts(result["thread_url"])
        summary = self._build_summary(result["title"], result["thread_url"], posts, self.store.list_assets(result["thread_url"]))
        self.store.save_summary(result["thread_url"], summary)
        path = self.markdown_dir / f"{self._slug(result['thread_url'])}.md"
        path.write_text(summary, encoding="utf-8")
        return {"thread_url": result["thread_url"], "summary_markdown": summary, "markdown_path": str(path)}

    def _crawl_with_mode(self, url: str, mode: str, max_pages: Optional[int]) -> List[ThreadPage]:
        if mode == "public":
            return self._crawl_public(url, max_pages=max_pages, session=requests.Session())
        if mode == "browser":
            return self._crawl_browser(url, max_pages=max_pages)
        raise ValueError(f"Unknown crawl mode: {mode}")

    def _crawl_public(self, url: str, max_pages: Optional[int], session: requests.Session) -> List[ThreadPage]:
        first_html = self._fetch(session, url)
        first_page = self.parser.parse_thread_page(first_html, url)
        page_total = min(first_page.page_count, max_pages or first_page.page_count)
        pages = [first_page]
        self._write_raw(url, 1, first_html)
        for page_number in range(2, page_total + 1):
            time.sleep(self.delay_seconds)
            page_url = self._page_url(url, page_number)
            html = self._fetch(session, page_url)
            self._write_raw(url, page_number, html)
            pages.append(self.parser.parse_thread_page(html, page_url))
        return pages

    def _crawl_browser(self, url: str, max_pages: Optional[int]) -> List[ThreadPage]:
        cdp_urls = self._browser_cdp_urls()
        if not cdp_urls:
            raise VozCrawlerError("Set VOZ_BROWSER_CDP_URLS or a browser-specific CDP URL")
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise VozCrawlerError("Install playwright and browser support for browser fallback") from exc

        last_error = None
        with sync_playwright() as p:
            for cdp_url in cdp_urls:
                try:
                    pages = self._crawl_browser_url(p, cdp_url, url, max_pages)
                    if self._looks_complete(pages):
                        return pages
                    last_error = VozCrawlerError(f"{cdp_url} returned no posts")
                except Exception as exc:
                    last_error = exc
        raise VozCrawlerError(str(last_error) if last_error else "No browser CDP endpoint worked")

    def _crawl_browser_url(self, playwright, cdp_url: str, url: str, max_pages: Optional[int]) -> List[ThreadPage]:
        pages: List[ThreadPage] = []
        browser = playwright.chromium.connect_over_cdp(cdp_url)
        try:
            context = browser.contexts[0] if browser.contexts else browser.new_context()
            page = context.new_page()
            try:
                page.goto(url, wait_until="networkidle", timeout=self.timeout_seconds * 1000)
                first_html = page.content()
                first_page = self.parser.parse_thread_page(first_html, url)
                page_total = min(first_page.page_count, max_pages or first_page.page_count)
                pages.append(first_page)
                self._write_raw(url, 1, first_html)
                for page_number in range(2, page_total + 1):
                    time.sleep(self.delay_seconds)
                    page_url = self._page_url(url, page_number)
                    page.goto(page_url, wait_until="networkidle", timeout=self.timeout_seconds * 1000)
                    html = page.content()
                    self._write_raw(url, page_number, html)
                    pages.append(self.parser.parse_thread_page(html, page_url))
            finally:
                page.close()
        finally:
            browser.close()
        return pages

    def _browser_cdp_urls(self) -> List[str]:
        return self.cdp_manager.cdp_urls(auto_launch=True)

    def _fetch(self, session: requests.Session, url: str) -> str:
        headers = {
            "User-Agent": "Mozilla/5.0 VOZKnowledgeCollector/0.1",
            "Accept-Language": "vi,en;q=0.8",
        }
        response = session.get(url, headers=headers, timeout=self.timeout_seconds)
        if response.status_code in (401, 403):
            raise VozCrawlerError(f"Login required or blocked: HTTP {response.status_code}")
        response.raise_for_status()
        return response.text

    def _persist(self, original_url: str, pages: List[ThreadPage], mode: str) -> Dict:
        thread_url = original_url
        title = pages[0].title
        total_posts = 0
        for page in pages:
            canonical_page = ThreadPage(url=thread_url, title=title, page_count=pages[0].page_count, posts=page.posts)
            total_posts += self.store.save_thread_page(canonical_page, mode)["posts_saved"]
        archived_posts = self.store.get_thread_posts(thread_url)
        archived_assets = self.store.list_assets(thread_url)
        payload = {
            "ok": True,
            "thread_url": thread_url,
            "title": title,
            "source_mode": mode,
            "pages_read": len(pages),
            "posts_saved": total_posts,
            "posts": archived_posts,
            "assets": archived_assets,
        }
        json_path = self.json_dir / f"{self._slug(thread_url)}.json"
        json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        payload["json_path"] = str(json_path)
        return payload

    def _build_summary(self, title: str, thread_url: str, posts: List[Dict[str, str]], assets: List[Dict[str, str]]) -> str:
        excerpts = [post["body_text"] for post in posts if post["body_text"]]
        top_posts = excerpts[:8]
        links = [asset["url"] for asset in assets if asset["asset_type"] == "link"][:30]
        lines = [f"# {title or thread_url}", "", f"- Thread: {thread_url}", f"- Posts archived: {len(posts)}", ""]
        lines.append("## Key excerpts")
        if top_posts:
            lines.extend(f"- {excerpt[:280]}" for excerpt in top_posts)
        else:
            lines.append("- No readable post text archived yet.")
        lines.extend(["", "## Links"])
        if links:
            lines.extend(f"- {link}" for link in links)
        else:
            lines.append("- No links found.")
        lines.extend(["", "## Checklist for manual review", "- Verify claims and external links.", "- Revisit image-only posts with OCR if needed.", "- Mark high-signal posts for deeper synthesis."])
        return "\n".join(lines) + "\n"

    def _looks_complete(self, pages: List[ThreadPage]) -> bool:
        return bool(pages and any(page.posts for page in pages))

    def _resolve_modes(self, mode: str) -> List[str]:
        if mode == "auto":
            return ["public", "browser"]
        return [mode]

    def _page_url(self, url: str, page_number: int) -> str:
        base = url.rstrip("/") + "/"
        return urljoin(base, f"page-{page_number}")

    def _write_raw(self, url: str, page_number: int, html: str) -> None:
        path = self.raw_dir / f"{self._slug(url)}-page-{page_number}.html"
        path.write_text(html, encoding="utf-8")

    def _slug(self, value: str) -> str:
        return "".join(char if char.isalnum() else "-" for char in value.lower()).strip("-")[:120]
