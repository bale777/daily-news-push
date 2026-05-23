import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path


class NewsStore:
    def __init__(self, db_path: str = "data/sent_news.db"):
        os.makedirs(Path(db_path).parent, exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_db()

    def _init_db(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS sent_articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                source_name TEXT NOT NULL,
                category TEXT NOT NULL,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                push_session TEXT NOT NULL
            )
        """)
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_sent_url ON sent_articles(url)"
        )
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_sent_at ON sent_articles(sent_at)"
        )
        self.conn.commit()

    def is_sent(self, url: str, dedup_window_days: int = 7) -> bool:
        cutoff = datetime.now() - timedelta(days=dedup_window_days)
        row = self.conn.execute(
            "SELECT 1 FROM sent_articles WHERE url = ? AND sent_at > ?",
            (url, cutoff.isoformat()),
        ).fetchone()
        return row is not None

    def get_sent_urls(self, dedup_window_days: int = 7) -> set[str]:
        cutoff = datetime.now() - timedelta(days=dedup_window_days)
        rows = self.conn.execute(
            "SELECT url FROM sent_articles WHERE sent_at > ?",
            (cutoff.isoformat(),),
        ).fetchall()
        return {r[0] for r in rows}

    def get_sent_titles(self, dedup_window_days: int = 7) -> list[tuple[str, str]]:
        cutoff = datetime.now() - timedelta(days=dedup_window_days)
        rows = self.conn.execute(
            "SELECT title, url FROM sent_articles WHERE sent_at > ?",
            (cutoff.isoformat(),),
        ).fetchall()
        return [(r[0], r[1]) for r in rows]

    def mark_sent(self, articles, push_session: str):
        now = datetime.now().isoformat()
        records = [
            (a.url, a.title, a.source_name, a.category, now, push_session)
            for a in articles
        ]
        self.conn.executemany(
            "INSERT OR IGNORE INTO sent_articles (url, title, source_name, category, sent_at, push_session) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            records,
        )
        self.conn.commit()

    def cleanup(self, retention_days: int = 30):
        cutoff = datetime.now() - timedelta(days=retention_days)
        self.conn.execute(
            "DELETE FROM sent_articles WHERE sent_at < ?",
            (cutoff.isoformat(),),
        )
        self.conn.commit()

    def close(self):
        self.conn.close()
