import logging

from apscheduler.schedulers.background import BackgroundScheduler

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def sync_prices_daily() -> None:
    logger.info("Job sync_prices_daily triggered, not yet implemented")


def ingest_channels_weekly() -> None:
    logger.info("Job ingest_channels_weekly triggered, not yet implemented")


def backup_monthly() -> None:
    logger.info("Job backup_monthly triggered, not yet implemented")


scheduler.add_job(
    sync_prices_daily,
    trigger="cron",
    hour=23,
    minute=0,
    id="sync_prices_daily",
    replace_existing=True,
)

scheduler.add_job(
    ingest_channels_weekly,
    trigger="cron",
    day_of_week="sun",
    hour=22,
    minute=0,
    id="ingest_channels_weekly",
    replace_existing=True,
)

scheduler.add_job(
    backup_monthly,
    trigger="cron",
    day=1,
    hour=2,
    minute=0,
    id="backup_monthly",
    replace_existing=True,
)
