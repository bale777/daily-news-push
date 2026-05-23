from datetime import datetime

from news_pusher.config import Config, FeedSource
from news_pusher.fetcher import NewsFetcher, Article
from news_pusher.dedup import dedup_articles, rank_articles
from news_pusher.formatter import format_message
from news_pusher.pusher import PushService
from news_pusher.store import NewsStore
from news_pusher.sources import get_enabled_feeds


def run_once(config: Config, log, session: str = "morning", dry_run: bool = False):
    log.info(f"Starting one-shot fetch (session={session}, dry_run={dry_run})")

    # 1. Get enabled sources
    sources = get_enabled_feeds(config.feeds)
    log.info(f"Loaded {len(sources)} enabled sources")

    # 2. Fetch
    fetcher = NewsFetcher(config)
    articles = fetcher.fetch_all(sources)
    log.info(f"Fetched {len(articles)} raw articles")

    if not articles:
        log.warning("No articles fetched, aborting")
        return

    # 3. Dedup
    store = NewsStore()
    articles = dedup_articles(articles, config, store)
    log.info(f"After dedup: {len(articles)} articles")

    # 4. Rank
    articles = rank_articles(articles, config)
    log.info(f"After ranking: {len(articles)} articles")

    if not articles:
        log.warning("No articles after dedup/ranking, aborting")
        store.close()
        return

    # 5. Format
    title, body = format_message(articles, config, session)
    log.info(f"Formatted message: {len(body)} chars")

    if dry_run:
        log.info("DRY RUN - message content:")
        print("=" * 60)
        print(f"TITLE: {title}")
        print("-" * 60)
        # Write to file to avoid Windows console encoding issues
        output_path = "data/dry_run_output.md"
        import os
        os.makedirs("data", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(f"# {title}\n\n{body}")
        log.info(f"Full output written to {output_path}")
        print(f"> Full output written to {output_path}")
        print("=" * 60)
        store.close()
        return

    # 6. Push
    pusher = PushService(config)
    success = pusher.send(title, body)
    if success:
        log.info("Push succeeded")
        store.mark_sent(articles, session)
    else:
        log.error("Push failed - check your push provider configuration")

    # 7. Cleanup
    store.cleanup(config.dedup.sent_retention_days)
    store.close()
    log.info("Done")
