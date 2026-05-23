import signal
import sys

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from news_pusher.run_once import run_once


def start_scheduler(config, log):
    tz = config.schedule.timezone
    times = config.schedule.times

    scheduler = BackgroundScheduler(timezone=tz)
    scheduler._daemon = False

    for t in times:
        hour, minute = t.split(":")
        trigger = CronTrigger(hour=int(hour), minute=int(minute), timezone=tz)
        session = "morning" if int(hour) < 14 else "evening"
        scheduler.add_job(
            run_once,
            trigger=trigger,
            args=[config, log, session, False],
            id=f"push_{t}",
            name=f"News push at {t} ({session})",
            misfire_grace_time=600,
        )
        log.info(f"Scheduled push at {t} ({session})")

    def _shutdown(signum, frame):
        log.info("Received shutdown signal, stopping scheduler...")
        scheduler.shutdown(wait=False)
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    scheduler.start()
    log.info("Scheduler started. Press Ctrl+C to stop.")

    try:
        # Windows-compatible wait: sleep in a loop instead of signal.pause()
        import time
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        _shutdown(None, None)
