# tests/test_gmail_reader.py
import base64
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
                        "data": base64.urlsafe_b64encode(
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
