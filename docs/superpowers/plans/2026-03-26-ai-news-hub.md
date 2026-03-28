# AI News Hub — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a public web app that scrapes AI news from official blogs and Gmail newsletters, summarizes and categorizes articles with Claude Haiku, and serves them via a FastAPI backend with a themeable vanilla JS frontend.

**Architecture:** Python FastAPI backend stores articles in SQLite via SQLAlchemy. Articles are collected from RSS feeds, Playwright-rendered pages, and Gmail newsletters. Claude Haiku processes each article once — returning a Spanish 2-sentence summary and a category ID — in a single API call. APScheduler triggers the full pipeline every 2 hours. FastAPI also serves the static frontend directly.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy, SQLite, httpx, feedparser, playwright, anthropic SDK, APScheduler, slowapi, google-api-python-client, BeautifulSoup4, pytest, pytest-asyncio, respx

> **Note on spec deviation:** The spec omits an `excerpt` column from the DB schema, but the summarizer needs the article excerpt at processing time. This plan adds `excerpt TEXT` to the articles table — it is the only schema addition beyond the spec.

---

## File Map

| File | Responsibility |
|---|---|
| `backend/database.py` | SQLAlchemy engine, session factory, `Base`, `init_db()`, `get_db()` |
| `backend/models.py` | `Article` ORM model |
| `backend/scraper.py` | `parse_rss_feed()`, `scrape_anthropic()`, `parse_*_articles(html)`, `fetch_page_html()`, `scrape_all(db)` |
| `backend/gmail_reader.py` | `build_gmail_service()`, `parse_gmail_message()`, `read_newsletters(db)`, `--auth` CLI mode |
| `backend/summarizer.py` | `load_categories()`, `call_claude()`, `summarize_pending(db)` |
| `backend/scheduler.py` | `setup_scheduler(app, db_factory)` — returns configured `AsyncIOScheduler` |
| `backend/main.py` | FastAPI app, lifespan, all API endpoints, rate limiting, static file mount |
| `frontend/themes.css` | 3 CSS themes: light (default), dark, gradient |
| `frontend/index.html` | HTML shell — navbar, hero, filter bars, cards grid, footer |
| `frontend/app.js` | Fetch, search, dual filters, pagination, theme switcher |
| `categories.json` | Category definitions (user-editable) |
| `.env.example` | Documented env var template |
| `requirements.txt` | All runtime + test dependencies |
| `tests/conftest.py` | Shared fixtures: in-memory DB session |
| `tests/test_database.py` | DB init, insert, dedup constraint |
| `tests/test_scraper.py` | RSS parse, Playwright HTML parse functions |
| `tests/test_gmail_reader.py` | Gmail message parsing |
| `tests/test_summarizer.py` | Claude response parsing, retry logic |
| `tests/test_api.py` | All API endpoints via TestClient |

---

## Task 1: Project Setup

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `categories.json`
- Create: `backend/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Create: `pytest.ini`

- [ ] **Step 1: Create directory structure**

```bash
cd "C:/Users/Usuario/OneDrive/Desktop/CLAUDIO/app ia"
mkdir -p backend frontend tests
```

- [ ] **Step 2: Create `requirements.txt`**

```
fastapi==0.115.0
uvicorn[standard]==0.30.6
httpx==0.27.2
feedparser==6.0.11
beautifulsoup4==4.12.3
playwright==1.47.0
sqlalchemy==2.0.35
apscheduler==3.10.4
anthropic==0.34.2
slowapi==0.1.9
python-dotenv==1.0.1
google-api-python-client==2.147.0
google-auth-httplib2==0.2.0
google-auth-oauthlib==1.2.1
# test deps
pytest==8.3.3
pytest-asyncio==0.24.0
respx==0.21.1
```

- [ ] **Step 3: Install dependencies and Playwright browser**

```bash
pip install -r requirements.txt
playwright install chromium
```

Expected: no errors. `playwright install chromium` downloads ~130MB.

- [ ] **Step 4: Create `.env.example`**

```
ANTHROPIC_API_KEY=your_key_here
REFRESH_SECRET_TOKEN=choose_a_random_secret
GMAIL_CREDENTIALS_PATH=./credentials.json
GMAIL_TOKEN_PATH=./gmail_token.json
NEWSLETTER_SENDERS=sender1@example.com,sender2@example.com
DATABASE_URL=sqlite:///./ainews.db
CATEGORIES_PATH=./categories.json
```

- [ ] **Step 5: Copy to `.env` and fill in your real values**

```bash
cp .env.example .env
```

- [ ] **Step 6: Create `categories.json`**

```json
[
  {
    "id": "modelos",
    "name": "Modelos de IA",
    "description": "Lanzamientos, actualizaciones y benchmarks de modelos de lenguaje, visión o multimodales"
  },
  {
    "id": "agentes",
    "name": "Agentes",
    "description": "Agentes autónomos, multi-agente, herramientas de automatización y workflows"
  },
  {
    "id": "plugins",
    "name": "Plugins y Extensiones",
    "description": "Plugins, extensiones, integraciones con apps de terceros"
  },
  {
    "id": "webdesign",
    "name": "Web & Diseño",
    "description": "Diseño web, UI/UX, generación de interfaces, herramientas de diseño con IA"
  },
  {
    "id": "creatividad",
    "name": "Ideas Creativas",
    "description": "Generación de contenido creativo, arte, música, escritura, storytelling con IA"
  },
  {
    "id": "investigacion",
    "name": "Investigación",
    "description": "Papers, avances científicos, seguridad en IA, alineamiento"
  },
  {
    "id": "otros",
    "name": "Otros",
    "description": "Temas que no encajan en ninguna categoría anterior"
  }
]
```

- [ ] **Step 7: Create `pytest.ini`**

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
```

- [ ] **Step 8: Create empty `__init__.py` files**

```bash
touch backend/__init__.py tests/__init__.py
```

- [ ] **Step 9: Create `tests/conftest.py`**

```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.database import Base
import backend.models  # noqa: F401 — registers models with Base


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(engine)
```

- [ ] **Step 10: Create `.gitignore`**

```
.env
gmail_token.json
ainews.db
__pycache__/
*.pyc
.pytest_cache/
```

- [ ] **Step 11: Commit**

```bash
git init
git add requirements.txt .env.example .gitignore categories.json pytest.ini backend/__init__.py tests/__init__.py tests/conftest.py
git commit -m "feat: initial project setup — deps, config, test scaffolding"
```

---

## Task 2: Database Models

**Files:**
- Create: `backend/database.py`
- Create: `backend/models.py`
- Create: `tests/test_database.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_database.py
from datetime import datetime, timezone
import pytest
from sqlalchemy.exc import IntegrityError
from backend.models import Article


def test_create_article(db_session):
    article = Article(
        title="Test Article",
        url="https://example.com/1",
        source="Anthropic",
        source_type="web",
        published_at=datetime.now(timezone.utc),
        excerpt="Some text here",
        scraped_at=datetime.now(timezone.utc),
    )
    db_session.add(article)
    db_session.commit()
    assert article.id is not None
    assert article.is_processed is False
    assert article.retry_count == 0
    assert article.ai_summary is None
    assert article.category_id is None


def test_url_uniqueness_constraint(db_session):
    now = datetime.now(timezone.utc)
    a1 = Article(title="A", url="https://example.com/dup", source="X",
                 source_type="web", published_at=now, excerpt="", scraped_at=now)
    a2 = Article(title="B", url="https://example.com/dup", source="X",
                 source_type="web", published_at=now, excerpt="", scraped_at=now)
    db_session.add(a1)
    db_session.commit()
    db_session.add(a2)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_init_db_creates_tables():
    from sqlalchemy import create_engine, inspect
    from backend.database import Base, init_db
    import backend.models  # noqa
    engine = create_engine("sqlite:///:memory:")
    init_db(engine)
    inspector = inspect(engine)
    assert "articles" in inspector.get_table_names()
```

