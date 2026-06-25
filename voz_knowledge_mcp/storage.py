import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from .knowledge import classify_topics, compact_post

from .models import ParsedPost, ThreadPage


class ArchiveStore:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def save_thread_page(self, page: ThreadPage, source_mode: str) -> Dict[str, int]:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO threads(url, title, page_count, last_crawled_at, source_mode)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(url) DO UPDATE SET
                    title=excluded.title,
                    page_count=MAX(threads.page_count, excluded.page_count),
                    last_crawled_at=excluded.last_crawled_at,
                    source_mode=excluded.source_mode
                """,
                (page.url, page.title, page.page_count, now, source_mode),
            )
            for post in page.posts:
                self._save_post(conn, page.url, post, now)
                self._save_assets(conn, page.url, post, now)
        return {"posts_saved": len(page.posts)}

    def save_summary(self, thread_url: str, summary_markdown: str, scope: str = "thread") -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO summaries(thread_url, scope, summary_markdown, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (thread_url, scope, summary_markdown, now),
            )

    def get_thread(self, thread_url: str) -> Optional[Dict[str, str]]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT url, title, page_count, last_crawled_at, source_mode FROM threads WHERE url = ?",
                (thread_url,),
            ).fetchone()
        return dict(row) if row else None

    def search_archive(self, query: str, limit: int = 50) -> List[Dict[str, str]]:
        pattern = f"%{query}%"
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT p.thread_url, t.title, p.post_id, p.username, p.timestamp, p.body_text
                FROM posts p
                JOIN threads t ON t.url = p.thread_url
                WHERE p.body_text LIKE ? OR p.username LIKE ? OR t.title LIKE ?
                ORDER BY p.timestamp DESC, p.post_id DESC
                LIMIT ?
                """,
                (pattern, pattern, pattern, limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def search_archive_grouped(self, query: str, limit_per_group: int = 5, max_matches: int = 500) -> Dict:
        matches = self.search_archive(query, limit=max_matches)
        grouped: Dict[str, List[Dict]] = {}
        for row in matches:
            row = dict(row)
            row["topics"] = classify_topics(row)
            row["signal_score"] = 1
            for topic in row["topics"]:
                grouped.setdefault(topic, []).append(row)
        groups = {}
        for topic, rows in grouped.items():
            groups[topic] = {
                "count": len(rows),
                "posts": [compact_post(row) for row in rows[:limit_per_group]],
            }
        return {
            "query": query,
            "total_matches": len(matches),
            "limit_per_group": limit_per_group,
            "groups": dict(sorted(groups.items())),
        }

    def list_assets(self, thread_url: Optional[str] = None) -> List[Dict[str, str]]:
        sql = "SELECT thread_url, post_id, asset_type, url, status FROM assets"
        params = ()
        if thread_url:
            sql += " WHERE thread_url = ?"
            params = (thread_url,)
        sql += " ORDER BY thread_url, post_id, asset_type, url"
        with self._connect() as conn:
            return [dict(row) for row in conn.execute(sql, params).fetchall()]

    def get_thread_posts(self, thread_url: str) -> List[Dict[str, str]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT post_id, username, timestamp, body_text, quotes_json, links_json, images_json
                FROM posts
                WHERE thread_url = ?
                ORDER BY CAST(post_id AS INTEGER)
                """,
                (thread_url,),
            ).fetchall()
        return [dict(row) for row in rows]

    def count_posts(self, thread_url: str) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS count FROM posts WHERE thread_url = ?", (thread_url,)).fetchone()
        return int(row["count"])

    def _save_post(self, conn: sqlite3.Connection, thread_url: str, post: ParsedPost, crawled_at: str) -> None:
        conn.execute(
            """
            INSERT INTO posts(
                thread_url, post_id, username, timestamp, body_text,
                quotes_json, links_json, images_json, crawled_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(thread_url, post_id) DO UPDATE SET
                username=excluded.username,
                timestamp=excluded.timestamp,
                body_text=excluded.body_text,
                quotes_json=excluded.quotes_json,
                links_json=excluded.links_json,
                images_json=excluded.images_json,
                crawled_at=excluded.crawled_at
            """,
            (
                thread_url,
                post.post_id,
                post.username,
                post.timestamp,
                post.body_text,
                json.dumps(post.quotes, ensure_ascii=False),
                json.dumps(post.links, ensure_ascii=False),
                json.dumps(post.images, ensure_ascii=False),
                crawled_at,
            ),
        )

    def _save_assets(self, conn: sqlite3.Connection, thread_url: str, post: ParsedPost, crawled_at: str) -> None:
        for url in post.links:
            conn.execute(
                """
                INSERT OR REPLACE INTO assets(thread_url, post_id, asset_type, url, status, crawled_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (thread_url, post.post_id, "link", url, "found", crawled_at),
            )
        for url in post.images:
            conn.execute(
                """
                INSERT OR REPLACE INTO assets(thread_url, post_id, asset_type, url, status, crawled_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (thread_url, post.post_id, "image", url, "found", crawled_at),
            )

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS threads (
                    url TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    page_count INTEGER NOT NULL DEFAULT 1,
                    last_crawled_at TEXT NOT NULL,
                    source_mode TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS posts (
                    thread_url TEXT NOT NULL,
                    post_id TEXT NOT NULL,
                    username TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    body_text TEXT NOT NULL,
                    quotes_json TEXT NOT NULL,
                    links_json TEXT NOT NULL,
                    images_json TEXT NOT NULL,
                    crawled_at TEXT NOT NULL,
                    PRIMARY KEY(thread_url, post_id),
                    FOREIGN KEY(thread_url) REFERENCES threads(url)
                );

                CREATE TABLE IF NOT EXISTS assets (
                    thread_url TEXT NOT NULL,
                    post_id TEXT NOT NULL,
                    asset_type TEXT NOT NULL,
                    url TEXT NOT NULL,
                    status TEXT NOT NULL,
                    crawled_at TEXT NOT NULL,
                    PRIMARY KEY(thread_url, post_id, asset_type, url),
                    FOREIGN KEY(thread_url, post_id) REFERENCES posts(thread_url, post_id)
                );

                CREATE TABLE IF NOT EXISTS summaries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    thread_url TEXT NOT NULL,
                    scope TEXT NOT NULL,
                    summary_markdown TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(thread_url) REFERENCES threads(url)
                );
                """
            )
