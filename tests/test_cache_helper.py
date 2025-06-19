import os
import time
import pytest
from mtg_deck_builder.db.cache_helper import get_universal_cache
from mtg_deck_builder.db import get_session
from mtg_deck_builder.db.models import CardDB, Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from tests.helpers import get_sample_data_path

def setup_test_db():
    # Use a sample DB if available, else create a temp one
    db_path = get_sample_data_path("test_cards.db")
    if os.path.exists(db_path):
        return db_path, None
    import tempfile, shutil
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test_cards.db")
    db_url = f"sqlite:///{db_path}"
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    card1 = CardDB(name="Test Card 1")
    card2 = CardDB(name="Test Card 2")
    session.add_all([card1, card2])
    session.commit()
    session.close()
    return db_path, temp_dir

def teardown_test_db(temp_dir):
    if temp_dir:
        import shutil
        try:
            shutil.rmtree(temp_dir)
        except PermissionError:
            # On Windows, SQLite may keep file handles open
            # Just ignore this error in tests
            pass

def loader_func(session, columns):
    query = session.query(CardDB)
    if columns:
        from sqlalchemy.orm import load_only
        # When using load_only, we need to use the actual model attributes, not strings
        try:
            # Get the class attributes, not string names
            model_attrs = []
            for col_name in columns:
                if hasattr(CardDB, col_name):
                    model_attrs.append(getattr(CardDB, col_name))

            if model_attrs:  # Only apply if we found valid attributes
                query = query.options(load_only(*model_attrs))
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Error in load_only: {e}")
            # Fall back to loading all columns if there's an error
    return query.all()

def test_get_universal_cache_basic():
    db_path, temp_dir = setup_test_db()
    session_factory = lambda: get_session(f"sqlite:///{db_path}")
    columns = ["name", "colors", "mana_cost", "type", "rarity"]
    try:
        session, cards = get_universal_cache(db_path, session_factory, loader_func, columns=columns, ttl=10)
        assert session is not None
        assert isinstance(cards, list)
        assert len(cards) >= 2
        names = sorted([c.name for c in cards])
        assert "Test Card 1" in names and "Test Card 2" in names
    finally:
        teardown_test_db(temp_dir)

def test_get_universal_cache_caching():
    db_path, temp_dir = setup_test_db()
    session_factory = lambda: get_session(f"sqlite:///{db_path}")
    columns = ["name", "colors", "mana_cost", "type", "rarity"]
    try:
        session1, cards1 = get_universal_cache(db_path, session_factory, loader_func, columns=columns, ttl=10)
        session2, cards2 = get_universal_cache(db_path, session_factory, loader_func, columns=columns, ttl=10)
        assert session1 is session2
        assert cards1 == cards2
    finally:
        teardown_test_db(temp_dir)

def test_get_universal_cache_invalidate_on_mtime():
    db_path, temp_dir = setup_test_db()
    session_factory = lambda: get_session(f"sqlite:///{db_path}")
    columns = ["name", "colors", "mana_cost", "type", "rarity"]
    try:
        session1, cards1 = get_universal_cache(db_path, session_factory, loader_func, columns=columns, ttl=10)
        # Touch the file to update mtime
        time.sleep(1)
        with open(db_path, "a") as f:
            f.write(" ")
        session2, cards2 = get_universal_cache(db_path, session_factory, loader_func, columns=columns, ttl=10)
        assert session1 is not session2
    finally:
        teardown_test_db(temp_dir)

def test_get_universal_cache_invalidate_on_ttl():
    db_path, temp_dir = setup_test_db()
    session_factory = lambda: get_session(f"sqlite:///{db_path}")
    columns = ["name", "colors", "mana_cost", "type", "rarity"]
    try:
        session1, cards1 = get_universal_cache(db_path, session_factory, loader_func, columns=columns, ttl=1)
        time.sleep(1.1)
        session2, cards2 = get_universal_cache(db_path, session_factory, loader_func, columns=columns, ttl=1)
        assert session1 is not session2
    finally:
        teardown_test_db(temp_dir)

