# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

**Run the app locally:**
```bash
uvicorn backend.main:app --reload
```

**Run all tests:**
```bash
pytest
```

**Run a single test file:**
```bash
pytest tests/test_scraper.py
```

**Run a single test:**
```bash
pytest tests/test_scraper.py::test_parse_rss_returns_articles
```

**Install dependencies:**
```bash
pip install -r requirements-dev.txt
playwright install chromium
```

**Gmail OAuth (one-time, local only):**
```bash
python -m backend.gmail_reader --auth
```

## Architecture

This is an **AI News Hub**: a FastAPI app that scrapes AI news from multiple sources, summarizes articles with GPT-4o-mini, and serves them through a vanilla JS frontend.

### Pipeline (runs every 2 hours via APScheduler)
```
scrape_all() → read_newsletters() → summarize_pending()
```
The full pipeline is also exposed at `POST /api/refresh` (requires `X-Refresh-Token` header).

### Backend modules (`backend/`)

| Module | Responsibility |
|---|---|
| `main.py` | FastAPI app, lifespan, API routes, static file serving, rate limiting (slowapi) |
| `database.py` | SQLAlchemy engine/session factory, `get_db` FastAPI dependency |
| `models.py` | `Article` ORM model (single table: `articles`) |
| `scraper.py` | Web scraping: Anthropic (RSS/httpx), OpenAI/DeepMind/Google Research/Mistral/TechCrunch/VentureBeat/MIT Tech Review/The Batch/arXiv (Playwright/RSS) |
| `gmail_reader.py` | Gmail API integration: reads unread newsletters from configured senders |
| `summarizer.py` | Calls GPT-4o-mini to generate Spanish summaries, assign categories, and set importance |
| `scheduler.py` | APScheduler setup — runs pipeline every 2 hours |

### Article model fields
- `importance` (Integer): 1=baja, 2=media (default), 3=alta — assigned by summarizer
- `source_type`: `"web"` or `"email"`
- `is_processed` / `retry_count`: summarizer state (max retries: 5)

### API rate limits (slowapi)
- `GET /api/articles`, `/api/stats`, `/api/sources`, `/api/categories`: 60/minute
- `POST /api/refresh`: 5/minute

### Scraper design
- **Pure parser functions** (`parse_rss_feed`, `parse_openai_articles`, etc.) do HTML/XML parsing with no I/O — this makes them independently testable with fixture files.
- `fetch_page_html()` uses headless Chromium (Playwright) for JS-rendered pages.
- `save_articles()` handles deduplication: duplicate URLs raise `IntegrityError` and are silently skipped.

### Article deduplication
Web articles use the canonical URL as the unique key. Email/newsletter articles use the `Message-ID` header (or a SHA-256 hash of sender+subject+date as fallback).

### Summarizer
Uses `OpenAI` client (not Anthropic — the function is named `call_claude` but calls GPT-4o-mini). Returns a 2-sentence Spanish summary, assigns one of the category IDs from `categories.json`, and sets `importance` (1–3). Articles that fail are retried up to `MAX_RETRIES = 5` times via `retry_count`.

### Frontend (`frontend/`)
Vanilla HTML + JS + CSS — no build step. Served directly by FastAPI as static files. Three CSS themes in `themes.css`. Charts use Chart.js (CDN). The root `/` serves `frontend/index.html`.

Six views registered in `app.js`:
| View | Description |
|---|---|
| `home` | Feed principal con filtros por fuente/categoría, búsqueda y paginación infinita |
| `dashboard` | Estadísticas con gráficos Chart.js (línea diaria, doughnut categorías, barras fuentes) |
| `digest` | Resumen del día agrupado por categoría |
| `search` | Búsqueda avanzada con filtros de fecha, fuente, categoría y orden |
| `myfeed` | Feed personalizado — preferencias guardadas en `localStorage` |
| `compare` | Comparar fuentes: muestra resultados de un término agrupados por fuente |

Frontend features:
- **Importance badge**: `🔴 Alta / 🟡 Media / ⚪ Baja` en cada card
- **Countdown**: timer hasta el próximo scraping vía `GET /api/next-run`
- **Auto-polling**: cuando hay artículos pendientes, refresca cada 30s y muestra toast al completarse

### Environment variables
See `.env.example` for all required vars. Key ones:
- `OPENAI_API_KEY` — required for summarization
- `REFRESH_SECRET_TOKEN` — protects `POST /api/refresh`
- `NEWSLETTER_SENDERS` — comma-separated email addresses to pull newsletters from
- `GMAIL_TOKEN_JSON` — production Gmail auth (full JSON string); falls back to `GMAIL_TOKEN_PATH` (file path) for local dev

### Testing
- Tests use `pytest-asyncio` in auto mode.
- The `db_session` fixture (in `conftest.py`) uses an in-memory SQLite database.
- Scraper parser tests use static HTML/XML fixtures in `tests/fixtures/` — update those files when site markup changes.
- `conftest.py` sets `CATEGORIES_PATH=./categories.json` — tests must be run from the repo root.

### Deployment
Deployed to Render.com via `render.yaml`. Build installs Python deps and Playwright Chromium. Start command: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`.
