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
