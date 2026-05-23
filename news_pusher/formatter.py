from datetime import datetime

from news_pusher.fetcher import Article
from news_pusher.config import Config


def format_message(
    articles: list[Article],
    config: Config,
    session: str = "morning",
) -> tuple[str, str]:
    """Return (title, body_markdown) for the push message."""

    tz_display = "CST"
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M")

    if session == "morning":
        prefix = config.content.title_prefix_morning
    else:
        prefix = config.content.title_prefix_evening

    push_title = f"{prefix} | {date_str} {time_str} {tz_display}"

    grouped = {"domestic": [], "international": [], "finance": []}
    for a in articles:
        if a.category in grouped:
            grouped[a.category].append(a)

    lines = [f"## {prefix}", f"**{date_str} {time_str}**\n"]

    labels = {
        "domestic": "国内热点",
        "international": "国际新闻",
        "finance": "财经资讯",
    }

    for cat in ("domestic", "international", "finance"):
        items = grouped[cat]
        if not items:
            continue
        lines.append(f"### {labels[cat]}")
        for i, a in enumerate(items, 1):
            lines.append(f"{i}. [{a.title}]({a.url}) - *{a.source_name}*")
        lines.append("")

    lines.append(f"> 共 {len(articles)} 条 | DailyNewsPush")

    return push_title, "\n".join(lines)
