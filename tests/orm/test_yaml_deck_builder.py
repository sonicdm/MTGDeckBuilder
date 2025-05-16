import os
import unittest
import time
import logging
from datetime import date
from mtg_deck_builder.yaml_deck_builder import load_yaml_template, build_deck_from_yaml
from mtg_deck_builder.db.setup import setup_database
from mtg_deck_builder.db.repository import CardRepository, InventoryRepository
from mtg_deck_builder.models.deck import Deck
from mtg_deck_builder.db.models import CardDB, CardPrintingDB, CardSetDB, InventoryItemDB
from mtg_deck_builder.db.bootstrap import bootstrap

logging.basicConfig(level=logging.DEBUG, format='[%(levelname)s][%(threadName)s] %(message)s')

class TestYamlDeckBuilder(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        logging.debug("Setting up minimal in-memory test database...")
        # Setup a shared in-memory DB and load sample data
        cls.db_url = "sqlite:///file:memdb2?mode=memory&cache=shared&uri=true"
        cls.connect_args = {"check_same_thread": False}
        cls.engine = setup_database(cls.db_url, connect_args=cls.connect_args)
        from sqlalchemy.orm import sessionmaker
        cls.Session = sessionmaker(bind=cls.engine)
        cls.session = cls.Session()

        # Insert a minimal set of cards, printings, sets, and inventory for the test
        # Add a set
        test_set = CardSetDB(
            set_code="TST",
            set_name="Test Set",
            release_date=date(2023, 1, 1),
            block="Test Block",
            set_metadata={}
        )
        cls.session.add(test_set)

        # Add cards and printings
        cards = [
            # Priority cards
            ("Lightning Bolt", "{R}", "Instant", ["R"], "Deal damage", "Common"),
            ("Monastery Swiftspear", "{R}", "Creature — Human Monk", ["R"], "Haste", "Uncommon"),
            # Lands
            ("Mountain", "", "Basic Land — Mountain", ["R"], "", "Basic"),
            ("Forest", "", "Basic Land — Forest", ["G"], "", "Basic"),
            # Creatures
            ("Burning-Tree Emissary", "{R}{G}", "Creature — Human Shaman", ["R", "G"], "Aggressive", "Uncommon"),
            ("Kird Ape", "{R}", "Creature — Ape", ["R"], "Aggressive", "Common"),
            # Removal
            ("Shock", "{R}", "Instant", ["R"], "Deal damage", "Common"),
            ("Lava Axe", "{4}{R}", "Sorcery", ["R"], "Deal damage", "Common"),
            # Card draw
            ("Tormenting Voice", "{1}{R}", "Sorcery", ["R"], "Draw a card", "Common"),
            # Buffs
            ("Giant Growth", "{G}", "Instant", ["G"], "+3/+3", "Common"),
            # Utility
            ("Treasure Map", "{2}", "Artifact", [], "Treasure", "Rare"),
        ]
        for name, mana_cost, card_type, colors, text, rarity in cards:
            card = CardDB(name=name)
            cls.session.add(card)
            printing = CardPrintingDB(
                uid=f"{name}-001",
                card_name=name,
                artist="Test Artist",
                number="001",
                set_code="TST",
                card_type=card_type,
                rarity=rarity,
                mana_cost=mana_cost,
                power="2" if "Creature" in card_type else None,
                toughness="2" if "Creature" in card_type else None,
                abilities=["Haste"] if "Haste" in text else [],
                flavor_text="Test card.",
                text=text,
                colors=colors,
                legalities={"standard": "Legal"},
                rulings=[],
                foreign_data={},
            )
            printing.set = test_set
            printing.card = card
            cls.session.add(printing)

        # Add inventory for all cards (simulate owning 4 of each)
        for name, *_ in cards:
            inv = InventoryItemDB(card_name=name, quantity=4, is_infinite=False)
            cls.session.add(inv)

        cls.session.commit()

        # Path to the sample YAML template
        cls.yaml_path = os.path.join(
            os.path.dirname(__file__), "../sample_data/yaml_template.yaml"
        )
        cls.yaml_path = os.path.abspath(cls.yaml_path)
        logging.debug("Minimal test database setup complete.")

    @classmethod
    def tearDownClass(cls):
        logging.debug("Tearing down minimal in-memory test database...")
        cls.session.close()
        cls.engine.dispose()
        logging.debug("Minimal test database teardown complete.")

    def test_build_deck_from_yaml(self):
        logging.debug("Running test_build_deck_from_yaml...")
        start = time.time()
        yaml_data = load_yaml_template(self.yaml_path)
        card_repo = CardRepository(session=self.session)
        inventory_repo = InventoryRepository(self.session)
        deck: Deck = build_deck_from_yaml(
            yaml_data, card_repo, inventory_repo=inventory_repo
        )
        # Check deck size: allow less than requested if not enough cards available
        deck_size = yaml_data["deck"]["size"]
        actual_count = sum(card.owned_qty for card in deck.cards.values())
        logging.debug(f"Deck built with {actual_count} cards in {time.time() - start:.2f}s")
        if actual_count < deck_size:
            logging.warning(f"Deck only contains {actual_count} cards (requested {deck_size}) due to limited card pool.")
        self.assertLessEqual(actual_count, deck_size)
        self.assertGreater(actual_count, 0)
        # Check color identity
        allowed_colors = set(yaml_data["deck"]["colors"])
        for card in deck.cards.values():
            card_colors = set(card.colors or [])
            self.assertTrue(card_colors.issubset(allowed_colors) or (not card_colors and "C" in allowed_colors))
        # Check priority cards
        for pc in yaml_data.get("priority_cards", []):
            name = pc["name"]
            min_copies = pc.get("min_copies", 1)
            if name in deck.cards:
                self.assertGreaterEqual(deck.cards[name].owned_qty, min_copies)
        logging.debug("test_build_deck_from_yaml complete.")

    def test_build_deck_from_full_database(self):
        logging.debug("Running test_build_deck_from_full_database...")
        start = time.time()
        # Store the bootstrapped DB as a file next to the test files
        db_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "test_full_cards.db")
        )
        db_url = f"sqlite:///{db_path}"
        connect_args = {"check_same_thread": False}
        engine = setup_database(db_url, connect_args=connect_args)
        from sqlalchemy.orm import sessionmaker
        Session = sessionmaker(bind=engine)
        session = Session()

        # Paths to full database and inventory
        all_printings_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../../atomic_json_files/AllPrintings.json")
        )
        inventory_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../../inventory_files/card inventory.txt")
        )
        yaml_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../sample_data/yaml_template.yaml")
        )

        logging.debug(f"Bootstrapping full database at {db_path} ...")
        t0 = time.time()
        bootstrap(json_path=all_printings_path, inventory_path=inventory_path, db_url=db_url, use_tqdm=False)
        logging.debug(f"Bootstrapping complete in {time.time() - t0:.2f}s")

        logging.debug("Building deck from full database...")
        t1 = time.time()
        yaml_data = load_yaml_template(yaml_path)
        card_repo = CardRepository(session=session)
        inventory_repo = InventoryRepository(session)
        deck: Deck = build_deck_from_yaml(
            yaml_data, card_repo, inventory_repo=inventory_repo
        )
        # Check deck size: allow less than requested if not enough cards available
        deck_size = yaml_data["deck"]["size"]
        actual_count = sum(card.owned_qty for card in deck.cards.values())
        logging.debug(f"Deck built with {actual_count} cards in {time.time() - t1:.2f}s")
        if actual_count < deck_size:
            logging.warning(f"Deck only contains {actual_count} cards (requested {deck_size}) due to limited card pool.")
        self.assertLessEqual(actual_count, deck_size)
        self.assertGreater(actual_count, 0)
        # Check color identity
        allowed_colors = set(yaml_data["deck"]["colors"])
        for card in deck.cards.values():
            card_colors = set(card.colors or [])
            self.assertTrue(card_colors.issubset(allowed_colors) or (not card_colors and "C" in allowed_colors))
        # Check priority cards
        for pc in yaml_data.get("priority_cards", []):
            name = pc["name"]
            min_copies = pc.get("min_copies", 1)
            if name in deck.cards:
                self.assertGreaterEqual(deck.cards[name].owned_qty, min_copies)
        logging.debug("test_build_deck_from_full_database complete.")

        session.close()
        engine.dispose()

if __name__ == "__main__":
    unittest.main()

