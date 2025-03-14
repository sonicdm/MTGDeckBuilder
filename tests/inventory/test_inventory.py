# tests/inventory/test_inventory.py

import unittest
import os
from mtg_deck_builder.models.inventory import Inventory, InventoryItem
from mtg_deck_builder.data_loader import load_inventory_from_txt
from tests.helpers import get_sample_data_path


class TestInventory(unittest.TestCase):
    def test_basic_inventory_creation(self):
        """
        Test creating an Inventory directly with some items in-memory.
        Ensures to_dict() merges duplicates properly.
        """
        items = [
            InventoryItem(card_name="Lightning Bolt", quantity=2),
            InventoryItem(card_name="Evolving Wilds", quantity=4),
            InventoryItem(card_name="Lightning Bolt", quantity=1),  # Duplicate card
        ]
        inv = Inventory(items=items)

        # Check we have 3 items in the list, but 2 are duplicates
        self.assertEqual(len(inv.items), 3)

        inv_dict = inv.to_dict()
        # "Lightning Bolt" should total 3 copies
        self.assertEqual(inv_dict["Lightning Bolt"], 3)
        # "Evolving Wilds" should be 4
        self.assertEqual(inv_dict["Evolving Wilds"], 4)

    def test_negative_or_zero_quantity(self):
        """
        If we accidentally add an item with zero or negative quantity, 
        check how we handle it. Typically we expect the final dict to show 0 or skip it.
        """
        items = [
            InventoryItem(card_name="Goblin Arsonist", quantity=2),
            InventoryItem(card_name="Goblin Arsonist", quantity=-1),  # negative
            InventoryItem(card_name="Goblin Arsonist", quantity=0),
        ]
        inv = Inventory(items=items)
        inv_dict = inv.to_dict()
        # The total for "Goblin Arsonist" = 2 + (-1) + 0 => 1
        # If negative is allowed, it merges. If you prefer skipping negative, 
        # you'd need to handle that logic in your model or test.
        self.assertEqual(inv_dict["Goblin Arsonist"], 1)

    def test_load_from_txt(self):
        """
        OPTIONAL: if you want to test loading from the real 'card inventory.txt' file 
        in this folder. We skip if file not found.
        """
        txt_path = get_sample_data_path("card inventory.txt")
        if not os.path.exists(txt_path):
            self.skipTest(f"{txt_path} not found; skipping test_load_from_txt.")

        inv = load_inventory_from_txt(txt_path)
        self.assertIsInstance(inv, Inventory)
        # Just a sanity check that it loaded some lines
        self.assertTrue(len(inv.items) > 0, "Expected to load at least one item from the inventory file.")


if __name__ == "__main__":
    unittest.main()
