# tests/test_database.py
from datetime import datetime, timezone
import pytest
from sqlalchemy.exc import IntegrityError
from backend.models import Article


def test_create_article(db_session):
    article = Article(
        title="Test Article",
        url="https://example.com/1",
        source="Anthropic",
        source_type="web",
        published_at=datetime.now(timezone.utc),
        excerpt="Some text here",
        scraped_at=datetime.now(timezone.utc),
    )
    db_session.add(article)
    db_session.commit()
    assert article.id is not None
    assert article.is_processed is False
    assert article.retry_count == 0
    assert article.ai_summary is None
    assert article.category_id is None


def test_url_uniqueness_constraint(db_session):
    now = datetime.now(timezone.utc)
    a1 = Article(title="A", url="https://example.com/dup", source="X",
                 source_type="web", published_at=now, excerpt="", scraped_at=now)
    a2 = Article(title="B", url="https://example.com/dup", source="X",
                 source_type="web", published_at=now, excerpt="", scraped_at=now)
    db_session.add(a1)
    db_session.commit()
    db_session.add(a2)
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_init_db_creates_tables():
    from sqlalchemy import create_engine, inspect
    from backend.database import Base, init_db
    import backend.models  # noqa
    engine = create_engine("sqlite:///:memory:")
    init_db(engine)
    inspector = inspect(engine)
    assert "articles" in inspector.get_table_names()
