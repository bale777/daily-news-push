import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import feedparser
import requests
from bs4 import BeautifulSoup

from news_pusher.config import Config, FeedSource


@dataclass
class Article:
    title: str
    url: str
    summary: str
    source_name: str
    category: str
    source_priority: int = 5
    published_at: Optional[datetime] = None
    fetched_at: datetime = field(default_factory=datetime.now)

    @property
    def url_hash(self) -> str:
        return hashlib.md5(self.url.encode()).hexdigest()

    @property
    def normalized_title(self) -> str:
        t = self.title.lower()
        t = re.sub(r"[^\w\s]", "", t)
        t = re.sub(r"\s+", " ", t).strip()
        return t


class NewsFetcher:
    def __init__(self, config: Config):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": config.scraping.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        })

    def fetch_all(self, sources: list[FeedSource]) -> list[Article]:
        articles = []
        for source in sources:
            try:
                if source.type == "rss":
                    result = self._fetch_rss(source)
                elif source.type == "toutiao":
                    result = self._fetch_toutiao(source)
                else:
                    result = self._fetch_scrape(source)

                if not result and source.fallback_url:
                    result = self._fetch_fallback(source)

                articles.extend(result)
            except Exception:
                pass
        return articles

    def _fetch_rss(self, source: FeedSource) -> list[Article]:
        articles = []
        try:
            resp = self.session.get(source.url, timeout=source.timeout)
            resp.raise_for_status()
            feed = feedparser.parse(resp.content)

            for entry in feed.entries:
                url = entry.get("link", "")
                title = entry.get("title", "").strip()
                if not url or not title:
                    continue

                summary = entry.get("summary", entry.get("description", ""))
                summary = _strip_html(summary)[:500]

                published = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    try:
                        published = datetime(*entry.published_parsed[:6])
                    except Exception:
                        pass

                articles.append(Article(
                    title=title,
                    url=url,
                    summary=summary,
                    source_name=source.name,
                    category=source.category,
                    source_priority=source.priority,
                    published_at=published,
                ))
        except Exception:
            pass
        return articles

    def _fetch_toutiao(self, source: FeedSource) -> list[Article]:
        articles = []
        try:
            resp = self.session.get(source.url, timeout=source.timeout)
            resp.raise_for_status()
            data = resp.json()

            items = data.get("data", [])
            if not isinstance(items, list):
                return articles

            for item in items:
                if "content" not in item:
                    continue

                try:
                    content = json.loads(item["content"])
                except (json.JSONDecodeError, TypeError):
                    continue

                title = ""
                url = ""
                summary = ""

                if "share" in content:
                    title = content["share"].get("share_title", "")
                    url = content["share"].get("share_url", "")
                if not title:
                    title = content.get("title", "")
                if not url:
                    url = content.get("share_url", "")
                if not url and "display_url" in content:
                    url = content["display_url"]
                summary = content.get("abstract", content.get("description", ""))

                if not title or not url:
                    continue

                articles.append(Article(
                    title=title,
                    url=url,
                    summary=summary,
                    source_name=source.name,
                    category=source.category,
                    source_priority=source.priority,
                ))
        except Exception:
            pass
        return articles

    def _fetch_scrape(self, source: FeedSource) -> list[Article]:
        articles = []
        try:
            resp = self.session.get(source.url, timeout=source.timeout)
            resp.raise_for_status()
            text = resp.text

            # Handle JSONP (Sina feeds: try{feedCallBack({...})}catch(e){})
            jsonp_match = re.search(r'feedCallBack\((\{.*\})\)', text, re.DOTALL)
            if not jsonp_match:
                jsonp_match = re.search(r'[\w$]+\((\{.*\})\)', text, re.DOTALL)
            if jsonp_match:
                data = json.loads(jsonp_match.group(1))
                if "result" in data and "data" in data["result"]:
                    for item in data["result"]["data"]:
                        title = item.get("title", "").strip()
                        url = item.get("url", "")
                        if not title or not url:
                            continue
                        articles.append(Article(
                            title=title,
                            url=url,
                            summary=item.get("intro", item.get("summary", "")),
                            source_name=source.name,
                            category=source.category,
                            source_priority=source.priority,
                        ))
                return articles

            # Fallback: HTML scraping (used when fallback_url is a real HTML page)
            soup = BeautifulSoup(text, "lxml")
            for link in soup.select("a[href]"):
                href = link.get("href", "")
                title = link.get_text(strip=True)
                if not title or not href or len(title) < 6:
                    continue
                if not href.startswith("http"):
                    continue
                articles.append(Article(
                    title=title,
                    url=href,
                    summary="",
                    source_name=source.name,
                    category=source.category,
                    source_priority=source.priority,
                ))
        except Exception:
            pass
        return articles

    def _fetch_fallback(self, source: FeedSource) -> list[Article]:
        try:
            resp = self.session.get(source.fallback_url, timeout=source.timeout)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")
            articles = []
            for link in soup.select("a[href]"):
                href = link.get("href", "")
                title = link.get_text(strip=True)
                if not title or not href or len(title) < 6:
                    continue
                if not href.startswith("http"):
                    continue
                articles.append(Article(
                    title=title,
                    url=href,
                    summary="",
                    source_name=source.name,
                    category=source.category,
                    source_priority=source.priority,
                ))
            return articles[:20]
        except Exception:
            return []


def _strip_html(text: str) -> str:
    if not text:
        return ""
    try:
        soup = BeautifulSoup(text, "lxml")
        return soup.get_text(separator=" ", strip=True)
    except Exception:
        return re.sub(r"<[^>]+>", "", text)
