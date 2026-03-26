import logging
from datetime import datetime, timezone

import httpx
import feedparser
from bs4 import BeautifulSoup

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
