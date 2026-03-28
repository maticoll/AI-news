import logging
import shutil
from datetime import datetime, timezone
from urllib.parse import urljoin

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
    """Fetch Anthropic RSS and return parsed article dicts. Returns [] on failure."""
    url = "https://www.anthropic.com/rss.xml"
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url)
            response.raise_for_status()
        return parse_rss_feed(response.text)
    except Exception as e:
        logger.error(f"Anthropic RSS fetch failed: {e}")
        return []


# ── Playwright helpers ─────────────────────────────────────────────────────────

def _chromium_executable() -> str | None:
    """Return system Chromium path if available (used when playwright bundled binary is skipped)."""
    return shutil.which("chromium") or shutil.which("chromium-browser")


async def fetch_page_html(url: str) -> str:
    """Fetch JS-rendered page HTML using headless Chromium."""
    launch_kwargs = {"headless": True}
    exe = _chromium_executable()
    if exe:
        launch_kwargs["executable_path"] = exe
    async with async_playwright() as p:
        browser = await p.chromium.launch(**launch_kwargs)
        async with browser:
            page = await browser.new_page()
            await page.goto(url, wait_until="networkidle", timeout=30000)
            html = await page.content()
    return html


def _extract_text(el) -> str:
    return el.get_text(strip=True) if el else ""


def _abs_url(href: str, base: str) -> str:
    if href.startswith("http"):
        return href
    return urljoin(base, href)


# ── Per-site parsers (pure functions) ─────────────────────────────────────────

def parse_openai_articles(html: str) -> list[dict]:
    """Parse OpenAI news page. Selectors verified against tests/fixtures/openai_news.html.
    Looks for <a href="/index/..."> links containing heading elements.
    """
    soup = BeautifulSoup(html, "html.parser")
    articles = []
    seen_urls = set()

    base = "https://openai.com"
    for a in soup.find_all("a", href=True):
        href = a.get("href", "").strip()
        # Article links follow the /index/<slug>/ pattern
        if not href or "/index/" not in href:
            continue
        url = _abs_url(href, base)
        if url in seen_urls:
            continue

        # Title from any heading inside the link
        heading = a.find(["h1", "h2", "h3", "h4"])
        title = _extract_text(heading)
        if not title:
            continue

        # Optional excerpt from <p>
        p = a.find("p")
        excerpt = _extract_text(p)[:500] if p else ""

        # Optional date from <time>
        time_el = a.find("time")
        published_at = None
        if time_el:
            dt_str = time_el.get("datetime", "") or time_el.get_text(strip=True)
            try:
                published_at = datetime.fromisoformat(dt_str).replace(tzinfo=timezone.utc)
            except ValueError:
                pass

        seen_urls.add(url)
        articles.append({
            "title": title,
            "url": url,
            "source": "OpenAI",
            "source_type": "web",
            "published_at": published_at,
            "excerpt": excerpt,
        })

    return articles


def parse_deepmind_articles(html: str) -> list[dict]:
    """Parse Google DeepMind publications page.
    Selectors verified against tests/fixtures/deepmind_news.html.
    Links: <a href="https://deepmind.google/research/publications/<id>/">
    Title: <span class="list-group__description"> inside <dl>
    Date:  <span class="list-group__date"> inside <dl>  (format: "23 April 2026")
    """
    soup = BeautifulSoup(html, "html.parser")
    articles = []
    seen_urls = set()

    for a in soup.find_all("a", href=True):
        href = a.get("href", "").strip()
        if not href or "/research/publications/" not in href:
            continue
        # Skip the listing page link itself
        if href.rstrip("/").endswith("/research/publications"):
            continue
        url = _abs_url(href, "https://deepmind.google")
        if url in seen_urls:
            continue

        dl = a.find("dl")
        if not dl:
            continue

        title_el = dl.find("span", class_="list-group__description")
        title = _extract_text(title_el)
        if not title:
            continue

        date_el = dl.find("span", class_="list-group__date")
        published_at = None
        if date_el:
            date_text = date_el.get_text(strip=True)
            try:
                published_at = datetime.strptime(date_text, "%d %B %Y").replace(tzinfo=timezone.utc)
            except ValueError:
                pass

        seen_urls.add(url)
        articles.append({
            "title": title,
            "url": url,
            "source": "Google DeepMind",
            "source_type": "web",
            "published_at": published_at,
            "excerpt": "",
        })

    return articles


def parse_mistral_articles(html: str) -> list[dict]:
    """Parse Mistral AI news page.
    Selectors verified against tests/fixtures/mistral_news.html.
    Links: <a href="/news/<slug>"> containing <article>
    Title: <h1> or <h2> inside the <a>
    Date:  <div class="...text-mistral-black-tint"> (format: "Mar 23, 2026")
    """
    soup = BeautifulSoup(html, "html.parser")
    articles = []
    seen_urls = set()

    base = "https://mistral.ai"
    for a in soup.find_all("a", href=True):
        href = a.get("href", "").strip()
        # Article links start with /news/ followed by a slug
        if not href or not href.startswith("/news/"):
            continue
        url = _abs_url(href, base)
        if url in seen_urls:
            continue

        # Title from h1 or h2
        heading = a.find(["h1", "h2"])
        title = _extract_text(heading)
        if not title:
            continue

        # Excerpt from <p>
        p = a.find("p")
        excerpt = _extract_text(p)[:500] if p else ""

        # Date from div with 'text-mistral-black-tint' class
        date_div = a.find("div", class_="text-mistral-black-tint")
        published_at = None
        if date_div:
            date_text = date_div.get_text(strip=True)
            try:
                published_at = datetime.strptime(date_text, "%b %d, %Y").replace(tzinfo=timezone.utc)
            except ValueError:
                pass

        seen_urls.add(url)
        articles.append({
            "title": title,
            "url": url,
            "source": "Mistral",
            "source_type": "web",
            "published_at": published_at,
            "excerpt": excerpt,
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
