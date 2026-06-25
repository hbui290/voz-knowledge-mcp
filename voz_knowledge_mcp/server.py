import os
from pathlib import Path
from typing import List, Optional

from mcp.server.fastmcp import FastMCP

from .crawler import VozCrawler
from .storage import ArchiveStore


ARCHIVE_DIR = Path(os.environ.get("VOZ_ARCHIVE_DIR", "archive"))
REPORTS_DIR = Path(os.environ.get("VOZ_REPORTS_DIR", "reports/voz"))
DB_PATH = Path(os.environ.get("VOZ_ARCHIVE_DB", str(ARCHIVE_DIR / "voz_archive.sqlite")))

mcp = FastMCP("voz_knowledge_mcp")


def _crawler() -> VozCrawler:
    return VozCrawler(ArchiveStore(DB_PATH), ARCHIVE_DIR, reports_dir=REPORTS_DIR)


@mcp.tool()
def read_thread(url: str, mode: str = "auto", max_pages: Optional[int] = None) -> dict:
    """Read a VOZ thread, archive posts/assets, and return crawl metadata."""
    return _crawler().read_thread(url, mode=mode, max_pages=max_pages)


@mcp.tool()
def summarize_thread(url: str, mode: str = "auto") -> dict:
    """Create a lightweight Markdown summary from archived VOZ thread content."""
    return _crawler().summarize_thread(url, mode=mode)


@mcp.tool()
def search_archive(query: str, limit: int = 50) -> list:
    """Search archived VOZ posts by thread title, username, or body text."""
    return ArchiveStore(DB_PATH).search_archive(query, limit=limit)


@mcp.tool()
def search_archive_grouped(query: str, limit_per_group: int = 5, max_matches: int = 500) -> dict:
    """Search archived VOZ posts and group matches by heuristic topic."""
    return ArchiveStore(DB_PATH).search_archive_grouped(query, limit_per_group=limit_per_group, max_matches=max_matches)


@mcp.tool()
def extract_links(url: str, mode: str = "auto") -> dict:
    """Read a VOZ thread and return archived links/images/files."""
    return _crawler().extract_links(url, mode=mode)


@mcp.tool()
def crawl_threads(urls: List[str], mode: str = "auto", max_pages: Optional[int] = None) -> list:
    """Crawl multiple VOZ thread URLs into the local archive."""
    return _crawler().crawl_threads(urls, mode=mode, max_pages=max_pages)


@mcp.tool()
def build_thread_packet(url: str, mode: str = "auto", max_posts: Optional[int] = None) -> dict:
    """Build a full clean/topic packet for insight synthesis and write it to archive/packets."""
    return _crawler().build_thread_packet(url, mode=mode, max_posts=max_posts)


@mcp.tool()
def topic_digest(url: str, topic: str, mode: str = "auto", max_posts: int = 200) -> dict:
    """Digest one topic from the full archived VOZ thread instead of relying on search limits."""
    return _crawler().topic_digest(url, topic=topic, mode=mode, max_posts=max_posts)


@mcp.tool()
def setup_browser_cdp() -> dict:
    """Launch installed Chromium-family browsers with local CDP ports for browser fallback."""
    return _crawler().cdp_manager.setup()


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
