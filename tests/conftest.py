import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from mtg_deck_builder.db.bootstrap import bootstrap
from mtg_deck_builder.db.repository import CardRepository, InventoryRepository

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
