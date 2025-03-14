import unittest
import os
from mtg_deck_builder.models.cards import AtomicCard, AtomicCards
from mtg_deck_builder.data_loader import load_atomic_cards_from_json
from tests.helpers import get_sample_data_path


class TestAtomicCard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Load the full sample data once
        json_path = get_sample_data_path("sampleAtomicCards.json")
        cls.atomic_cards = load_atomic_cards_from_json(json_path)

        # For convenience, pick out references to certain cards
        cls.bolt = cls.atomic_cards.cards["Lightning Bolt"]  # Instant, R, no power/toughness
        cls.angel = cls.atomic_cards.cards["Angelic Defender"]  # 2/4, W
        cls.bolas = cls.atomic_cards.cards["Nicol Bolas, the Ravager"]  # 4/4, UBR
        cls.equipment = cls.atomic_cards.cards["Leonin Scimitar"]  # artifact equipment, no power/toughness
        cls.battle_mammoth = cls.atomic_cards.cards["Battle Mammoth"]  # 6/5, G

    def test_power_toughness_parsing(self):
        """
        Ensure power/toughness are parsed as floats or None if not numeric.
        """
        # Lightning Bolt has no power/toughness => None
        self.assertIsNone(self.bolt.power)
        self.assertIsNone(self.bolt.toughness)

        # Angelic Defender => power=2.0, toughness=4.0
        self.assertEqual(self.angel.power, 2.0)
        self.assertEqual(self.angel.toughness, 4.0)

        # Nicol Bolas => 4.0 / 4.0
        self.assertEqual(self.bolas.power, 4.0)
        self.assertEqual(self.bolas.toughness, 4.0)

    def test_mana_value_parsing(self):
        """
        Check that manaValue is parsed, falling back to convertedManaCost if missing.
        """
        # Lightning Bolt => manaValue=1.0
        self.assertEqual(self.bolt.manaValue, 1.0)
        # Leonin Scimitar => manaValue=1.0
        self.assertEqual(self.equipment.manaValue, 1.0)

    def test_matches_power(self):
        """
        Test the matches_power(value, op) method.
        """
        # Angelic Defender => power=2
        self.assertTrue(self.angel.matches_power(2, "=="))
        self.assertTrue(self.angel.matches_power(1, ">"))
        self.assertFalse(self.angel.matches_power(5, ">="))

        # Lightning Bolt => None, always false
        self.assertFalse(self.bolt.matches_power(1, "=="))
        self.assertFalse(self.bolt.matches_power(0, ">="))

    def test_matches_toughness(self):
        """
        Test the matches_toughness(value, op) method.
        """
        # Battle Mammoth => toughness=5
        self.assertTrue(self.battle_mammoth.matches_toughness(5, "=="))
        self.assertTrue(self.battle_mammoth.matches_toughness(4, ">"))
        self.assertFalse(self.battle_mammoth.matches_toughness(6, ">="))

    def test_matches_mana_value(self):
        """
        Test the matches_mana_value(value, op) method.
        """
        # Lightning Bolt => 1.0
        self.assertTrue(self.bolt.matches_mana_value(1, "=="))
        self.assertFalse(self.bolt.matches_mana_value(2, "=="))
        self.assertTrue(self.bolt.matches_mana_value(2, "<"))

        # Nicol Bolas => 4
        self.assertTrue(self.bolas.matches_mana_value(3, ">"))  # 4 > 3 => True
        self.assertFalse(self.bolas.matches_mana_value(3, "<="))  # 4 <= 3 => False


if __name__ == "__main__":
    unittest.main()
