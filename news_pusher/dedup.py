import difflib
import re
from datetime import datetime, timedelta

from news_pusher.store import NewsStore
from news_pusher.fetcher import Article
from news_pusher.config import Config


def normalize_title(title: str) -> str:
    t = title.lower()
    t = re.sub(r"[^\w\s]", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def title_similarity(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, a, b).ratio()


HOT_KEYWORDS = ["重磅", "突发", "紧急", "刚刚", "快讯", "breaking", "urgent"]


def rank_articles(articles: list[Article], config: Config) -> list[Article]:
    """Score and sort articles, returning top results."""
    now = datetime.now()
    scored = []
    for a in articles:
        score = 0
        # Source priority (1-10)
        score += a.source_priority * 1.5

        # Recency boost (within 4 hours)
        if a.published_at:
            age_hours = (now - a.published_at).total_seconds() / 3600
            if age_hours < 4:
                score += (4 - age_hours) * 2
            elif age_hours < 24:
                score += max(0, 3 - age_hours / 8)
            else:
                score += max(0, -age_hours / 24)

        # Hot keyword boost
        title_lower = a.title.lower()
        for kw in HOT_KEYWORDS:
            if kw in title_lower:
                score += 3
                break

        scored.append((score, a))

    scored.sort(key=lambda x: x[0], reverse=True)

    # Apply category caps
    result = []
    cat_counts = {"domestic": 0, "international": 0, "finance": 0}
    for _, article in scored:
        cat = article.category
        if cat_counts.get(cat, 0) < config.content.max_per_category:
            result.append(article)
            cat_counts[cat] = cat_counts.get(cat, 0) + 1
        if len(result) >= config.content.max_total:
            break

    return result


def dedup_articles(
    articles: list[Article],
    config: Config,
    store: NewsStore,
) -> list[Article]:
    dedup_window = config.dedup.dedup_window_days
    sent_urls = store.get_sent_urls(dedup_window)
    sent_titles_raw = store.get_sent_titles(dedup_window)
    sent_norm_titles = [(normalize_title(t), u) for t, u in sent_titles_raw]

    seen_norm_titles: dict[str, Article] = {}
    result = []

    for article in articles:
        # URL dedup
        if article.url in sent_urls:
            continue

        # Within-session title dedup
        norm = article.normalized_title
        if norm in seen_norm_titles:
            continue

        # Cross-session title similarity dedup
        is_dup = False
        for st, su in sent_norm_titles:
            sim = title_similarity(norm, st)
            if sim >= config.dedup.title_similarity_threshold:
                is_dup = True
                break

        if is_dup:
            continue

        seen_norm_titles[norm] = article
        result.append(article)

    return result
