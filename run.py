import argparse
import os
import sys
from pathlib import Path

# Ensure we work from the project directory regardless of where run.py is called from
PROJECT_DIR = Path(__file__).parent.resolve()
os.chdir(str(PROJECT_DIR))
sys.path.insert(0, str(PROJECT_DIR))

from news_pusher.config import load_config
from news_pusher.logger import setup_logging


def main():
    parser = argparse.ArgumentParser(
        description="每日新闻推送系统 - Daily News Push"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--daemon", action="store_true",
        help="启动定时调度器，在配置的时间自动推送"
    )
    group.add_argument(
        "--once", action="store_true",
        help="立即执行一次抓取和推送"
    )
    parser.add_argument(
        "--session", choices=["morning", "evening"],
        help="指定推送时段（用于标题前缀）"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="抓取并格式化，但不实际推送"
    )
    parser.add_argument(
        "--config", type=str, default=None,
        help="配置文件路径"
    )

    args = parser.parse_args()

    config = load_config(args.config)
    log = setup_logging(
        level=config.logging.level,
        file_path=config.logging.file,
        max_bytes=config.logging.max_bytes,
        backup_count=config.logging.backup_count,
    )

    log.info("Daily News Push starting...")

    if args.once:
        from news_pusher.run_once import run_once
        session = args.session or _guess_session(config)
        run_once(config, log, session=session, dry_run=args.dry_run)
    elif args.daemon:
        from news_pusher.scheduler import start_scheduler
        start_scheduler(config, log)


def _guess_session(config) -> str:
    from datetime import datetime
    from zoneinfo import ZoneInfo
    try:
        tz = ZoneInfo(config.schedule.timezone)
    except Exception:
        tz = None
    now = datetime.now(tz)
    return "morning" if now.hour < 14 else "evening"


if __name__ == "__main__":
    main()
