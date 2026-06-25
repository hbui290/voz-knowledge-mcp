import argparse
import json
from pathlib import Path

from .crawler import VozCrawler
from .storage import ArchiveStore


def build_crawler(args: argparse.Namespace) -> VozCrawler:
    archive_dir = Path(args.archive_dir)
    db_path = Path(args.db_path) if args.db_path else archive_dir / "voz_archive.sqlite"
    return VozCrawler(ArchiveStore(db_path), archive_dir)


def main() -> None:
    parser = argparse.ArgumentParser(description="VOZ knowledge collector")
    parser.add_argument("--archive-dir", default="archive")
    parser.add_argument("--db-path")
    sub = parser.add_subparsers(dest="command", required=True)

    read = sub.add_parser("read-thread")
    read.add_argument("url")
    read.add_argument("--mode", default="auto", choices=["auto", "public", "browser"])
    read.add_argument("--max-pages", type=int)

    summary = sub.add_parser("summarize-thread")
    summary.add_argument("url")
    summary.add_argument("--mode", default="auto", choices=["auto", "public", "browser"])

    search = sub.add_parser("search-archive")
    search.add_argument("query")
    search.add_argument("--limit", type=int, default=20)

    links = sub.add_parser("extract-links")
    links.add_argument("url")
    links.add_argument("--mode", default="auto", choices=["auto", "public", "browser"])

    args = parser.parse_args()
    crawler = build_crawler(args)
    if args.command == "read-thread":
        result = crawler.read_thread(args.url, mode=args.mode, max_pages=args.max_pages)
    elif args.command == "summarize-thread":
        result = crawler.summarize_thread(args.url, mode=args.mode)
    elif args.command == "search-archive":
        result = crawler.store.search_archive(args.query, limit=args.limit)
    elif args.command == "extract-links":
        result = crawler.extract_links(args.url, mode=args.mode)
    else:
        raise SystemExit(f"Unknown command: {args.command}")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
