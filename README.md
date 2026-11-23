# AI News Hub

Agregador público de novedades de IA en español. Cada 2 horas junta artículos de los blogs oficiales (Anthropic, OpenAI, Google DeepMind, Mistral…) y de newsletters que llegan por Gmail, los resume y categoriza con un LLM y los muestra en un sitio filtrable por fuente y tema.

## Qué hace

- **Scraping programado** de RSS y blogs (feedparser, BeautifulSoup, Playwright para páginas con JS), con APScheduler.
- **Lectura de newsletters** desde Gmail vía Google API.
- **Resumen y categorización** automática en español, con nivel de importancia (alta / media / baja).
- **Frontend sin frameworks**: búsqueda avanzada, "mi feed", dashboard con gráficos, comparador de fuentes y 3 temas visuales.
- **API con rate limiting** (slowapi).

## Stack

Python 3.11 · FastAPI · SQLAlchemy (SQLite / PostgreSQL) · APScheduler · Playwright · OpenAI API · Vanilla JS · Docker · Render

## Correrlo local

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env   # completar las claves
uvicorn backend.main:app --reload
```

Abrí `http://localhost:8000`.

## Tests

```bash
pytest
```

Cubren el scraper (con fixtures HTML/XML reales), el lector de Gmail, el summarizer, la base de datos y la API.

## Estructura

```
backend/    API, scraper, summarizer, lector de Gmail, scheduler y modelos
frontend/   sitio estático (HTML + JS + temas CSS)
tests/      pytest con fixtures de cada fuente
docs/       spec de diseño y plan de implementación
```

## Licencia

MIT
