import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
import tempfile

from mtg_deck_builder.db.bootstrap import bootstrap
from mtg_deck_builder.db.repository import CardRepository, InventoryRepository
from mtg_deck_builder.db import get_session

TEST_DB_URL = "sqlite:///tests/test_cards.db"
CARD_JSON = "tests/sample_data/AllPrintings.json"
INVENTORY_FILE = "tests/sample_data/card inventory.txt"

@pytest.fixture(scope="session")
def test_db_session():
    bootstrap(json_path=CARD_JSON, inventory_path=INVENTORY_FILE, db_url=TEST_DB_URL)

    engine = create_engine(TEST_DB_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

@pytest.fixture
def test_repositories(test_db_session):
    return (
        CardRepository(session=test_db_session),
        InventoryRepository(session=test_db_session),
    )

@pytest.fixture(scope="session")
def create_dummy_db():
    """
    Pytest fixture to create a temporary SQLite DB loaded with sample data and inventory.
    Yields a SQLAlchemy session for use in tests.
    """
    # Create a temp file for the SQLite DB
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)
    db_url = f"sqlite:///{db_path}"

    # Paths to sample data
    sample_data_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "sample_data", "sample_allprintings.json"))
    sample_inventory_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "sample_data", "sample_inventory.txt"))

    # Bootstrap the DB
    bootstrap(
        json_path=sample_data_path,
        inventory_path=sample_inventory_path,
        db_url=db_url,
        use_tqdm=False
    )

    # Yield a session
    with get_session(db_url) as session:
        yield session

    # Cleanup
    try:
        os.remove(db_path)
    except Exception:
        pass