- [ ] **Step 2: Run tests — expect failure**

```bash
cd "C:/Users/Usuario/OneDrive/Desktop/CLAUDIO/app ia"
python -m pytest tests/test_database.py -v
```

Expected: `ImportError` or `ModuleNotFoundError` — `backend.database` doesn't exist yet.

- [ ] **Step 3: Create `backend/database.py`**

```python
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase


class Base(DeclarativeBase):
    pass


def get_engine(url: str | None = None):
    database_url = url or os.getenv("DATABASE_URL", "sqlite:///./ainews.db")
    return create_engine(database_url, connect_args={"check_same_thread": False})


def init_db(engine=None):
    """Create all tables. Pass engine for testing; uses default engine otherwise."""
    from backend import models  # noqa: F401 — registers models
    target = engine or get_engine()
    Base.metadata.create_all(bind=target)


def get_session_factory(engine=None):
    target = engine or get_engine()
    return sessionmaker(autocommit=False, autoflush=False, bind=target)


def get_db(session_factory=None):
    """FastAPI dependency — yields a DB session."""
    factory = session_factory or get_session_factory()
    db = factory()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 4: Create `backend/models.py`**

```python
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from backend.database import Base


class Article(Base):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(Text, nullable=False)
    url = Column(String(2048), unique=True, nullable=False)
    source = Column(String(100), nullable=False)
    source_type = Column(String(10), nullable=False)   # "web" or "email"
    published_at = Column(DateTime, nullable=False)
    excerpt = Column(Text, nullable=True)               # first 500 chars; used by summarizer
    ai_summary = Column(Text, nullable=True)
    category_id = Column(String(50), nullable=True)
    scraped_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    is_processed = Column(Boolean, nullable=False, default=False)
    retry_count = Column(Integer, nullable=False, default=0)
```

- [ ] **Step 5: Run tests — expect pass**

```bash
python -m pytest tests/test_database.py -v
```

Expected: all 3 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/database.py backend/models.py tests/test_database.py
git commit -m "feat: database models and session setup"
```

---

## Task 3: RSS Scraper (Anthropic)

**Files:**
- Create: `backend/scraper.py`
- Create: `tests/test_scraper.py`
- Create: `tests/fixtures/anthropic_feed.xml`

- [ ] **Step 1: Create RSS fixture file**

Create `tests/fixtures/` directory and save this as `tests/fixtures/anthropic_feed.xml`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Anthropic</title>
    <link>https://www.anthropic.com</link>
    <item>
      <title>Claude 3.5 Sonnet release</title>
      <link>https://www.anthropic.com/news/claude-3-5-sonnet</link>
      <pubDate>Thu, 20 Jun 2024 17:00:00 +0000</pubDate>
      <description>&lt;p&gt;Today we are releasing Claude 3.5 Sonnet, our most intelligent model to date.&lt;/p&gt;</description>
    </item>
    <item>
      <title>Another article</title>
      <link>https://www.anthropic.com/news/another</link>
      <pubDate>Wed, 19 Jun 2024 10:00:00 +0000</pubDate>
      <description>&lt;p&gt;Short article description here.&lt;/p&gt;</description>
    </item>
  </channel>
</rss>
```

- [ ] **Step 2: Write failing tests for RSS parsing**

```python
# tests/test_scraper.py
import pytest
from pathlib import Path
from backend.scraper import parse_rss_feed


FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_rss_returns_articles():
    xml = (FIXTURES / "anthropic_feed.xml").read_text(encoding="utf-8")
    articles = parse_rss_feed(xml)
    assert len(articles) == 2


def test_parse_rss_article_fields():
    xml = (FIXTURES / "anthropic_feed.xml").read_text(encoding="utf-8")
    articles = parse_rss_feed(xml)
    first = articles[0]
    assert first["title"] == "Claude 3.5 Sonnet release"
    assert first["url"] == "https://www.anthropic.com/news/claude-3-5-sonnet"
    assert first["source"] == "Anthropic"
    assert first["source_type"] == "web"
    assert first["published_at"] is not None
    assert "Sonnet" in first["excerpt"] or first["excerpt"] == ""


def test_parse_rss_missing_pubdate():
    xml = """<?xml version="1.0"?><rss version="2.0"><channel>
      <item><title>No date</title><link>https://example.com/x</link></item>
    </channel></rss>"""
    articles = parse_rss_feed(xml)
    assert len(articles) == 1
    assert articles[0]["published_at"] is None  # will fall back to scraped_at
```

- [ ] **Step 3: Run tests — expect failure**

```bash
python -m pytest tests/test_scraper.py -v
```

Expected: `ImportError` — `backend.scraper` doesn't exist.

- [ ] **Step 4: Create `backend/scraper.py` with `parse_rss_feed()`**

```python
import logging
from datetime import datetime, timezone

import httpx
import feedparser
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from backend.models import Article

logger = logging.getLogger(__name__)


# ── RSS ────────────────────────────────────────────────────────────────────────

def parse_rss_feed(xml_content: str) -> list[dict]:
    """Parse RSS XML string → list of article dicts. Pure function (no I/O)."""
    feed = feedparser.parse(xml_content)
    articles = []
    for entry in feed.entries:
        published_at = None
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            published_at = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)

        excerpt = ""
        raw = getattr(entry, "summary", "") or ""
        if raw:
            excerpt = BeautifulSoup(raw, "html.parser").get_text()[:500]

        articles.append({
            "title": entry.get("title", ""),
            "url": entry.get("link", ""),
            "source": "Anthropic",
            "source_type": "web",
            "published_at": published_at,
            "excerpt": excerpt,
        })
    return articles


async def scrape_anthropic() -> list[dict]:
    """Fetch Anthropic RSS and return parsed article dicts."""
    url = "https://www.anthropic.com/rss.xml"
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(url)
        response.raise_for_status()
    return parse_rss_feed(response.text)
```

- [ ] **Step 5: Run tests — expect pass**

```bash
python -m pytest tests/test_scraper.py -v
```

Expected: 3 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/scraper.py tests/test_scraper.py tests/fixtures/
git commit -m "feat: Anthropic RSS scraper with unit tests"
```

---

## Task 4: Playwright Scrapers (OpenAI, DeepMind, Mistral)

**Files:**
- Modify: `backend/scraper.py` — add Playwright fetch + per-site parsers + `scrape_all()`
- Modify: `tests/test_scraper.py` — add HTML parse tests
- Create: `tests/fixtures/openai_news.html`, `tests/fixtures/deepmind_news.html`, `tests/fixtures/mistral_news.html`

> **Important:** The CSS selectors for each site must be verified by visiting the actual pages before implementing. The selectors below are starting points — inspect the live DOM and adjust as needed. Sites change their markup; the tests use fixture HTML so they stay stable regardless.

- [ ] **Step 1: Capture fixture HTML from each site**

Run this once to capture real page HTML for tests:

