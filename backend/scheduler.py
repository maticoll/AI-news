import logging
from datetime import datetime, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def setup_scheduler(pipeline_fn, session_factory) -> AsyncIOScheduler:
    """
    Create and return a configured scheduler.
    pipeline_fn: async callable(db: Session)
    session_factory: callable that returns a DB session
    """
    scheduler = AsyncIOScheduler()

    async def job():
        db: Session = session_factory()
        try:
            await pipeline_fn(db)
        except Exception as e:
            logger.error(f"Scheduler job failed: {e}")
        finally:
            db.close()

    scheduler.add_job(
        job,
        trigger="interval",
        hours=2,
        max_instances=1,
        id="scrape_and_summarize",
        next_run_time=datetime.now(timezone.utc),  # run immediately on startup
    )
    return scheduler
