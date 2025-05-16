import os
import tempfile
import json
import unittest
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from mtg_deck_builder.db.setup import setup_database
from mtg_deck_builder.db.models import CardDB, CardSetDB, InventoryItemDB
from mtg_deck_builder.db.bootstrap import bootstrap
from mtg_deck_builder.db.repository import CardRepository

def make_minimal_json(path):
    # Minimal card/set data for testing
    data = {
        "meta": {"date": "2024-06-01"},
        "data": {
            "ABC": {
                "name": "Test Set",
                "releaseDate": "2024-06-01",
                "block": "Test Block",
                "cards": [
                    {
                        "uuid": "card-001",
                        "name": "Test Card",
                        "type": "Creature",
                        "rarity": "Common",
                        "manaCost": "{1}{G}",
                        "power": 2,
                        "toughness": 2,
                        "keywords": ["Trample"],
                        "flavorText": "A test card.",
                        "text": "Trample",
                        "artist": "Test Artist",
                        "number": "001",
                        "colorIdentity": ["G"],
                        "legalities": {"standard": "Legal"},
                        "rulings": [],
                        "foreignData": {},
                    }
                ]
            }
        }
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)

class TestDBBootstrap(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Use a shared in-memory SQLite DB for all tests in this class
        cls.db_url = "sqlite:///file:memdb1?mode=memory&cache=shared&uri=true"
        cls.connect_args = {"check_same_thread": False}
        # Create a temp file for the JSON (inventory can be in temp too)
        cls.tmpdir = tempfile.TemporaryDirectory()
        cls.json_path = os.path.join(cls.tmpdir.name, "test_cards.json")
        make_minimal_json(cls.json_path)

    @classmethod
    def tearDownClass(cls):
        cls.tmpdir.cleanup()

    def setUp(self):
        self.engine = setup_database(self.db_url, poolclass=NullPool, connect_args=self.connect_args)
        self.Session = sessionmaker(bind=self.engine)
        self.session = None

    def tearDown(self):
        if self.session is not None:
            self.session.close()
            self.session = None
        if self.engine is not None:
            self.engine.dispose()
            self.engine = None

    def test_db_creation_and_loading(self):
        # Run bootstrap to create and load the DB (uses the same shared in-memory DB)
        bootstrap(json_path=self.json_path, db_url=self.db_url)
        self.session = self.Session()
        cards = self.session.query(CardDB).all()
        sets = self.session.query(CardSetDB).all()
        self.assertEqual(len(cards), 1)
        self.assertEqual(len(sets), 1)
        self.assertEqual(cards[0].name, "Test Card")
        self.assertEqual(sets[0].set_name, "Test Set")

    def test_inventory_loading(self):
        inv_path = os.path.join(self.tmpdir.name, "test_inventory.txt")
        with open(inv_path, "w", encoding="utf-8") as f:
            f.write("2 Test Card\n")
        # Run bootstrap with inventory (uses the same shared in-memory DB)
        bootstrap(json_path=self.json_path, inventory_path=inv_path, db_url=self.db_url)
        self.session = self.Session()
        inv = self.session.query(InventoryItemDB).all()
        # Find the Test Card entry and check its quantity
        test_card = next((item for item in inv if item.card_name == "Test Card"), None)
        self.assertIsNotNone(test_card)
        self.assertEqual(test_card.quantity, 2)

    def test_get_owned_cards_by_inventory(self):
        # Prepare inventory file and bootstrap DB
        inv_path = os.path.join(self.tmpdir.name, "test_inventory.txt")
        with open(inv_path, "w", encoding="utf-8") as f:
            f.write("2 Test Card\n")
            f.write("1 Nonexistent Card\n")
        bootstrap(json_path=self.json_path, inventory_path=inv_path, db_url=self.db_url)
        self.session = self.Session()
        # Query inventory items
        from mtg_deck_builder.db.models import InventoryItemDB
        inventory_items = self.session.query(InventoryItemDB).all()
        # Use CardRepository to get owned cards
        repo = CardRepository(session=self.session)
        owned_repo = repo.get_owned_cards_by_inventory(inventory_items)
        owned_cards = owned_repo.get_all_cards()
        # Only "Test Card" should be present (not "Nonexistent Card")
        self.assertEqual(len(owned_cards), 1)
        self.assertEqual(owned_cards[0].name, "Test Card")

if __name__ == "__main__":
    unittest.main()
