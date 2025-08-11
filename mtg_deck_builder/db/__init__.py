"""Database initialization and session management."""

from contextlib import contextmanager
from pathlib import Path
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from mtg_deck_builder.db.repository import SummaryCardRepository
from mtg_deck_builder.db.inventory import InventoryItem
from mtg_deck_builder.models.card_meta import load_card_types, load_keywords, CardTypesData, KeywordsData

# paths relative to this file
KEYWORDS_PATH = Path(__file__).parent / "Keywords.json"
CARD_TYPES_PATH = Path(__file__).parent / "CardTypes.json"


def get_engine(database_url: str = "sqlite:///AllPrintings.sqlite"):
    """Create SQLAlchemy engine with optimized settings."""
    return create_engine(
        database_url,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
        echo=False,
    )


@contextmanager
def get_session(engine=None, db_url: Optional[str] = None):
    """Get database session as a context manager."""
    if engine is None:
        if db_url is None:
            engine = get_engine()
        else:
            engine = get_engine(db_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def get_card_types(card_types_json_path: Path = CARD_TYPES_PATH) -> CardTypesData:
    """Get card types from JSON file using card_meta utilities."""
    return load_card_types(card_types_json_path)


def get_keywords(keywords_json_path: Path = KEYWORDS_PATH) -> KeywordsData:
    """Get keywords from JSON file using card_meta utilities."""
    return load_keywords(keywords_json_path)


__all__ = [
    "get_engine", 
    "get_session", 
    "SummaryCardRepository", 
    "get_card_types", 
    "get_keywords",
    "InventoryItem",
    "CardTypesData",
    "KeywordsData"
]