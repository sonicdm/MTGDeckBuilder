# This file contains pytest fixtures and dummy classes for testing.

import os
import tempfile
import pytest
from pathlib import Path
from mtg_deck_builder.db.bootstrap import bootstrap
from mtg_deck_builder.db import get_session

class DummyCard:
    def __init__(self, name, colors=None, owned_qty=1, rarity=None, legalities=None, text=None, converted_mana_cost=0, type=None, power=None, toughness=None):
        self.name = name
        self.colors = colors or []
        self.owned_qty = owned_qty
        self.rarity = rarity or "common"
        self.legalities = legalities or {}
        self.text = text or ""
        self.converted_mana_cost = converted_mana_cost
        self.type = type or "Creature"
        self.power = power
        self.toughness = toughness
        
    def matches_color_identity(self, allowed, mode):
        return set(self.colors) <= set(allowed)
        
    def matches_type(self, type_str):
        return type_str.lower() in self.type.lower()
        
    def is_basic_land(self):
        return self.type.lower() == "basic land"
        
    def __repr__(self):
        return f"DummyCard({self.name}, CMC={self.converted_mana_cost}, Type={self.type})"

class DummyRepo:
    def __init__(self, cards):
        self._cards = cards
        self.session = None
    def get_all_cards(self):
        return self._cards
    def find_by_name(self, name):
        for c in self._cards:
            if c.name == name:
                return c
        return None
    def filter_cards(self, color_identity=None, color_mode=None, legal_in=None):
        # For test purposes, just return self (no filtering)
        return self
    def __iter__(self):
        return iter(self._cards)

class DummyInventoryRepo:
    def __init__(self):
        pass

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
    sample_data_path = Path(__file__).parent / "sample_data" / "sample_allprintings.json"
    sample_inventory_path = Path(__file__).parent / "sample_data" / "sample_inventory.txt"

    # Bootstrap the DB
    bootstrap(
        json_path=str(sample_data_path),
        inventory_path=str(sample_inventory_path),
        db_url=db_url,
        use_tqdm=False
    )

    # Yield a session
    with get_session(db_url) as session:
        yield session

    # Cleanup
    try:
        Path(db_path).unlink()
    except Exception:
        pass
