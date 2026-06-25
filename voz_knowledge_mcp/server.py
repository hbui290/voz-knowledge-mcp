import os
from pathlib import Path
from typing import List, Optional

from mcp.server.fastmcp import FastMCP

from .crawler import VozCrawler
from .storage import ArchiveStore


ARCHIVE_DIR = Path(os.environ.get("VOZ_ARCHIVE_DIR", "archive"))
DB_PATH = Path(os.environ.get("VOZ_ARCHIVE_DB", str(ARCHIVE_DIR / "voz_archive.sqlite")))

mcp = FastMCP("voz_knowledge_mcp")


def _crawler() -> VozCrawler:
    return VozCrawler(ArchiveStore(DB_PATH), ARCHIVE_DIR)


@mcp.tool()
def read_thread(url: str, mode: str = "auto", max_pages: Optional[int] = None) -> dict:
    """Read a VOZ thread, archive posts/assets, and return crawl metadata."""
    return _crawler().read_thread(url, mode=mode, max_pages=max_pages)


@mcp.tool()
def summarize_thread(url: str, mode: str = "auto") -> dict:
    """Create a lightweight Markdown summary from archived VOZ thread content."""
    return _crawler().summarize_thread(url, mode=mode)


@mcp.tool()
def search_archive(query: str, limit: int = 20) -> list:
    """Search archived VOZ posts by thread title, username, or body text."""
    return ArchiveStore(DB_PATH).search_archive(query, limit=limit)


@mcp.tool()
def extract_links(url: str, mode: str = "auto") -> dict:
    """Read a VOZ thread and return archived links/images/files."""
    return _crawler().extract_links(url, mode=mode)


@mcp.tool()
def crawl_threads(urls: List[str], mode: str = "auto", max_pages: Optional[int] = None) -> list:
    """Crawl multiple VOZ thread URLs into the local archive."""
    return _crawler().crawl_threads(urls, mode=mode, max_pages=max_pages)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
