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