```python
# run_once: save_fixtures.py  (delete after use)
import asyncio
from playwright.async_api import async_playwright

async def save(url, filename):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url, wait_until="networkidle", timeout=30000)
        html = await page.content()
        await browser.close()
    with open(f"tests/fixtures/{filename}", "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Saved {filename}")

async def main():
    await save("https://openai.com/news", "openai_news.html")
    await save("https://deepmind.google/research/publications", "deepmind_news.html")
    await save("https://mistral.ai/news", "mistral_news.html")

asyncio.run(main())
```

```bash
python save_fixtures.py
```

Then inspect the saved HTML files to find article card selectors before continuing.

- [ ] **Step 2: Write failing parse tests (update selectors after inspecting fixtures)**

```python
# Add to tests/test_scraper.py
from backend.scraper import parse_openai_articles, parse_deepmind_articles, parse_mistral_articles


def test_parse_openai_returns_articles():
    html = (FIXTURES / "openai_news.html").read_text(encoding="utf-8")
    articles = parse_openai_articles(html)
    assert len(articles) > 0
    assert articles[0]["source"] == "OpenAI"
    assert articles[0]["source_type"] == "web"
    assert articles[0]["url"].startswith("http")
    assert len(articles[0]["title"]) > 0


def test_parse_deepmind_returns_articles():
    html = (FIXTURES / "deepmind_news.html").read_text(encoding="utf-8")
    articles = parse_deepmind_articles(html)
    assert len(articles) > 0
    assert articles[0]["source"] == "Google DeepMind"


def test_parse_mistral_returns_articles():
    html = (FIXTURES / "mistral_news.html").read_text(encoding="utf-8")
    articles = parse_mistral_articles(html)
    assert len(articles) > 0
    assert articles[0]["source"] == "Mistral"
```

- [ ] **Step 3: Run tests — expect failure**

```bash
python -m pytest tests/test_scraper.py::test_parse_openai_returns_articles -v
```

Expected: `ImportError` — functions not defined yet.

- [ ] **Step 4: Add Playwright scrapers to `backend/scraper.py`**

Add after the RSS section:

```python
# ── Playwright helpers ─────────────────────────────────────────────────────────

async def fetch_page_html(url: str) -> str:
    """Fetch JS-rendered page HTML using headless Chromium."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url, wait_until="networkidle", timeout=30000)
        html = await page.content()
        await browser.close()
    return html


def _extract_text(el) -> str:
    return el.get_text(strip=True) if el else ""


def _abs_url(href: str, base: str) -> str:
    if href.startswith("http"):
        return href
    from urllib.parse import urljoin
    return urljoin(base, href)


# ── Per-site parsers (pure functions — no network I/O) ────────────────────────

def parse_openai_articles(html: str) -> list[dict]:
    """
    Parse OpenAI news page.
    Inspect tests/fixtures/openai_news.html to verify selectors.
    Typical structure: <a> tags linking to /index/* with a heading inside.
    """
    soup = BeautifulSoup(html, "html.parser")
    articles = []
    seen_urls = set()
    # Adjust selector after inspecting the fixture
    for card in soup.select("a[href]"):
        href = card.get("href", "")
        if "/index/" not in href and "/research/" not in href:
            continue
        title_el = card.find(["h2", "h3", "h4"])
        if not title_el:
            continue
        title = _extract_text(title_el)
        url = _abs_url(href, "https://openai.com")
        if not title or url in seen_urls:
            continue
        seen_urls.add(url)
        articles.append({
            "title": title,
            "url": url,
            "source": "OpenAI",
            "source_type": "web",
            "published_at": None,
            "excerpt": "",
        })
    return articles


def parse_deepmind_articles(html: str) -> list[dict]:
    """
    Parse Google DeepMind publications page.
    Inspect tests/fixtures/deepmind_news.html to verify selectors.
    """
    soup = BeautifulSoup(html, "html.parser")
    articles = []
    seen_urls = set()
    for card in soup.select("a[href]"):
        href = card.get("href", "")
        if "/research/" not in href and "/discover/" not in href:
            continue
        title_el = card.find(["h2", "h3", "h4", "p"])
        if not title_el:
            continue
        title = _extract_text(title_el)
        url = _abs_url(href, "https://deepmind.google")
        if not title or url in seen_urls or len(title) < 10:
            continue
        seen_urls.add(url)
        articles.append({
            "title": title,
            "url": url,
            "source": "Google DeepMind",
            "source_type": "web",
            "published_at": None,
            "excerpt": "",
        })
    return articles


def parse_mistral_articles(html: str) -> list[dict]:
    """
    Parse Mistral news page.
    Inspect tests/fixtures/mistral_news.html to verify selectors.
    """
    soup = BeautifulSoup(html, "html.parser")
    articles = []
    seen_urls = set()
    for card in soup.select("a[href]"):
        href = card.get("href", "")
        if "/news/" not in href and "/blog/" not in href:
            continue
        title_el = card.find(["h2", "h3", "h4"])
        if not title_el:
            continue
        title = _extract_text(title_el)
        url = _abs_url(href, "https://mistral.ai")
        if not title or url in seen_urls:
            continue
        seen_urls.add(url)
        articles.append({
            "title": title,
            "url": url,
            "source": "Mistral",
            "source_type": "web",
            "published_at": None,
            "excerpt": "",
        })
    return articles


# ── DB insert helper ───────────────────────────────────────────────────────────

def save_articles(articles: list[dict], db: Session) -> int:
    """Insert new articles into DB. Skips duplicates. Returns count inserted."""
    now = datetime.now(timezone.utc)
    inserted = 0
    for data in articles:
        article = Article(
            title=data["title"],
            url=data["url"],
            source=data["source"],
            source_type=data["source_type"],
            published_at=data.get("published_at") or now,
            excerpt=data.get("excerpt", ""),
            scraped_at=now,
        )
        try:
            db.add(article)
            db.commit()
            inserted += 1
        except IntegrityError:
            db.rollback()  # duplicate URL — skip
    return inserted


# ── Orchestrator ───────────────────────────────────────────────────────────────

async def scrape_all(db: Session) -> None:
    """Run all web scrapers and save to DB. Continues on per-source failures."""
    # Anthropic RSS
    try:
        articles = await scrape_anthropic()
        count = save_articles(articles, db)
        logger.info(f"Anthropic: {count} new articles")
    except Exception as e:
        logger.error(f"Anthropic scraper failed: {e}")

    # Playwright sources
    playwright_sources = [
        ("https://openai.com/news", parse_openai_articles, "OpenAI"),
        ("https://deepmind.google/research/publications", parse_deepmind_articles, "Google DeepMind"),
        ("https://mistral.ai/news", parse_mistral_articles, "Mistral"),
    ]
    for url, parser, name in playwright_sources:
        try:
            html = await fetch_page_html(url)
            articles = parser(html)
            count = save_articles(articles, db)
            logger.info(f"{name}: {count} new articles")
        except Exception as e:
            logger.error(f"{name} scraper failed: {e}")
```

- [ ] **Step 5: Run tests — expect pass (adjust selectors if needed)**

```bash
python -m pytest tests/test_scraper.py -v
```

Expected: all tests PASS. If selector tests fail, open the fixture HTML, find article link/heading structure, update selectors in the parse functions and re-run.

- [ ] **Step 6: Commit**

```bash
git add backend/scraper.py tests/test_scraper.py tests/fixtures/
git commit -m "feat: Playwright scrapers for OpenAI, DeepMind, Mistral"
```

---

## Task 5: Gmail Newsletter Reader

