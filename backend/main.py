import asyncio
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Depends, Header, HTTPException, Query, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.database import init_db, get_db, get_session_factory, get_engine
from backend.models import Article
from backend.scraper import scrape_all
from backend.gmail_reader import read_newsletters
from backend.summarizer import summarize_pending, load_categories
from backend.scheduler import setup_scheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

REFRESH_TOKEN = os.getenv("REFRESH_SECRET_TOKEN", "")
SOURCES = [
    "Anthropic",
    "OpenAI",
    "Google DeepMind",
    "Google Research",
    "Mistral",
    "TechCrunch",
    "VentureBeat",
    "MIT Technology Review",
    "The Batch",
    "arXiv",
    "Newsletter",
]

limiter = Limiter(key_func=get_remote_address)


async def run_pipeline(db: Session) -> None:
    """Full scrape + summarize pipeline. Called by scheduler and /api/refresh."""
    await scrape_all(db)
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, read_newsletters, db)
    await loop.run_in_executor(None, summarize_pending, db)


@asynccontextmanager
async def lifespan(app: FastAPI):
    engine = get_engine()
    init_db(engine)
    session_factory = get_session_factory(engine)
    app.state.session_factory = session_factory

    scheduler = setup_scheduler(run_pipeline, session_factory)
    scheduler.start()
    logger.info("Scheduler started")

    yield

    scheduler.shutdown()
    logger.info("Scheduler stopped")


def get_db_from_state(request: Request):
    db = request.app.state.session_factory()
    try:
        yield db
    finally:
        db.close()


app = FastAPI(title="AI News Hub", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# ── API routes ─────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/articles")
@limiter.limit("60/minute")
def get_articles(
    request: Request,
    source: str | None = None,
    category: str | None = None,
    q: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    sort: str = Query(default="desc"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db_from_state),
):
    query = db.query(Article)
    if source:
        query = query.filter(Article.source == source)
    if category:
        query = query.filter(Article.category_id == category)
    if q:
        query = query.filter(Article.title.ilike(f"%{q}%"))
    if date_from:
        try:
            df = datetime.fromisoformat(date_from).replace(tzinfo=timezone.utc)
            query = query.filter(Article.published_at >= df)
        except ValueError:
            pass
    if date_to:
        try:
            dt = datetime.fromisoformat(date_to).replace(tzinfo=timezone.utc)
            # Include the full day_to
            dt = dt.replace(hour=23, minute=59, second=59)
            query = query.filter(Article.published_at <= dt)
        except ValueError:
            pass

    if sort == "asc":
        query = query.order_by(Article.published_at.asc())
    else:
        query = query.order_by(Article.published_at.desc())

    articles = query.offset(offset).limit(limit).all()
    return [
        {
            "id": a.id,
            "title": a.title,
            "url": a.url,
            "source": a.source,
            "source_type": a.source_type,
            "published_at": a.published_at.isoformat() if a.published_at else None,
            "ai_summary": a.ai_summary or (a.excerpt if a.source_type == "email" else None),
            "category_id": a.category_id,
            "is_processed": a.is_processed,
        }
        for a in articles
    ]


@app.get("/api/stats")
@limiter.limit("60/minute")
def get_stats(request: Request, db: Session = Depends(get_db_from_state)):
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=6)

    total = db.query(func.count(Article.id)).scalar() or 0
    today_count = db.query(func.count(Article.id)).filter(
        Article.published_at >= today_start
    ).scalar() or 0
    week_count = db.query(func.count(Article.id)).filter(
        Article.published_at >= week_start
    ).scalar() or 0
    processed = db.query(func.count(Article.id)).filter(
        Article.is_processed == True  # noqa: E712
    ).scalar() or 0

    # By category
    cat_rows = (
        db.query(Article.category_id, func.count(Article.id))
        .filter(Article.category_id != None)  # noqa: E711
        .group_by(Article.category_id)
        .order_by(func.count(Article.id).desc())
        .all()
    )

    # By source (top 10)
    source_rows = (
        db.query(Article.source, func.count(Article.id))
        .group_by(Article.source)
        .order_by(func.count(Article.id).desc())
        .limit(10)
        .all()
    )

    # Articles per day for the last 7 days
    daily_counts = []
    for i in range(6, -1, -1):
        day_start = today_start - timedelta(days=i)
        day_end = day_start + timedelta(days=1)
        count = db.query(func.count(Article.id)).filter(
            Article.published_at >= day_start,
            Article.published_at < day_end,
        ).scalar() or 0
        daily_counts.append({
            "date": day_start.strftime("%Y-%m-%d"),
            "label": day_start.strftime("%d/%m"),
            "count": count,
        })

    processed_pct = round((processed / total * 100)) if total > 0 else 0

    return {
        "total": total,
        "today": today_count,
        "this_week": week_count,
        "processed": processed,
        "processed_pct": processed_pct,
        "by_category": [{"id": k, "count": v} for k, v in cat_rows],
        "by_source": [{"name": k, "count": v} for k, v in source_rows],
        "articles_per_day": daily_counts,
    }


@app.get("/api/sources")
@limiter.limit("60/minute")
def get_sources(request: Request):
    return SOURCES


@app.get("/api/categories")
@limiter.limit("60/minute")
def get_categories(request: Request):
    return load_categories()


@app.post("/api/refresh")
@limiter.limit("5/minute")
async def refresh(
    request: Request,
    x_refresh_token: str | None = Header(default=None),
    db: Session = Depends(get_db_from_state),
):
    if not REFRESH_TOKEN or x_refresh_token != REFRESH_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid or missing refresh token")
    await run_pipeline(db)
    return {"status": "ok"}


# ── Static frontend ────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return FileResponse("frontend/index.html")


app.mount("/static", StaticFiles(directory="frontend"), name="static")
