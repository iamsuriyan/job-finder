"""Scheduler loop with configurable interval, jitter, and graceful shutdown."""

from __future__ import annotations

import logging
import random
import signal
import sys
import threading
from typing import Any

from fundwatch.db import Database
from fundwatch.models import Settings
from fundwatch.notifiers import Notifier
from fundwatch.pipeline import run_cycle

logger = logging.getLogger(__name__)


class Scheduler:
    """Runs pipeline cycles on a recurring schedule with jitter and signal handling."""

    def __init__(
        self,
        settings: Settings,
        db: Database,
        notifiers: list[Notifier] | None = None,
    ) -> None:
        self.settings = settings
        self.db = db
        self.notifiers = notifiers or []
        self._stop_event = threading.Event()

    def stop(self, *args: Any) -> None:
        """Signal scheduler to gracefully shut down after the current cycle."""
        logger.info("Shutdown signal received. Finishing active cycle then exiting...")
        self._stop_event.set()

    def run_forever(self) -> None:
        """Execute cycle repeatedly until SIGINT or SIGTERM is received."""
        # Register signals
        signal.signal(signal.SIGINT, self.stop)
        signal.signal(signal.SIGTERM, self.stop)

        interval_sec = self.settings.poll_interval_minutes * 60
        jitter_range = self.settings.jitter_seconds

        logger.info(
            "Scheduler started: interval=%d min, jitter=±%ds",
            self.settings.poll_interval_minutes,
            jitter_range,
        )

        while not self._stop_event.is_set():
            logger.info("Starting scheduled cycle...")
            try:
                run_cycle(
                    settings=self.settings,
                    db=self.db,
                    notifiers=self.notifiers,
                )
            except Exception as exc:
                logger.error("Unhandled error during poll cycle: %s", exc, exc_info=True)

            if self._stop_event.is_set():
                break

            jitter = random.uniform(-jitter_range, jitter_range)
            sleep_time = max(10.0, interval_sec + jitter)
            logger.info("Sleeping %.1f seconds until next cycle...", sleep_time)

            # Wait on stop_event so shutdown is immediate if signaled during sleep
            interrupted = self._stop_event.wait(timeout=sleep_time)
            if interrupted:
                break

        logger.info("Scheduler exited cleanly.")
        sys.exit(0)
