import json
import logging
import os

from openai import OpenAI
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
    client: OpenAI,
    title: str,
    excerpt: str,
    categories: list[dict],
) -> tuple[str, str, int]:
    """
    Single OpenAI call → (summary_es, category_id, importance).
    importance: 3=alta (nuevo modelo, lanzamiento mayor), 2=media, 1=baja (changelog menor).
    Falls back to 'otros' / 2 if values are missing or invalid.
    Raises on API error.
    """
    valid_ids = {c["id"] for c in categories}
    categories_text = json.dumps(categories, ensure_ascii=False)

    prompt = (
        f"Dado este artículo de noticias de IA, responde SOLO con JSON válido:\n"
        f"Título: {title}\n"
        f"Extracto: {excerpt}\n\n"
        f"Categorías disponibles: {categories_text}\n\n"
        f"Reglas de importancia:\n"
        f"  3 = ALTA: nuevo modelo de IA, lanzamiento mayor de producto, adquisición, hito histórico\n"
        f"  2 = MEDIA: nueva feature, paper relevante, partnership, actualización importante\n"
        f"  1 = BAJA: changelog menor, opinión, noticia general, update rutinario\n\n"
        f"Responde con:\n"
        f'{{"summary": "<resumen de 2 oraciones en español>", '
        f'"category_id": "<id de la categoría más apropiada>", '
        f'"importance": <1, 2 o 3>}}'
    )

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.choices[0].message.content.strip()
    # Strip markdown code fences if present (e.g. ```json...```)
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    data = json.loads(raw)

    summary = data.get("summary", "")
    category_id = data.get("category_id", "otros")
    if category_id not in valid_ids:
        category_id = "otros"
    importance = int(data.get("importance", 2))
    if importance not in (1, 2, 3):
        importance = 2

    return summary, category_id, importance


def summarize_pending(
    db: Session,
    client: OpenAI | None = None,
    categories: list[dict] | None = None,
) -> None:
    """Process all unprocessed articles (retry_count < MAX_RETRIES)."""
    if client is None:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
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
            summary, category_id, importance = call_claude(
                client=client,
                title=article.title,
                excerpt=article.excerpt or "",
                categories=categories,
            )
            article.ai_summary = summary
            article.category_id = category_id
            article.importance = importance
            article.is_processed = True
            db.commit()
        except Exception as e:
            article.retry_count += 1
            db.commit()
            logger.error(f"Summarizer failed for article {article.id}: {e}")
