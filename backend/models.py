from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, func
from backend.database import Base


class Article(Base):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(Text, nullable=False)
    url = Column(String(2048), unique=True, nullable=False)
    source = Column(String(100), nullable=False)
    source_type = Column(String(10), nullable=False)        # "web" or "email"
    published_at = Column(DateTime(timezone=True), nullable=False)
    excerpt = Column(Text, nullable=True)                   # first 500 chars; used by summarizer
    ai_summary = Column(Text, nullable=True)
    category_id = Column(String(50), nullable=True)
    scraped_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )
    is_processed = Column(Boolean, nullable=False, default=False)
    retry_count = Column(Integer, nullable=False, default=0)
    importance = Column(Integer, nullable=False, default=2)  # 1=baja, 2=media, 3=alta
