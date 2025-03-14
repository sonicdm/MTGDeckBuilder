# tests/inventory/test_inventory.py

import unittest
import os

from mtg_deck_builder.models.inventory import Inventory, InventoryItem
from mtg_deck_builder.data_loader import load_inventory_from_txt
from tests.helpers import get_sample_data_path

# We also need these imports for the new integration tests
from mtg_deck_builder.models.cards import AtomicCard, AtomicCards
from mtg_deck_builder.models.collection import Collection

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



class TestCollectionInventoryIntegration(unittest.TestCase):
    """
    Tests creating a Collection from AtomicCards + Inventory
    using in-memory data that matches the user-provided inventory snippet.
    """

    def setUp(self):
        """
        Create a minimal AtomicCards with 12 entries
        matching the user snippet's names & an Inventory referencing them.
        """
        # 1) Define atomic data for 12 cards
        # (the user snippet has 12 lines: 4 lines with '4', 8 lines with '1')
        atomic_cards_dict = {
            "Conclave Mentor": AtomicCard(
                name="Conclave Mentor",
                type="Creature — Centaur Cleric",
                manaValue=2.0,
                colorIdentity=["G", "W"]
            ),
            "Indulging Patrician": AtomicCard(
                name="Indulging Patrician",
                type="Creature — Vampire Noble",
                manaValue=3.0,
                colorIdentity=["W", "B"]
            ),
            "Chrome Replicator": AtomicCard(
                name="Chrome Replicator",
                type="Artifact Creature",
                manaValue=5.0,
                colorIdentity=[]
            ),
            "Sparkhunter Masticore": AtomicCard(
                name="Sparkhunter Masticore",
                type="Artifact Creature — Masticore",
                manaValue=3.0,
                colorIdentity=[]
            ),
            "Bloodfell Caves": AtomicCard(
                name="Bloodfell Caves",
                type="Land",
                manaValue=0.0,
                colorIdentity=["B", "R"]
            ),
            "Blossoming Sands": AtomicCard(
                name="Blossoming Sands",
                type="Land",
                manaValue=0.0,
                colorIdentity=["G", "W"]
            ),
            "Dismal Backwater": AtomicCard(
                name="Dismal Backwater",
                type="Land",
                manaValue=0.0,
                colorIdentity=["U", "B"]
            ),
            "Jungle Hollow": AtomicCard(
                name="Jungle Hollow",
                type="Land",
                manaValue=0.0,
                colorIdentity=["G", "B"]
            ),
            "Radiant Fountain": AtomicCard(
                name="Radiant Fountain",
                type="Land",
                manaValue=0.0,
                colorIdentity=[]
            ),
            "Rugged Highlands": AtomicCard(
                name="Rugged Highlands",
                type="Land",
                manaValue=0.0,
                colorIdentity=["R", "G"]
            ),
            "Scoured Barrens": AtomicCard(
                name="Scoured Barrens",
                type="Land",
                manaValue=0.0,
                colorIdentity=["W", "B"]
            ),
            "Swiftwater Cliffs": AtomicCard(
                name="Swiftwater Cliffs",
                type="Land",
                manaValue=0.0,
                colorIdentity=["U", "R"]
            ),
        }
        self.atomic_cards = AtomicCards(**{"data": atomic_cards_dict})

        # 2) Define Inventory referencing the same names
        inv_items = [
            InventoryItem(card_name="Conclave Mentor", quantity=1),
            InventoryItem(card_name="Indulging Patrician", quantity=1),
            InventoryItem(card_name="Chrome Replicator", quantity=1),
            InventoryItem(card_name="Sparkhunter Masticore", quantity=1),
            InventoryItem(card_name="Bloodfell Caves", quantity=4),
            InventoryItem(card_name="Blossoming Sands", quantity=4),
            InventoryItem(card_name="Dismal Backwater", quantity=4),
            InventoryItem(card_name="Jungle Hollow", quantity=4),
            InventoryItem(card_name="Radiant Fountain", quantity=1),
            InventoryItem(card_name="Rugged Highlands", quantity=4),
            InventoryItem(card_name="Scoured Barrens", quantity=4),
            InventoryItem(card_name="Swiftwater Cliffs", quantity=4),
        ]
        self.inventory = Inventory(items=inv_items)

        # 3) Build the Collection
        self.collection = Collection.build_from_inventory(
            atomic_cards=self.atomic_cards,
            inventory=self.inventory
        )

    def test_collection_size(self):
        """
        Verify the Collection has all the cards from atomic_cards.
        We expect 12 total entries.
        """
        self.assertEqual(
            len(self.collection.cards),
            12,
            "Collection should have 12 card entries from atomic data."
        )

    def test_owned_quantities(self):
        """
        Check that each card in the inventory is set correctly in the collection.
        """
        # Check single-quantity cards
        self.assertEqual(self.collection.get_owned_quantity("Conclave Mentor"), 1)
        self.assertEqual(self.collection.get_owned_quantity("Indulging Patrician"), 1)
        self.assertEqual(self.collection.get_owned_quantity("Chrome Replicator"), 1)
        self.assertEqual(self.collection.get_owned_quantity("Sparkhunter Masticore"), 1)
        self.assertEqual(self.collection.get_owned_quantity("Radiant Fountain"), 1)

        # Check the 4-of lands
        self.assertEqual(self.collection.get_owned_quantity("Bloodfell Caves"), 4)
        self.assertEqual(self.collection.get_owned_quantity("Blossoming Sands"), 4)
        self.assertEqual(self.collection.get_owned_quantity("Dismal Backwater"), 4)
        self.assertEqual(self.collection.get_owned_quantity("Jungle Hollow"), 4)
        self.assertEqual(self.collection.get_owned_quantity("Rugged Highlands"), 4)
        self.assertEqual(self.collection.get_owned_quantity("Scoured Barrens"), 4)
        self.assertEqual(self.collection.get_owned_quantity("Swiftwater Cliffs"), 4)

    def test_no_extras(self):
        """
        Ensure there are no additional keys beyond the 12 in atomic_cards.
        """
        all_keys = list(self.collection.cards.keys())
        expected_keys = list(self.atomic_cards.cards.keys())
        self.assertCountEqual(all_keys, expected_keys, "Collection keys differ from atomic data keys.")


if __name__ == "__main__":
    unittest.main()