**Files:**
- Create: `backend/gmail_reader.py`
- Create: `tests/test_gmail_reader.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_gmail_reader.py
import hashlib
from datetime import timezone
from unittest.mock import MagicMock, patch
from backend.gmail_reader import parse_gmail_message


def _make_mock_message(subject, sender_email, sender_name, date_str, body_html, message_id="<test-id@mail>"):
    """Build a mock Gmail API message payload."""
    headers = [
        {"name": "Subject", "value": subject},
        {"name": "From", "value": f"{sender_name} <{sender_email}>"},
        {"name": "Date", "value": date_str},
        {"name": "Message-ID", "value": message_id},
    ]
    return {
        "payload": {
            "headers": headers,
            "body": {"data": ""},
            "parts": [
                {
                    "mimeType": "text/html",
                    "body": {
                        "data": __import__("base64").urlsafe_b64encode(
                            body_html.encode()
                        ).decode()
                    },
                }
            ],
        }
    }


def test_parse_gmail_message_fields():
    msg = _make_mock_message(
        subject="TLDR AI #123",
        sender_email="dan@tldrnewsletter.com",
        sender_name="TLDR AI",
        date_str="Mon, 25 Mar 2024 10:00:00 +0000",
        body_html="<p>Claude gets smarter and faster in new update from Anthropic.</p>",
    )
    result = parse_gmail_message(msg)
    assert result["title"] == "TLDR AI #123"
    assert result["source"] == "TLDR AI"
    assert result["source_type"] == "email"
    assert result["url"] == "<test-id@mail>"
    assert result["published_at"] is not None
    assert result["published_at"].tzinfo == timezone.utc
    assert "Claude" in result["excerpt"]


def test_parse_gmail_message_fallback_url():
    """When Message-ID is absent, URL is sha256 of sender+subject+date."""
    msg = _make_mock_message(
        subject="AI Weekly",
        sender_email="news@aiweekly.co",
        sender_name="AI Weekly",
        date_str="Tue, 26 Mar 2024 08:00:00 +0000",
        body_html="<p>News content</p>",
        message_id="",  # absent
    )
    result = parse_gmail_message(msg)
    expected_key = hashlib.sha256(
        ("news@aiweekly.co" + "AI Weekly" + "Tue, 26 Mar 2024 08:00:00 +0000").encode()
    ).hexdigest()
    assert result["url"] == expected_key


def test_parse_gmail_excerpt_stripped_of_html():
    msg = _make_mock_message(
        subject="Test",
        sender_email="a@b.com",
        sender_name="A",
        date_str="Mon, 25 Mar 2024 10:00:00 +0000",
        body_html="<html><body><h1>Header</h1><p>Body text content here.</p></body></html>",
    )
    result = parse_gmail_message(msg)
    assert "<" not in result["excerpt"]  # no HTML tags in excerpt
    assert "Body text" in result["excerpt"]
```

- [ ] **Step 2: Run tests — expect failure**

```bash
python -m pytest tests/test_gmail_reader.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Create `backend/gmail_reader.py`**

```python
import base64
import hashlib
import logging
import os
import sys
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from backend.scraper import save_articles

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]


def _get_header(headers: list, name: str) -> str:
    for h in headers:
        if h["name"].lower() == name.lower():
            return h["value"]
    return ""


def _decode_body(part: dict) -> str:
    data = part.get("body", {}).get("data", "")
    if not data:
        return ""
    return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")


def _extract_html_part(payload: dict) -> str:
    """Recursively find text/html part in message payload."""
    if payload.get("mimeType") == "text/html":
        return _decode_body(payload)
    for part in payload.get("parts", []):
        result = _extract_html_part(part)
        if result:
            return result
    return ""


def parse_gmail_message(message: dict) -> dict:
    """Parse a Gmail API message payload → article dict. Pure function."""
    payload = message["payload"]
    headers = payload.get("headers", [])

    subject = _get_header(headers, "Subject")
    from_header = _get_header(headers, "From")
    date_str = _get_header(headers, "Date")
    message_id = _get_header(headers, "Message-ID").strip()

    # Sender display name vs email
    sender_name = from_header
    sender_email = from_header
    if "<" in from_header:
        parts = from_header.split("<")
        sender_name = parts[0].strip().strip('"')
        sender_email = parts[1].rstrip(">").strip()

    # Deduplication key
    if message_id:
        url_key = message_id
    else:
        url_key = hashlib.sha256(
            (sender_email + subject + date_str).encode()
        ).hexdigest()

    # Published date
    published_at = None
    try:
        published_at = parsedate_to_datetime(date_str).astimezone(timezone.utc).replace(tzinfo=timezone.utc)
    except Exception:
        pass

    # Excerpt
    html_body = _extract_html_part(payload)
    soup = BeautifulSoup(html_body, "html.parser")
    excerpt = soup.get_text(separator=" ", strip=True)[:500]

    return {
        "title": subject,
        "url": url_key,
        "source": sender_name or sender_email,
        "source_type": "email",
        "published_at": published_at,
        "excerpt": excerpt,
    }


def build_gmail_service():
    """Build authenticated Gmail API service using cached token."""
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    creds_path = os.getenv("GMAIL_CREDENTIALS_PATH", "./credentials.json")
    token_path = os.getenv("GMAIL_TOKEN_PATH", "./gmail_token.json")

    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(token_path, "w") as f:
                f.write(creds.to_json())
        else:
            raise RuntimeError(
                f"Gmail token not found or invalid. Run: python -m backend.gmail_reader --auth"
            )

    return build("gmail", "v1", credentials=creds)


def read_newsletters(db: Session) -> None:
    """Fetch unread newsletter emails from configured senders and save to DB."""
    senders_raw = os.getenv("NEWSLETTER_SENDERS", "")
    if not senders_raw.strip():
        logger.info("NEWSLETTER_SENDERS not configured — skipping Gmail")
        return

    senders = [s.strip() for s in senders_raw.split(",") if s.strip()]

    try:
        service = build_gmail_service()
    except Exception as e:
        logger.error(f"Gmail auth failed: {e}")
        return

    query = "is:unread (" + " OR ".join(f"from:{s}" for s in senders) + ")"

    try:
        result = service.users().messages().list(userId="me", q=query).execute()
        messages = result.get("messages", [])
    except Exception as e:
        logger.error(f"Gmail list messages failed: {e}")
        return

    articles = []
    msg_ids = []
    for msg_ref in messages:
        try:
            msg = service.users().messages().get(
                userId="me", id=msg_ref["id"], format="full"
            ).execute()
            article = parse_gmail_message(msg)
            articles.append(article)
            msg_ids.append(msg_ref["id"])
        except Exception as e:
            logger.error(f"Failed to process Gmail message {msg_ref['id']}: {e}")

    count = save_articles(articles, db)
    logger.info(f"Gmail: {count} new newsletter articles")

    # Mark processed emails as read
    if msg_ids:
        try:
            service.users().messages().batchModify(
                userId="me",
                body={"ids": msg_ids, "removeLabelIds": ["UNREAD"]},
            ).execute()
        except Exception as e:
            logger.error(f"Failed to mark emails as read: {e}")


# ── Auth CLI mode ──────────────────────────────────────────────────────────────

def run_auth():
    """One-time OAuth flow. Run on local machine to generate gmail_token.json."""
    from google_auth_oauthlib.flow import InstalledAppFlow

    creds_path = os.getenv("GMAIL_CREDENTIALS_PATH", "./credentials.json")
    token_path = os.getenv("GMAIL_TOKEN_PATH", "./gmail_token.json")

    flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
    creds = flow.run_local_server(port=0)
    with open(token_path, "w") as f:
        f.write(creds.to_json())
    print(f"Token saved to {token_path}")


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    if "--auth" in sys.argv:
        run_auth()
    else:
        print("Usage: python -m backend.gmail_reader --auth")
