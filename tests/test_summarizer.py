# tests/test_summarizer.py
import json
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock
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


def _make_openai_response(text: str) -> MagicMock:
    """Build a mock OpenAI chat completion response."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = text
    return mock_response


def test_call_claude_returns_summary_and_category():
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _make_openai_response(
        json.dumps({"summary": "Claude lanzó un nuevo modelo más rápido.", "category_id": "modelos"})
    )

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
    mock_client.chat.completions.create.return_value = _make_openai_response(
        json.dumps({"summary": "Un resumen cualquiera.", "category_id": "categoria_inexistente"})
    )

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
    mock_client.chat.completions.create.side_effect = Exception("API error")

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
    mock_client.chat.completions.create.return_value = _make_openai_response(
        json.dumps({"summary": "Un resumen.", "category_id": "modelos"})
    )

    summarize_pending(db=db_session, client=mock_client, categories=SAMPLE_CATEGORIES)

    db_session.refresh(article)
    assert article.is_processed is True
    assert article.ai_summary == "Un resumen."
    assert article.category_id == "modelos"
