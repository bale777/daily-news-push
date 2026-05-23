import logging
import logging.handlers
import os
from pathlib import Path


def setup_logging(level: str = "INFO", file_path: str = "logs/news_push.log",
                  max_bytes: int = 5 * 1024 * 1024, backup_count: int = 5):
    log_dir = Path(file_path).parent
    os.makedirs(log_dir, exist_ok=True)

    logger = logging.getLogger("news_pusher")
    logger.setLevel(logging.DEBUG)

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    console = logging.StreamHandler()
    console.setLevel(getattr(logging, level.upper(), logging.INFO))
    console.setFormatter(fmt)
    logger.addHandler(console)

    # Rotating file handler
    fh = logging.handlers.RotatingFileHandler(
        file_path, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    # Suppress noisy third-party loggers
    for name in ("feedparser", "urllib3", "chardet"):
        logging.getLogger(name).setLevel(logging.WARNING)

    return logger