```

- [ ] **Step 4: Run tests — expect pass**

```bash
python -m pytest tests/test_gmail_reader.py -v
```

Expected: all 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/gmail_reader.py tests/test_gmail_reader.py
git commit -m "feat: Gmail newsletter reader with OAuth and unit tests"
```

---

## Task 6: AI Summarizer

**Files:**
- Create: `backend/summarizer.py`
- Create: `tests/test_summarizer.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_summarizer.py
import json
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from backend.models import Article
from backend.summarizer import load_categories, call_claude, summarize_pending


SAMPLE_CATEGORIES = [
    {"id": "modelos", "name": "Modelos de IA", "description": "Lanzamientos y actualizaciones de modelos"},
    {"id": "otros", "name": "Otros", "description": "Temas que no encajan en ninguna categoría"},
]


def test_load_categories(tmp_path):
    cat_file = tmp_path / "categories.json"
    cat_file.write_text(json.dumps(SAMPLE_CATEGORIES))
    result = load_categories(str(cat_file))
    assert len(result) == 2
    assert result[0]["id"] == "modelos"


def test_call_claude_returns_summary_and_category():
    mock_client = MagicMock()
    mock_message = MagicMock()
    mock_message.content = [
        MagicMock(text=json.dumps({
            "summary": "Claude lanzó un nuevo modelo más rápido.",
            "category_id": "modelos"
        }))
    ]
    mock_client.messages.create.return_value = mock_message

    summary, category_id = call_claude(
        client=mock_client,
        title="Claude 3.5 released",
        excerpt="Anthropic releases Claude 3.5 Sonnet...",
        categories=SAMPLE_CATEGORIES,
    )
    assert summary == "Claude lanzó un nuevo modelo más rápido."
    assert category_id == "modelos"


def test_call_claude_invalid_category_falls_back_to_otros():
    mock_client = MagicMock()
    mock_message = MagicMock()
    mock_message.content = [
        MagicMock(text=json.dumps({
            "summary": "Un resumen cualquiera.",
            "category_id": "categoria_inexistente"
        }))
    ]
    mock_client.messages.create.return_value = mock_message

    _, category_id = call_claude(
        client=mock_client,
        title="Test",
        excerpt="Test excerpt",
        categories=SAMPLE_CATEGORIES,
    )
    assert category_id == "otros"


def test_summarize_pending_increments_retry_on_failure(db_session):
    now = datetime.now(timezone.utc)
    article = Article(
        title="Test", url="https://example.com/t1", source="X",
        source_type="web", published_at=now, excerpt="some text", scraped_at=now,
    )
    db_session.add(article)
    db_session.commit()

    mock_client = MagicMock()
    mock_client.messages.create.side_effect = Exception("API error")

    summarize_pending(db=db_session, client=mock_client, categories=SAMPLE_CATEGORIES)

    db_session.refresh(article)
    assert article.retry_count == 1
    assert article.is_processed is False


def test_summarize_pending_marks_processed_on_success(db_session):
    now = datetime.now(timezone.utc)
    article = Article(
        title="Test", url="https://example.com/t2", source="X",
        source_type="web", published_at=now, excerpt="some text", scraped_at=now,
    )
    db_session.add(article)
    db_session.commit()

    mock_client = MagicMock()
    mock_message = MagicMock()
    mock_message.content = [
        MagicMock(text=json.dumps({"summary": "Un resumen.", "category_id": "modelos"}))
    ]
    mock_client.messages.create.return_value = mock_message

    summarize_pending(db=db_session, client=mock_client, categories=SAMPLE_CATEGORIES)

    db_session.refresh(article)
    assert article.is_processed is True
    assert article.ai_summary == "Un resumen."
    assert article.category_id == "modelos"
```

- [ ] **Step 2: Run tests — expect failure**

```bash
python -m pytest tests/test_summarizer.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Create `backend/summarizer.py`**

```python
import json
import logging
import os

from anthropic import Anthropic
from sqlalchemy.orm import Session

from backend.models import Article

logger = logging.getLogger(__name__)

MAX_RETRIES = 5
CATEGORIES_PATH = os.getenv("CATEGORIES_PATH", "./categories.json")


