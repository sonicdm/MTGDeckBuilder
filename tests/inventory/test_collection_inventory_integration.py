import unittest
from pydantic import ValidationError
from mtg_deck_builder.models.cards import AtomicCards, AtomicCard
from mtg_deck_builder.models.collection import Collection
from mtg_deck_builder.models.inventory import Inventory, InventoryItem

class TestCollectionInventoryIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """
        Define minimal atomic data in-memory that matches the partial inventory.
        Then create an Inventory object and build a Collection from it.
        """
        # 1) Minimal atomic data for the test (only the cards we care about)
        # In a real test, you'd define all relevant fields or parse from a small JSON
        atomic_cards_data = {
            "data": {
                "Conclave Mentor": {
                    "name": "Conclave Mentor",
                    "type": "Creature — Centaur Cleric",
                    "colorIdentity": ["G", "W"],
                    "manaValue": 2.0,
                },
                "Indulging Patrician": {
                    "name": "Indulging Patrician",
                    "type": "Creature — Vampire Noble",
                    "colorIdentity": ["W", "B"],
                    "manaValue": 3.0,
                },
                "Chrome Replicator": {
                    "name": "Chrome Replicator",
                    "type": "Artifact Creature — Construct",
                    "colorIdentity": [],
                    "manaValue": 5.0,
                },
                "Sparkhunter Masticore": {
                    "name": "Sparkhunter Masticore",
                    "type": "Artifact Creature — Masticore",
                    "colorIdentity": [],
                    "manaValue": 3.0,
                },
                "Bloodfell Caves": {
                    "name": "Bloodfell Caves",
                    "type": "Land",
                    "colorIdentity": ["B", "R"],
                    "manaValue": 0.0,
                },
                "Blossoming Sands": {
                    "name": "Blossoming Sands",
                    "type": "Land",
                    "colorIdentity": ["G", "W"],
                    "manaValue": 0.0,
                },
                "Dismal Backwater": {
                    "name": "Dismal Backwater",
                    "type": "Land",
                    "colorIdentity": ["U", "B"],
                    "manaValue": 0.0,
                },
                "Jungle Hollow": {
                    "name": "Jungle Hollow",
                    "type": "Land",
                    "colorIdentity": ["B", "G"],
                    "manaValue": 0.0,
                },
                "Radiant Fountain": {
                    "name": "Radiant Fountain",
                    "type": "Land",
                    "colorIdentity": [],
                    "manaValue": 0.0,
                },
                "Rugged Highlands": {
                    "name": "Rugged Highlands",
                    "type": "Land",
                    "colorIdentity": ["R", "G"],
                    "manaValue": 0.0,
                },
                "Scoured Barrens": {
                    "name": "Scoured Barrens",
                    "type": "Land",
                    "colorIdentity": ["W", "B"],
                    "manaValue": 0.0,
                },
                "Swiftwater Cliffs": {
                    "name": "Swiftwater Cliffs",
                    "type": "Land",
                    "colorIdentity": ["U", "R"],
                    "manaValue": 0.0,
                }
            }
        }

        # Parse into an AtomicCards model
        cls.atomic_cards = AtomicCards.model_validate(atomic_cards_data)

        # 2) Partial inventory data from your snippet
        # We define it inline as a list of InventoryItem
        inventory_items = [
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
        cls.inventory = Inventory.from_list(inventory_items)

        # 3) Build the Collection
        cls.collection = Collection.build_from_inventory(cls.atomic_cards, cls.inventory)

    def test_collection_size(self):
        """
        Verify the Collection has all the cards from atomic_cards.
        """
        # We expect 12 keys in 'data'
        self.assertEqual(len(self.collection.cards), 12, "Collection should have 12 card entries from atomic data.")

    def test_owned_quantities(self):
        """
        Check that each card in the inventory has the correct owned quantity in the collection.
        """
        expected = {
            "Conclave Mentor": 1,
            "Indulging Patrician": 1,
            "Chrome Replicator": 1,
            "Sparkhunter Masticore": 1,
            "Bloodfell Caves": 4,
            "Blossoming Sands": 4,
            "Dismal Backwater": 4,
            "Jungle Hollow": 4,
            "Radiant Fountain": 1,
            "Rugged Highlands": 4,
            "Scoured Barrens": 4,
            "Swiftwater Cliffs": 4
        }
        for card_name, qty in expected.items():
            owned = self.collection.get_owned_quantity(card_name)
            self.assertEqual(owned, qty, f"Expected {qty} copies of {card_name}, got {owned}.")

    def test_missing_card_in_inventory(self):
        """
        If we query a card not in the inventory, it should return 0.
        """
        owned = self.collection.get_owned_quantity("Nonexistent Card")
        self.assertEqual(owned, 0, "Expected 0 for a card not in inventory.")


if __name__ == "__main__":
    unittest.main()
