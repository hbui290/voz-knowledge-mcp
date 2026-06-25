import argparse
import json
from pathlib import Path

from .crawler import VozCrawler
from .storage import ArchiveStore


def build_crawler(args: argparse.Namespace) -> VozCrawler:
    archive_dir = Path(args.archive_dir)
    reports_dir = Path(args.reports_dir)
    db_path = Path(args.db_path) if args.db_path else archive_dir / "voz_archive.sqlite"
    return VozCrawler(ArchiveStore(db_path), archive_dir, reports_dir=reports_dir)


def main() -> None:
    parser = argparse.ArgumentParser(description="VOZ knowledge collector")
    parser.add_argument("--archive-dir", default="archive")
    parser.add_argument("--reports-dir", default="reports")
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
    search.add_argument("--limit", type=int, default=50)

    grouped = sub.add_parser("search-archive-grouped")
    grouped.add_argument("query")
    grouped.add_argument("--limit-per-group", type=int, default=5)
    grouped.add_argument("--max-matches", type=int, default=500)

    links = sub.add_parser("extract-links")
    links.add_argument("url")
    links.add_argument("--mode", default="auto", choices=["auto", "public", "browser"])

    packet = sub.add_parser("build-thread-packet")
    packet.add_argument("url")
    packet.add_argument("--mode", default="auto", choices=["auto", "public", "browser"])
    packet.add_argument("--max-posts", type=int)

    digest = sub.add_parser("topic-digest")
    digest.add_argument("url")
    digest.add_argument("topic")
    digest.add_argument("--mode", default="auto", choices=["auto", "public", "browser"])
    digest.add_argument("--max-posts", type=int, default=200)

    args = parser.parse_args()
    crawler = build_crawler(args)
    if args.command == "read-thread":
        result = crawler.read_thread(args.url, mode=args.mode, max_pages=args.max_pages)
    elif args.command == "summarize-thread":
        result = crawler.summarize_thread(args.url, mode=args.mode)
    elif args.command == "search-archive":
        result = crawler.store.search_archive(args.query, limit=args.limit)
    elif args.command == "search-archive-grouped":
        result = crawler.store.search_archive_grouped(args.query, limit_per_group=args.limit_per_group, max_matches=args.max_matches)
    elif args.command == "extract-links":
        result = crawler.extract_links(args.url, mode=args.mode)
    elif args.command == "build-thread-packet":
        result = crawler.build_thread_packet(args.url, mode=args.mode, max_posts=args.max_posts)
    elif args.command == "topic-digest":
        result = crawler.topic_digest(args.url, topic=args.topic, mode=args.mode, max_posts=args.max_posts)
    else:
        raise SystemExit(f"Unknown command: {args.command}")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
