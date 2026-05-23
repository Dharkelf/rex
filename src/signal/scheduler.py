"""APScheduler-based scheduler for the 4 daily signal triggers."""

from __future__ import annotations

import logging

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from src.signal.generator import (
    EveningSignal,
    OvernightGapSignal,
    UsOpenLagSignal,
    XetraOpenSignal,
)
from src.utils.config import load_config

logger = logging.getLogger(__name__)
_TZ = "Europe/Vienna"


def _run(cls: type) -> None:
    try:
        output = cls().run()
        # output already logged inside generator
    except Exception as exc:
        logger.error("Signal job %s failed: %s", cls.__name__, exc, exc_info=True)


def start_scheduler() -> None:
    cfg = load_config()["signal"]["triggers"]
    scheduler = BlockingScheduler(timezone=_TZ)

    def _time(key: str) -> tuple[int, int]:
        t = cfg[key]["time_cet"]
        h, m = t.split(":")
        return int(h), int(m)

    h, m = _time("overnight_gap")
    scheduler.add_job(lambda: _run(OvernightGapSignal), CronTrigger(hour=h, minute=m, timezone=_TZ))

    h, m = _time("xetra_open")
    scheduler.add_job(lambda: _run(XetraOpenSignal), CronTrigger(hour=h, minute=m, timezone=_TZ))

    h, m = _time("us_open_lag")
    scheduler.add_job(lambda: _run(UsOpenLagSignal), CronTrigger(hour=h, minute=m, timezone=_TZ))

    h, m = _time("evening")
    scheduler.add_job(lambda: _run(EveningSignal), CronTrigger(hour=h, minute=m, timezone=_TZ))

    logger.info(
        "Scheduler started — triggers at %s / %s / %s / %s CET (Mon–Fri)",
        cfg["overnight_gap"]["time_cet"],
        cfg["xetra_open"]["time_cet"],
        cfg["us_open_lag"]["time_cet"],
        cfg["evening"]["time_cet"],
    )
    scheduler.start()
