# tests/test_scraper.py
import pytest
from pathlib import Path
from datetime import datetime, timezone

from backend.scraper import (
    parse_rss_feed,
    parse_openai_articles,
    parse_deepmind_articles,
    parse_mistral_articles,
    save_articles,
)


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
    assert first["excerpt"] == "Today we are releasing Claude 3.5 Sonnet, our most intelligent model to date."


def test_parse_rss_missing_pubdate():
    xml = """<?xml version="1.0"?><rss version="2.0"><channel>
      <item><title>No date</title><link>https://example.com/x</link></item>
    </channel></rss>"""
    articles = parse_rss_feed(xml)
    assert len(articles) == 1
    assert articles[0]["published_at"] is None


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


def test_save_articles_inserts_and_deduplicates(db_session):
    now = datetime.now(timezone.utc)
    articles = [
        {"title": "A", "url": "https://x.com/1", "source": "OpenAI",
         "source_type": "web", "published_at": now, "excerpt": "text"},
        {"title": "A dup", "url": "https://x.com/1", "source": "OpenAI",
         "source_type": "web", "published_at": now, "excerpt": "text"},
    ]
    count = save_articles(articles, db_session)
    assert count == 1  # duplicate skipped


def test_save_articles_fallback_published_at(db_session):
    articles = [
        {"title": "No date", "url": "https://x.com/2", "source": "Test",
         "source_type": "web", "published_at": None, "excerpt": ""},
    ]
    count = save_articles(articles, db_session)
    assert count == 1
    from backend.models import Article
    article = db_session.query(Article).filter_by(url="https://x.com/2").first()
    assert article.published_at is not None  # should have fallback to now
