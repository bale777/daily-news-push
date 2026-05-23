from news_pusher.config import FeedSource


def get_enabled_feeds(feeds: dict[str, list[FeedSource]]) -> list[FeedSource]:
    result = []
    for category_sources in feeds.values():
        for src in category_sources:
            if src.enabled:
                result.append(src)
    return result


def get_feeds_by_category(feeds: dict[str, list[FeedSource]]) -> dict[str, list[FeedSource]]:
    return {
        cat: [s for s in sources if s.enabled]
        for cat, sources in feeds.items()
    }
