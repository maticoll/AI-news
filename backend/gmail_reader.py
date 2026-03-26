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
        published_at = parsedate_to_datetime(date_str).astimezone(timezone.utc)
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
