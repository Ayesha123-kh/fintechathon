"""Scheduler process (run one instance): `python -m app.worker`."""

import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.core.config import settings
from app.seed.loader import load_reference_data
from app.services import gmail, jobs

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("worker")
TZ = "Asia/Karachi"


def build_scheduler() -> AsyncIOScheduler:
    s = AsyncIOScheduler(timezone=TZ, job_defaults={"coalesce": True, "max_instances": 1, "misfire_grace_time": 600})
    s.add_job(gmail.sync_all, IntervalTrigger(minutes=settings.gmail_poll_minutes), id="gmail")

    # Watchers: PSX during market hours, crypto around the clock, the rest a few times a day.
    s.add_job(jobs.wake_watchers, CronTrigger(day_of_week="mon-fri", hour="9-15", minute="40", timezone=TZ),
              args=["psx"], id="watch-psx")
    s.add_job(jobs.wake_watchers, CronTrigger(minute="5", timezone=TZ), args=["crypto"], id="watch-crypto")
    s.add_job(jobs.wake_watchers, CronTrigger(hour="10,13,16,19", minute="15", timezone=TZ),
              args=["gold_silver"], id="watch-bullion")
    s.add_job(jobs.wake_watchers, CronTrigger(day_of_week="mon-fri", hour="19,22", minute="0", timezone=TZ),
              args=["foreign_stocks"], id="watch-foreign")
    s.add_job(jobs.wake_watchers, CronTrigger(hour="11", minute="30", timezone=TZ),
              args=["pk_real_estate"], id="watch-realestate")

    s.add_job(jobs.wake_researchers, CronTrigger(hour="8,16", minute="0", timezone=TZ), id="research")
    s.add_job(jobs.wake_analysts, CronTrigger(hour="9,17", minute="30", timezone=TZ), id="analysis")

    s.add_job(jobs.screen_merchants, IntervalTrigger(minutes=15), id="merchant-screen")
    s.add_job(jobs.wake_deal_scout, IntervalTrigger(hours=2), id="deal-scout")
    s.add_job(jobs.wake_deal_crawler, CronTrigger(hour="*/3", minute="20", timezone=TZ), id="deal-crawl")
    s.add_job(jobs.wake_deal_curator, CronTrigger(hour="3", minute="0", timezone=TZ), id="deal-curate")

    s.add_job(jobs.weekly_motivation, CronTrigger(day_of_week="fri", hour="18", minute="0", timezone=TZ), id="motivation")
    s.add_job(jobs.weekly_review, CronTrigger(day_of_week="sun", hour="19", minute="0", timezone=TZ), id="review")
    s.add_job(jobs.sadqah_reminders, CronTrigger(day_of_week="fri", hour="12", minute="0", timezone=TZ),
              args=["friday"], id="sadqah-friday")
    s.add_job(jobs.sadqah_reminders, CronTrigger(day_of_week="mon", hour="10", minute="0", timezone=TZ),
              args=["weekly"], id="sadqah-weekly")
    s.add_job(jobs.sadqah_reminders, CronTrigger(day="1", hour="10", minute="0", timezone=TZ),
              args=["monthly"], id="sadqah-monthly")
    s.add_job(jobs.month_end_leftover, CronTrigger(hour="23", minute="30", timezone=TZ), id="month-end")
    s.add_job(jobs.overspend_nudge, CronTrigger(hour="20", minute="30", timezone=TZ), id="overspend")
    return s


async def main() -> None:
    settings.check_production()
    await load_reference_data()
    scheduler = build_scheduler()
    scheduler.start()
    log.info("scheduler started with %d jobs", len(scheduler.get_jobs()))
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
