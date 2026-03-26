# tests/test_api.py
import json
from datetime import datetime, timezone
from unittest.mock import patch, AsyncMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database import Base, get_db
from backend.models import Article
import backend.models  # noqa


# Override db_session for this module to use StaticPool so that the in-memory
# SQLite database is shared across threads (TestClient runs ASGI in a thread).
@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def client(db_session):
    from backend.main import app

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _add_article(db, **kwargs):
    defaults = dict(
        title="Test Article",
        url="https://example.com/1",
        source="Anthropic",
        source_type="web",
        published_at=datetime.now(timezone.utc),
        excerpt="some text",
        scraped_at=datetime.now(timezone.utc),
        is_processed=True,
        ai_summary="Un resumen.",
        category_id="modelos",
    )
    defaults.update(kwargs)
    article = Article(**defaults)
    db.add(article)
    db.commit()
    return article


def test_get_articles_empty(client):
    response = client.get("/api/articles")
    assert response.status_code == 200
    assert response.json() == []


def test_get_articles_returns_data(client, db_session):
    _add_article(db_session)
    response = client.get("/api/articles")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Test Article"
    assert "ai_summary" in data[0]
    assert "category_id" in data[0]


def test_get_articles_filter_by_source(client, db_session):
    _add_article(db_session, url="https://example.com/a1", source="Anthropic")
    _add_article(db_session, url="https://example.com/o1", source="OpenAI")
    response = client.get("/api/articles?source=Anthropic")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["source"] == "Anthropic"


def test_get_articles_filter_by_category(client, db_session):
    _add_article(db_session, url="https://example.com/m1", category_id="modelos")
    _add_article(db_session, url="https://example.com/a1", category_id="agentes")
    response = client.get("/api/articles?category=modelos")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["category_id"] == "modelos"


def test_get_articles_search(client, db_session):
    _add_article(db_session, url="https://example.com/s1", title="Claude sonnet release")
    _add_article(db_session, url="https://example.com/s2", title="OpenAI GPT news")
    response = client.get("/api/articles?q=claude")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert "Claude" in data[0]["title"]


def test_get_articles_pagination(client, db_session):
    for i in range(25):
        _add_article(db_session, url=f"https://example.com/{i}", title=f"Article {i}")
    response = client.get("/api/articles?limit=20&offset=0")
    assert len(response.json()) == 20
    response2 = client.get("/api/articles?limit=20&offset=20")
    assert len(response2.json()) == 5


def test_get_sources(client):
    response = client.get("/api/sources")
    assert response.status_code == 200
    sources = response.json()
    assert "Anthropic" in sources
    assert "OpenAI" in sources


def test_get_categories(client):
    response = client.get("/api/categories")
    assert response.status_code == 200
    cats = response.json()
    assert isinstance(cats, list)
    assert any(c["id"] == "modelos" for c in cats)


def test_post_refresh_requires_token(client):
    response = client.post("/api/refresh")
    assert response.status_code == 401


def test_post_refresh_wrong_token(client):
    response = client.post("/api/refresh", headers={"X-Refresh-Token": "wrong"})
    assert response.status_code == 401


def test_post_refresh_valid_token(client):
    with patch("backend.main.run_pipeline", new_callable=AsyncMock) as mock_pipeline:
        response = client.post(
            "/api/refresh",
            headers={"X-Refresh-Token": "test-secret"},
        )
    assert response.status_code == 200
    mock_pipeline.assert_awaited_once()
