import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Depends, Header, HTTPException, Query, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
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
SOURCES = ["Anthropic", "OpenAI", "Google DeepMind", "Mistral", "Newsletter"]

limiter = Limiter(key_func=get_remote_address)


async def run_pipeline(db: Session) -> None:
    """Full scrape + summarize pipeline. Called by scheduler and /api/refresh."""
    await scrape_all(db)
    read_newsletters(db)
    summarize_pending(db)


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
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db_from_state),
):
    query = db.query(Article).order_by(Article.published_at.desc())
    if source:
        query = query.filter(Article.source == source)
    if category:
        query = query.filter(Article.category_id == category)
    if q:
        query = query.filter(Article.title.ilike(f"%{q}%"))
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
