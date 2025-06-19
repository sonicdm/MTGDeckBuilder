from ast import Dict
from contextlib import contextmanager
# from mtg_deck_builder.db.models import CardDB
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
# from mtg_deck_builder.db.repository import CardRepository, InventoryRepository
# from mtg_deck_builder.db.setup import setup_database
# from mtg_deck_builder.db.bootstrap import bootstrap
import json
from pathlib import Path
from typing import Generator, Any, Optional
from mtg_deck_builder.models.card_meta import load_card_types, load_keywords, CardTypesData, KeywordsData

@contextmanager
def get_session(
    db_url: str = "sqlite:///data/mtgjson/AllPrintings.sqlite",
    engine_args: Optional[dict[str, Any]] = None
) -> Generator[Any, None, None]:
    """Context manager for SQLAlchemy session with optional custom engine
    arguments.

    Args:
        db_url: SQLAlchemy database URL.
        engine_args: Arguments to pass to create_engine (e.g., connect_args).

    Yields:
        SQLAlchemy session object.
    """
    engine_args = engine_args or {}

    # Optimize SQLite for fastest possible operations
    if db_url.startswith("sqlite"):
        # Use in-memory DB if specified, else file-based
        if ":memory:" in db_url:
            engine_args.setdefault("connect_args", {}).update(
                {"check_same_thread": False}
            )
        # Use NullPool for fastest connections (no pooling)
        engine_args.setdefault("poolclass", NullPool)

    engine = create_engine(db_url, **engine_args)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


def get_keywords() -> KeywordsData:
    """Load keywords from JSON file.

    Returns:
        Dictionary of keywords data.
    """
    keywords = json.load(open(Path(__file__).parent / "Keywords.json"))
    return KeywordsData.model_validate(keywords)


def get_card_types() -> CardTypesData:
    """Load card types from JSON file.

    Returns:
        Dictionary of card type data.
    """
    card_types = json.load(open(Path(__file__).parent / "CardTypes.json"))
    return CardTypesData.model_validate(card_types)



# __all__ = [
#     # "CardDB",
#     # "CardRepository",
#     # "InventoryRepository",
#     "get_session",
#     "setup_database",
#     "bootstrap",
#     "get_keywords",
#     "get_card_types"
# ]
