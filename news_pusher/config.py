import os
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from dotenv import load_dotenv


@dataclass
class PushConfig:
    provider: str = "pushplus"  # serverchan, pushplus, both
    serverchan_sendkey: str = ""
    serverchan_api_url: str = "https://sctapi.ftqq.com"
    pushplus_token: str = ""
    pushplus_api_url: str = "http://www.pushplus.plus/send"


@dataclass
class ScheduleConfig:
    times: list[str] = field(default_factory=lambda: ["09:00", "20:00"])
    timezone: str = "Asia/Shanghai"


@dataclass
class ContentConfig:
    max_per_category: int = 10
    max_total: int = 30
    title_prefix_morning: str = "早间新闻速递"
    title_prefix_evening: str = "晚间新闻速递"


@dataclass
class DedupConfig:
    title_similarity_threshold: float = 0.85
    sent_retention_days: int = 30
    dedup_window_days: int = 7


@dataclass
class FeedSource:
    name: str
    category: str  # domestic, international, finance
    url: str
    type: str = "rss"  # rss, scrape
    fallback_url: str = ""
    priority: int = 5
    enabled: bool = True
    timeout: int = 15


@dataclass
class LoggingConfig:
    level: str = "INFO"
    file: str = "logs/news_push.log"
    max_bytes: int = 5 * 1024 * 1024
    backup_count: int = 5


@dataclass
class ScrapingConfig:
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
    request_delay: float = 1.0
    max_retries: int = 3


@dataclass
class Config:
    push: PushConfig = field(default_factory=PushConfig)
    schedule: ScheduleConfig = field(default_factory=ScheduleConfig)
    content: ContentConfig = field(default_factory=ContentConfig)
    dedup: DedupConfig = field(default_factory=DedupConfig)
    feeds: dict[str, list[FeedSource]] = field(default_factory=dict)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    scraping: ScrapingConfig = field(default_factory=ScrapingConfig)


def _resolve_env(value: str) -> str:
    """Resolve ${VAR_NAME} placeholders in string values."""
    pattern = re.compile(r"\$\{(\w+)\}")
    matches = pattern.findall(value)
    for var in matches:
        env_val = os.environ.get(var, "")
        value = value.replace(f"${{{var}}}", env_val)
    return value


def _parse_feeds(raw_feeds: dict) -> dict[str, list[FeedSource]]:
    feeds: dict[str, list[FeedSource]] = {}
    for category, source_list in raw_feeds.items():
        feeds[category] = []
        for src in source_list:
            feeds[category].append(FeedSource(
                name=src.get("name", ""),
                category=category,
                url=src.get("url", ""),
                type=src.get("type", "rss"),
                fallback_url=src.get("fallback_url", ""),
                priority=src.get("priority", 5),
                enabled=src.get("enabled", True),
                timeout=src.get("timeout", 15),
            ))
    return feeds


def load_config(config_path: str = None) -> Config:
    load_dotenv()

    if config_path is None:
        config_path = os.environ.get(
            "NEWS_PUSH_CONFIG",
            str(Path(__file__).parent.parent / "config.yaml"),
        )

    with open(config_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    push_raw = raw.get("push", {})
    serverchan_raw = push_raw.get("serverchan", {})
    pushplus_raw = push_raw.get("pushplus", {})

    push = PushConfig(
        provider=_resolve_env(push_raw.get("provider", "pushplus")),
        serverchan_sendkey=_resolve_env(
            serverchan_raw.get("sendkey", "") or os.environ.get("SERVERCHAN_SENDKEY", "")
        ),
        serverchan_api_url=serverchan_raw.get("api_url", "https://sctapi.ftqq.com"),
        pushplus_token=_resolve_env(
            pushplus_raw.get("token", "") or os.environ.get("PUSHPLUS_TOKEN", "")
        ),
        pushplus_api_url=pushplus_raw.get("api_url", "http://www.pushplus.plus/send"),
    )

    schedule_raw = raw.get("schedule", {})
    schedule = ScheduleConfig(
        times=schedule_raw.get("times", ["09:00", "20:00"]),
        timezone=schedule_raw.get("timezone", "Asia/Shanghai"),
    )

    content_raw = raw.get("content", {})
    content = ContentConfig(
        max_per_category=content_raw.get("max_per_category", 10),
        max_total=content_raw.get("max_total", 30),
        title_prefix_morning=content_raw.get("title_prefix_morning", "早间新闻速递"),
        title_prefix_evening=content_raw.get("title_prefix_evening", "晚间新闻速递"),
    )

    dedup_raw = raw.get("dedup", {})
    dedup = DedupConfig(
        title_similarity_threshold=dedup_raw.get("title_similarity_threshold", 0.85),
        sent_retention_days=dedup_raw.get("sent_retention_days", 30),
        dedup_window_days=dedup_raw.get("dedup_window_days", 7),
    )

    feeds = _parse_feeds(raw.get("feeds", {}))

    logging_raw = raw.get("logging", {})
    logging_config = LoggingConfig(
        level=logging_raw.get("level", "INFO"),
        file=logging_raw.get("file", "logs/news_push.log"),
        max_bytes=logging_raw.get("max_bytes", 5 * 1024 * 1024),
        backup_count=logging_raw.get("backup_count", 5),
    )

    _default_ua = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
    scraping_raw = raw.get("scraping", {})
    scraping = ScrapingConfig(
        user_agent=scraping_raw.get("user_agent", _default_ua),
        request_delay=scraping_raw.get("request_delay", 1.0),
        max_retries=scraping_raw.get("max_retries", 3),
    )

    return Config(
        push=push,
        schedule=schedule,
        content=content,
        dedup=dedup,
        feeds=feeds,
        logging=logging_config,
        scraping=scraping,
    )