def load_categories(path: str = CATEGORIES_PATH) -> list[dict]:
    """Read categories.json. Called at the start of each summarizer run."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def call_claude(
    client: Anthropic,
    title: str,
    excerpt: str,
    categories: list[dict],
) -> tuple[str, str]:
    """
    Single Claude Haiku call → (summary_es, category_id).
    Falls back to 'otros' if returned category_id is not in categories list.
    Raises on API error.
    """
    valid_ids = {c["id"] for c in categories}
    categories_text = json.dumps(categories, ensure_ascii=False)

    prompt = (
        f"Dado este artículo de noticias de IA, responde SOLO con JSON válido:\n"
        f"Título: {title}\n"
        f"Extracto: {excerpt}\n\n"
        f"Categorías disponibles: {categories_text}\n\n"
        f"Responde con:\n"
        f'{{"summary": "<resumen de 2 oraciones en español>", '
        f'"category_id": "<id de la categoría más apropiada>"}}'
    )

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()
    data = json.loads(raw)

    summary = data.get("summary", "")
    category_id = data.get("category_id", "otros")
    if category_id not in valid_ids:
        category_id = "otros"

    return summary, category_id


def summarize_pending(
    db: Session,
    client: Anthropic | None = None,
    categories: list[dict] | None = None,
) -> None:
    """Process all unprocessed articles (retry_count < MAX_RETRIES)."""
    if client is None:
        client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    if categories is None:
        categories = load_categories()

    pending = (
        db.query(Article)
        .filter(Article.is_processed.is_(False), Article.retry_count < MAX_RETRIES)
        .all()
    )

    logger.info(f"Summarizer: {len(pending)} articles to process")

    for article in pending:
        try:
            summary, category_id = call_claude(
                client=client,
                title=article.title,
                excerpt=article.excerpt or "",
                categories=categories,
            )
            article.ai_summary = summary
            article.category_id = category_id
            article.is_processed = True
            db.commit()
        except Exception as e:
            article.retry_count += 1
            db.commit()
            logger.error(f"Summarizer failed for article {article.id}: {e}")
```

- [ ] **Step 4: Run tests — expect pass**

```bash
python -m pytest tests/test_summarizer.py -v
```

Expected: all 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/summarizer.py tests/test_summarizer.py
git commit -m "feat: Claude Haiku summarizer with category assignment"
```

---

## Task 7: FastAPI App & API Endpoints

**Files:**
- Create: `backend/main.py`
- Create: `backend/scheduler.py`
- Create: `tests/test_api.py`

- [ ] **Step 1: Write failing API tests**

```python
# tests/test_api.py
import json
from datetime import datetime, timezone
from unittest.mock import patch, AsyncMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base, get_db
from backend.models import Article
import backend.models  # noqa


@pytest.fixture
def client(db_session):
    from backend.main import app

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _add_article(db, **kwargs):
    defaults = dict(
        title="Test Article",
        url="https://example.com/1",
        source="Anthropic",
        source_type="web",
        published_at=datetime.now(timezone.utc),
        excerpt="some text",
        scraped_at=datetime.now(timezone.utc),
        is_processed=True,
        ai_summary="Un resumen.",
        category_id="modelos",
    )
    defaults.update(kwargs)
    article = Article(**defaults)
    db.add(article)
    db.commit()
    return article


def test_get_articles_empty(client):
    response = client.get("/api/articles")
    assert response.status_code == 200
    assert response.json() == []


def test_get_articles_returns_data(client, db_session):
    _add_article(db_session)
    response = client.get("/api/articles")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Test Article"
    assert "ai_summary" in data[0]
    assert "category_id" in data[0]


def test_get_articles_filter_by_source(client, db_session):
    _add_article(db_session, url="https://example.com/a1", source="Anthropic")
    _add_article(db_session, url="https://example.com/o1", source="OpenAI")
    response = client.get("/api/articles?source=Anthropic")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["source"] == "Anthropic"


def test_get_articles_filter_by_category(client, db_session):
    _add_article(db_session, url="https://example.com/m1", category_id="modelos")
    _add_article(db_session, url="https://example.com/a1", category_id="agentes")
    response = client.get("/api/articles?category=modelos")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["category_id"] == "modelos"


def test_get_articles_search(client, db_session):
    _add_article(db_session, url="https://example.com/s1", title="Claude sonnet release")
    _add_article(db_session, url="https://example.com/s2", title="OpenAI GPT news")
    response = client.get("/api/articles?q=claude")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert "Claude" in data[0]["title"]


def test_get_articles_pagination(client, db_session):
    for i in range(25):
        _add_article(db_session, url=f"https://example.com/{i}", title=f"Article {i}")
    response = client.get("/api/articles?limit=20&offset=0")
    assert len(response.json()) == 20
    response2 = client.get("/api/articles?limit=20&offset=20")
    assert len(response2.json()) == 5


def test_get_sources(client):
    response = client.get("/api/sources")
    assert response.status_code == 200
    sources = response.json()
    assert "Anthropic" in sources
    assert "OpenAI" in sources


def test_get_categories(client):
    response = client.get("/api/categories")
    assert response.status_code == 200
    cats = response.json()
    assert isinstance(cats, list)
    assert any(c["id"] == "modelos" for c in cats)


def test_post_refresh_requires_token(client):
    response = client.post("/api/refresh")
    assert response.status_code == 401


def test_post_refresh_wrong_token(client):
    response = client.post("/api/refresh", headers={"X-Refresh-Token": "wrong"})
    assert response.status_code == 401


def test_post_refresh_valid_token(client):
    with patch("backend.main.run_pipeline", new_callable=AsyncMock) as mock_pipeline:
        response = client.post(
            "/api/refresh",
            headers={"X-Refresh-Token": "test-secret"},
        )
    assert response.status_code == 200
```

- [ ] **Step 2: Run tests — expect failure**

```bash
python -m pytest tests/test_api.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Create `backend/scheduler.py`**

```python
import logging
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
    )
    return scheduler
```

- [ ] **Step 4: Create `backend/main.py`**

```python
import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Depends, Header, HTTPException, Request
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

    scheduler = setup_scheduler(run_pipeline, session_factory)
    scheduler.start()
    logger.info("Scheduler started")

    yield

    scheduler.shutdown()
    logger.info("Scheduler stopped")


app = FastAPI(title="AI News Hub", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# ── API routes ─────────────────────────────────────────────────────────────────

@app.get("/api/articles")
@limiter.limit("60/minute")
def get_articles(
    request: Request,
    source: str | None = None,
    category: str | None = None,
    q: str | None = None,
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
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
            "ai_summary": a.ai_summary,
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
    db: Session = Depends(get_db),
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
```

- [ ] **Step 5: Set `REFRESH_SECRET_TOKEN=test-secret` for tests**

Add to `tests/conftest.py` at the top:

```python
import os
os.environ.setdefault("REFRESH_SECRET_TOKEN", "test-secret")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
```

- [ ] **Step 6: Run tests — expect pass**

```bash
python -m pytest tests/test_api.py -v
```

Expected: all 10 tests PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/main.py backend/scheduler.py tests/test_api.py
git commit -m "feat: FastAPI app with all endpoints, rate limiting, scheduler"
```

---

## Task 8: CSS Themes

**Files:**
- Create: `frontend/themes.css`

- [ ] **Step 1: Create `frontend/themes.css`**

```css
/* ── Base reset & variables ──────────────────────────────────────────────── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --radius: 12px;
  --radius-sm: 8px;
  --transition: 0.2s ease;
  --font: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

body { font-family: var(--font); transition: background var(--transition), color var(--transition); }

/* ── Theme: Light (default) ─────────────────────────────────────────────── */
[data-theme="light"] {
  --bg: #f9fafb;
  --bg-card: #ffffff;
  --bg-nav: #ffffff;
  --bg-hero-start: #6366f1;
  --bg-hero-end: #8b5cf6;
  --text-primary: #111827;
  --text-secondary: #6b7280;
  --text-muted: #9ca3af;
  --border: #e5e7eb;
  --accent: #6366f1;
  --accent-soft: #ede9fe;
  --chip-active-bg: #6366f1;
  --chip-active-text: #ffffff;
  --chip-bg: #f3f4f6;
  --chip-text: #6b7280;
  --badge-email-bg: #fef3c7;
  --badge-email-text: #92400e;
  --shadow: 0 1px 3px rgba(0,0,0,.08);
  --shadow-card: 0 2px 8px rgba(0,0,0,.06);
}

/* ── Theme: Dark Tech ───────────────────────────────────────────────────── */
[data-theme="dark"] {
  --bg: #0d1117;
  --bg-card: #161b22;
  --bg-nav: #161b22;
  --bg-hero-start: #0d1117;
  --bg-hero-end: #0d1117;
  --text-primary: #e6edf3;
  --text-secondary: #8b949e;
  --text-muted: #6e7681;
  --border: #30363d;
  --accent: #58a6ff;
  --accent-soft: rgba(88,166,255,.12);
  --chip-active-bg: #58a6ff;
  --chip-active-text: #0d1117;
  --chip-bg: #21262d;
  --chip-text: #8b949e;
  --badge-email-bg: rgba(88,166,255,.15);
  --badge-email-text: #58a6ff;
  --shadow: 0 1px 3px rgba(0,0,0,.4);
  --shadow-card: 0 2px 8px rgba(0,0,0,.3);
}

/* ── Theme: Gradient Modern ─────────────────────────────────────────────── */
[data-theme="gradient"] {
  --bg: #0f0c29;
  --bg-card: rgba(255,255,255,.05);
  --bg-nav: rgba(30,27,75,.95);
  --bg-hero-start: #1e1b4b;
  --bg-hero-end: #312e81;
  --text-primary: #f5f3ff;
  --text-secondary: #c4b5fd;
  --text-muted: #a78bfa;
  --border: rgba(167,139,250,.25);
  --accent: #a78bfa;
  --accent-soft: rgba(167,139,250,.15);
  --chip-active-bg: #a78bfa;
  --chip-active-text: #1e1b4b;
  --chip-bg: rgba(167,139,250,.1);
  --chip-text: #c4b5fd;
  --badge-email-bg: rgba(167,139,250,.2);
  --badge-email-text: #a78bfa;
  --shadow: 0 1px 3px rgba(0,0,0,.5);
  --shadow-card: 0 4px 16px rgba(0,0,0,.4);
}

/* ── Layout components ───────────────────────────────────────────────────── */
body { background: var(--bg); color: var(--text-primary); min-height: 100vh; }

nav {
  background: var(--bg-nav);
  border-bottom: 1px solid var(--border);
  padding: 14px 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  position: sticky; top: 0; z-index: 100;
  box-shadow: var(--shadow);
}

.logo { display: flex; align-items: center; gap: 8px; }
.logo-dot { width: 9px; height: 9px; border-radius: 50%; background: var(--accent); }
.logo-text { font-size: 13px; font-weight: 700; color: var(--accent); letter-spacing: 2px; }

.theme-switcher { display: flex; align-items: center; gap: 8px; }
.theme-label { font-size: 11px; color: var(--text-muted); }
.theme-btn {
  width: 18px; height: 18px; border-radius: 50%; border: 2px solid var(--border);
  cursor: pointer; transition: border-color var(--transition), transform var(--transition);
}
.theme-btn:hover { transform: scale(1.15); }
.theme-btn[data-theme="light"] { background: #f9fafb; }
.theme-btn[data-theme="dark"] { background: #0d1117; }
.theme-btn[data-theme="gradient"] { background: linear-gradient(135deg, #1e1b4b, #a78bfa); }
.theme-btn.active { border-color: var(--accent); }

.hero {
  background: linear-gradient(135deg, var(--bg-hero-start), var(--bg-hero-end));
  padding: 36px 24px;
  text-align: center;
}
.hero h1 { color: #fff; font-size: 22px; font-weight: 700; margin-bottom: 6px; }
.hero p { color: rgba(255,255,255,.75); font-size: 13px; margin-bottom: 20px; }

.search-wrap { display: inline-flex; align-items: center; gap: 8px; background: #fff;
  border-radius: 24px; padding: 9px 18px; width: min(400px, 90vw); box-shadow: 0 2px 8px rgba(0,0,0,.15); }
.search-wrap input { border: none; outline: none; font-size: 13px; color: #374151;
  background: transparent; width: 100%; }

.filter-section { background: var(--bg-nav); border-bottom: 1px solid var(--border); padding: 10px 24px; }
.filter-row { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
.filter-row + .filter-row { margin-top: 8px; }
.filter-row-label { font-size: 10px; font-weight: 600; color: var(--text-muted);
  letter-spacing: 1px; text-transform: uppercase; min-width: 60px; }

.chip {
  padding: 4px 12px; border-radius: 14px; font-size: 11px; font-weight: 600;
  cursor: pointer; transition: background var(--transition), color var(--transition);
  border: 1px solid transparent;
  background: var(--chip-bg); color: var(--chip-text);
}
.chip.active { background: var(--chip-active-bg); color: var(--chip-active-text); }
.chip:hover:not(.active) { border-color: var(--accent); color: var(--accent); }

.main { max-width: 1200px; margin: 0 auto; padding: 24px; }

.cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
}

.card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 16px;
  box-shadow: var(--shadow-card);
  transition: transform var(--transition), box-shadow var(--transition);
  display: flex; flex-direction: column; gap: 10px;
}
.card:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(0,0,0,.1); }

.card-header { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.badge {
  font-size: 10px; font-weight: 600; padding: 3px 8px; border-radius: 8px;
  white-space: nowrap;
}
.badge-source { background: var(--accent-soft); color: var(--accent); }
.badge-email { background: var(--badge-email-bg); color: var(--badge-email-text); }
.badge-category { background: var(--chip-bg); color: var(--chip-text); font-weight: 500; }
.card-time { font-size: 10px; color: var(--text-muted); }

.card-title { font-size: 14px; font-weight: 600; color: var(--text-primary); line-height: 1.4; }

.card-summary { font-size: 12px; color: var(--text-secondary); line-height: 1.6; flex: 1; }
.card-summary.pending { color: var(--text-muted); font-style: italic; }

.card-footer { display: flex; align-items: center; justify-content: space-between; }
.ai-badge { font-size: 10px; color: var(--accent); font-weight: 600; }
.read-link {
  font-size: 11px; font-weight: 600; color: var(--accent);
  text-decoration: none; transition: opacity var(--transition);
}
.read-link:hover { opacity: 0.75; }

.load-more-wrap { text-align: center; margin: 32px 0; }
.load-more-btn {
  background: var(--accent); color: #fff; border: none; border-radius: 24px;
  padding: 10px 28px; font-size: 13px; font-weight: 600; cursor: pointer;
  transition: opacity var(--transition);
}
.load-more-btn:hover { opacity: 0.85; }
.load-more-btn:disabled { opacity: 0.4; cursor: not-allowed; }

.empty-state { text-align: center; padding: 60px 24px; color: var(--text-muted); }
.error-msg { text-align: center; padding: 24px; color: #ef4444; font-size: 13px; }

footer { border-top: 1px solid var(--border); padding: 16px; text-align: center;
  font-size: 11px; color: var(--text-muted); background: var(--bg-nav); }
```

- [ ] **Step 2: Verify visually (manual)**

Open `frontend/themes.css` — no automated test needed for pure CSS. Visual verification happens in Task 10.

- [ ] **Step 3: Commit**

```bash
git add frontend/themes.css
git commit -m "feat: 3 CSS themes (light, dark, gradient)"
```

---

## Task 9: Frontend HTML & JavaScript

**Files:**
- Create: `frontend/index.html`
- Create: `frontend/app.js`

- [ ] **Step 1: Create `frontend/index.html`**

```html
<!DOCTYPE html>
<html lang="es" data-theme="light">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>AI News Hub</title>
  <link rel="stylesheet" href="/static/themes.css" />
</head>
<body>
  <!-- Nav -->
  <nav>
    <div class="logo">
      <div class="logo-dot"></div>
      <span class="logo-text">AI NEWS HUB</span>
    </div>
    <div class="theme-switcher">
      <span class="theme-label">Tema:</span>
      <button class="theme-btn active" data-theme="light" title="Clean Light" onclick="setTheme('light')"></button>
      <button class="theme-btn" data-theme="dark" title="Dark Tech" onclick="setTheme('dark')"></button>
      <button class="theme-btn" data-theme="gradient" title="Gradient Modern" onclick="setTheme('gradient')"></button>
    </div>
  </nav>

  <!-- Hero + search -->
  <div class="hero">
    <h1>Noticias de IA al instante</h1>
    <p>Actualizadas cada 2 horas · Resúmenes con Claude AI</p>
    <div class="search-wrap">
      <span>🔍</span>
      <input id="search-input" type="text" placeholder="Buscar noticias, modelos, features..." autocomplete="off" />
    </div>
  </div>

  <!-- Filters -->
  <div class="filter-section">
    <div class="filter-row">
      <span class="filter-row-label">Fuente</span>
      <div id="source-filters"></div>
    </div>
    <div class="filter-row">
      <span class="filter-row-label">Tema</span>
      <div id="category-filters"></div>
    </div>
  </div>

  <!-- Cards -->
  <main class="main">
    <div id="error-msg" class="error-msg" style="display:none"></div>
    <div id="cards-grid" class="cards-grid"></div>
    <div class="load-more-wrap">
      <button id="load-more-btn" class="load-more-btn" onclick="loadMore()" style="display:none">
        Cargar más
      </button>
    </div>
  </main>

  <footer>
    <span id="footer-info">Cargando...</span> · Powered by Claude AI
  </footer>

  <script src="/static/app.js"></script>
</body>
</html>
```

- [ ] **Step 2: Create `frontend/app.js`**

```javascript
// ── State ─────────────────────────────────────────────────────────────────────
const state = {
  source: null,
  category: null,
  q: '',
  offset: 0,
  limit: 20,
  loading: false,
  totalLoaded: 0,
};

// ── Theme ─────────────────────────────────────────────────────────────────────
function setTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  localStorage.setItem('ai-news-theme', theme);
  document.querySelectorAll('.theme-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.theme === theme);
  });
}

function initTheme() {
  const saved = localStorage.getItem('ai-news-theme') || 'light';
  setTheme(saved);
}

// ── Relative time ─────────────────────────────────────────────────────────────
function relativeTime(isoString) {
  if (!isoString) return '';
  const diff = (Date.now() - new Date(isoString).getTime()) / 1000;
  if (diff < 60) return 'hace un momento';
  if (diff < 3600) return `hace ${Math.floor(diff / 60)}m`;
  if (diff < 86400) return `hace ${Math.floor(diff / 3600)}h`;
  return `hace ${Math.floor(diff / 86400)}d`;
}

// ── Card rendering ────────────────────────────────────────────────────────────
function renderCard(article) {
  const isEmail = article.source_type === 'email';
  const sourceBadgeClass = isEmail ? 'badge-email' : 'badge-source';
  const summaryText = article.ai_summary || 'Procesando...';
  const summaryClass = article.ai_summary ? '' : 'pending';

  return `
    <div class="card">
      <div class="card-header">
        <span class="badge ${sourceBadgeClass}">${article.source}</span>
        <span class="card-time">${relativeTime(article.published_at)}</span>
      </div>
      <div class="card-title">${article.title}</div>
      <div class="card-summary ${summaryClass}">
        ${article.ai_summary ? '✨ ' : '⏳ '}${summaryText}
      </div>
      <div class="card-footer">
        <span class="badge badge-category">${article.category_id || '—'}</span>
        <a class="read-link" href="${article.url}" target="_blank" rel="noopener">Leer más →</a>
      </div>
    </div>
  `;
}

// ── Fetch articles ────────────────────────────────────────────────────────────
async function fetchArticles(append = false) {
  if (state.loading) return;
  state.loading = true;

  const params = new URLSearchParams({
    limit: state.limit,
    offset: state.offset,
  });
  if (state.source) params.set('source', state.source);
  if (state.category) params.set('category', state.category);
  if (state.q) params.set('q', state.q);

  try {
    const res = await fetch(`/api/articles?${params}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const articles = await res.json();

    const grid = document.getElementById('cards-grid');
    const errorEl = document.getElementById('error-msg');
    errorEl.style.display = 'none';

    if (!append) grid.innerHTML = '';

    if (articles.length === 0 && !append) {
      grid.innerHTML = '<div class="empty-state">No se encontraron artículos.</div>';
    } else {
      grid.insertAdjacentHTML('beforeend', articles.map(renderCard).join(''));
      state.totalLoaded = append ? state.totalLoaded + articles.length : articles.length;
      state.offset += articles.length;
    }

    const btn = document.getElementById('load-more-btn');
    btn.style.display = articles.length === state.limit ? 'inline-block' : 'none';

    updateFooter();
  } catch (e) {
    const errorEl = document.getElementById('error-msg');
    errorEl.textContent = 'No se pudo cargar el contenido. Intentá de nuevo más tarde.';
    errorEl.style.display = 'block';
  } finally {
    state.loading = false;
  }
}

function loadMore() {
  fetchArticles(true);
}

// ── Filters ───────────────────────────────────────────────────────────────────
function resetPagination() {
  state.offset = 0;
  state.totalLoaded = 0;
}

function buildChips(containerId, items, activeKey, onSelect) {
  const container = document.getElementById(containerId);
  const allChip = `<span class="chip active" data-val="">Todas</span>`;
  const chips = items.map(item => {
    const val = typeof item === 'string' ? item : item.id;
    const label = typeof item === 'string' ? item : item.name;
    return `<span class="chip" data-val="${val}">${label}</span>`;
  });
  container.innerHTML = [allChip, ...chips].join('');

  container.querySelectorAll('.chip').forEach(chip => {
    chip.addEventListener('click', () => {
      container.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      onSelect(chip.dataset.val || null);
      resetPagination();
      fetchArticles();
    });
  });
}

async function initFilters() {
  const [sourcesRes, catsRes] = await Promise.all([
    fetch('/api/sources'),
    fetch('/api/categories'),
  ]);
  const sources = await sourcesRes.json();
  const categories = await catsRes.json();

  buildChips('source-filters', sources, 'source', val => { state.source = val; });
  buildChips('category-filters', categories, 'category', val => { state.category = val; });
}

// ── Search ────────────────────────────────────────────────────────────────────
let searchTimeout;
document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('search-input').addEventListener('input', e => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
      state.q = e.target.value.trim();
      resetPagination();
      fetchArticles();
    }, 300);
  });
});

// ── Footer ────────────────────────────────────────────────────────────────────
function updateFooter() {
  document.getElementById('footer-info').textContent =
    `${state.totalLoaded} artículos cargados`;
}

// ── Init ──────────────────────────────────────────────────────────────────────
async function init() {
  initTheme();
  await initFilters();
  await fetchArticles();
}

init();
```

- [ ] **Step 3: Run the app and verify visually**

```bash
cd "C:/Users/Usuario/OneDrive/Desktop/CLAUDIO/app ia"
python -m uvicorn backend.main:app --reload --port 8000
```

Open `http://localhost:8000` in your browser. Verify:
- Page loads with Clean Light theme
- Theme switcher changes all 3 themes correctly
- Filter chips appear for sources and categories
- Search input debounces correctly
- "Cargar más" appears when articles exist

- [ ] **Step 4: Commit**

```bash
git add frontend/index.html frontend/app.js
git commit -m "feat: frontend HTML and vanilla JS with theme switcher, filters, search"
```

---

## Task 10: Gmail Auth Setup & End-to-End Smoke Test

**Files:**
- No new files — configuration and verification

- [ ] **Step 1: Set up Gmail API credentials**

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project → Enable "Gmail API"
3. Create OAuth 2.0 credentials (Desktop app type)
4. Download `credentials.json` and place it at the path in `GMAIL_CREDENTIALS_PATH`

- [ ] **Step 2: Generate Gmail token (run once on local machine)**

```bash
cd "C:/Users/Usuario/OneDrive/Desktop/CLAUDIO/app ia"
python -m backend.gmail_reader --auth
```

This opens a browser. Authorize the app. `gmail_token.json` is created.

- [ ] **Step 3: Configure your newsletter senders in `.env`**

Edit `.env` and add your actual newsletter sender addresses:

```
NEWSLETTER_SENDERS=sender@example.com,another@newsletter.com
```

- [ ] **Step 4: Run the full test suite**

```bash
python -m pytest -v
```

Expected: all tests PASS.

- [ ] **Step 5: Trigger a manual pipeline run via API**

With the server running (`uvicorn backend.main:app --reload`):

```bash
curl -X POST http://localhost:8000/api/refresh \
  -H "X-Refresh-Token: YOUR_REFRESH_SECRET_TOKEN"
```

Expected: `{"status": "ok"}`. Check terminal logs for scraping + summarization output.

- [ ] **Step 6: Verify articles in browser**

Open `http://localhost:8000` — articles should appear with Spanish summaries and category badges.

- [ ] **Step 7: Final commit**

```bash
git add .
git commit -m "feat: complete AI News Hub v1 — web scraping, Gmail, Claude summaries, themeable frontend"
```

---

## Adding a New Category (Post-Launch)

Edit `categories.json` and add a new entry:

```json
{
  "id": "hardware",
  "name": "Hardware & Chips",
  "description": "GPUs, TPUs, chips especializados para IA, eficiencia energética"
}
```

Save the file. The next scheduler run (within 2 hours) will use the new category automatically. No code changes, no restart needed.
