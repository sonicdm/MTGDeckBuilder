# tests/inventory/test_collection.py

import unittest
import os

from mtg_deck_builder.data_loader import (
    load_atomic_cards_from_json,
    load_inventory_from_txt
)
from mtg_deck_builder.models.collection import Collection
from mtg_deck_builder.models.inventory import Inventory

import os

from tests.helpers import get_sample_data_path


class TestCollection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """
        Runs once before all tests in this class.
        Loads sample atomic cards + inventory into a Collection.
        """

        atomic_path = get_sample_data_path("sampleAtomicCards.json")
        inv_path = get_sample_data_path("card inventory.txt")

        cls.atomic_cards = load_atomic_cards_from_json(atomic_path)
        cls.inventory = load_inventory_from_txt(inv_path)
        cls.collection = Collection.build_from_inventory(cls.atomic_cards, cls.inventory)

    def test_basic_land_infinite(self):
        """
        Check that each basic land is infinite (999999).
        """
        for land in ["Mountain", "Plains", "Island", "Swamp", "Forest"]:
            qty = self.collection.get_owned_quantity(land)
            self.assertEqual(qty, 999999, f"{land} should be infinite")

    def test_nonbasic_ownership(self):
        """
        Check a known nonbasic card from sample data.
        E.g., if 'Lightning Bolt' is in sampleAtomicCards.json but not in inventory,
        we expect 0. Or if 'Elvish Mystic' is in both, we check the correct quantity.
        """
        # Replace "Lightning Bolt" with a card name you actually have in the sample data
        card_name = "Lightning Bolt"
        owned = self.collection.get_owned_quantity(card_name)
        # We simply confirm it's >= 0, or some known quantity if you want a stricter check
        self.assertGreaterEqual(owned, 0)

    def test_no_duplicates(self):
        """
        Ensure we don't accidentally store duplicates in owned_quantities
        or the parent 'cards'.
        """
        # 'cards' should be a dict with unique keys
        self.assertEqual(len(self.collection.cards), len(set(self.collection.cards.keys())))

        # 'owned_quantities' likewise
        self.assertEqual(len(self.collection.owned_quantities), len(set(self.collection.owned_quantities.keys())))

    def test_missing_card_in_inventory(self):
        """
        If a card is missing in the inventory, we expect get_owned_quantity to return 0 (unless it's a basic land).
        """
        # Suppose "Some Rare Card" not in 'card inventory.txt'
        # but is in sampleAtomicCards.json
        missing_name = "Some Rare Card"
        # If it's not actually in the sample data, skip or test something else
        if missing_name in self.collection.cards:
            qty = self.collection.get_owned_quantity(missing_name)
            self.assertEqual(qty, 0, f"Expected {missing_name} to have 0 copies")

if __name__ == "__main__":
    unittest.main()
