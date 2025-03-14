# tests/test_full_integration.py

import unittest
import os

from mtg_deck_builder.data_loader import (
    load_atomic_cards_from_json,
    load_inventory_from_txt
)
from mtg_deck_builder.models.collection import Collection
from mtg_deck_builder.models.inventory import Inventory
from tests.helpers import get_sample_data_path  # your helper that returns a path

class TestFullIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """
        Loads the large AtomicCards.json and card inventory.txt from sample_data,
        then builds a Collection. This ensures the entire pipeline can handle
        real or large data without error.
        """
        atomic_json_path = get_sample_data_path("AtomicCards.json")
        inventory_txt_path = get_sample_data_path("card inventory.txt")

        # Load the large dataset
        cls.atomic_cards = load_atomic_cards_from_json(atomic_json_path)
        cls.inventory = load_inventory_from_txt(inventory_txt_path)
        cls.collection = Collection.build_from_inventory(cls.atomic_cards, cls.inventory)

    def test_large_dataset_loaded(self):
        """
        Check that we have a substantial number of cards in atomic_cards/cards.
        This ensures we actually loaded the big dataset.
        """
        num_cards = len(self.atomic_cards.cards)
        self.assertGreater(num_cards, 100, "Expected a large dataset with >100 cards")

    def test_basic_collection_integration(self):
        """
        Check that we can build a small deck from the collection without error,
        verifying the pipeline works end-to-end.
        """
        # For instance, let's pick up to 20 cards from alphabetical order
        # (If you have a specialized method, you can do that here.)
        sorted_cards = sorted(self.collection.cards.items(), key=lambda x: x[0])
        deck_size = 0
        for card_name, card_obj in sorted_cards:
            owned = self.collection.get_owned_quantity(card_name)
            if owned > 0:
                deck_size += owned
            if deck_size >= 20:
                break

        self.assertGreater(deck_size, 0, "Expected to build at least some deck from the data")

    def test_basic_lands_in_collection(self):
        """
        Ensure that the basic lands are recognized and infinite.
        """
        for land in ["Mountain", "Plains", "Island", "Swamp", "Forest"]:
            qty = self.collection.get_owned_quantity(land)
            self.assertEqual(qty, 999999, f"{land} should be infinite in the large dataset")

if __name__ == "__main__":
    unittest.main()
