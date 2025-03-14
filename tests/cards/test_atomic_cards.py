import unittest
import os
from mtg_deck_builder.models.cards import AtomicCards
from mtg_deck_builder.data_loader import load_atomic_cards_from_json
from tests.helpers import get_sample_data_path


class TestAtomicCards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        json_path = get_sample_data_path("sampleAtomicCards.json")
        cls.atomic_cards = load_atomic_cards_from_json(json_path)

    def test_filter_by_mana_value(self):
        """
        Check we can filter cards by manaValue < 3, etc.
        """
        # e.g. find all spells with MV < 3
        cheap_spells = self.atomic_cards.filter_cards(
            mana_value=3,
            mana_op="<"
        )
        # Expect Lightning Bolt (MV=1), Leonin Scimitar (1), Elvish Visionary (2?), etc.
        cheap_names = {c.name for c in cheap_spells}
        self.assertIn("Lightning Bolt", cheap_names)
        self.assertIn("Leonin Scimitar", cheap_names)
        self.assertIn("Elvish Visionary", cheap_names)
        self.assertNotIn("Angelic Defender", cheap_names)  # MV=3 => not < 3

    def test_filter_by_toughness(self):
        """
        Find creatures with toughness >= 4
        """
        big_butts = self.atomic_cards.filter_cards(
            type_query="creature",
            toughness_value=4,
            toughness_op=">="
        )
        big_names = {c.name for c in big_butts}
        # Angelic Defender => 2/4
        self.assertIn("Angelic Defender", big_names)
        # Nicol Bolas => 4/4
        self.assertIn("Nicol Bolas, the Ravager", big_names)
        # Battle Mammoth => 6/5
        self.assertIn("Battle Mammoth", big_names)
        # Elvish Visionary => 1/1 => not included
        self.assertNotIn("Elvish Visionary", big_names)

    def test_filter_big_green_trample(self):
        """
        Check multi-constraint: EXACT color identity = {G}, keyword=Trample, power >=5
        Should match Battle Mammoth (6/5, G, Trample)
        """
        results = self.atomic_cards.filter_cards(
            color_identity=["G"],
            color_mode="exact",
            keyword_query="Trample",
            power_value=5,
            power_op=">="
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].name, "Battle Mammoth")

    def test_filter_multi(self):
        """
        Another multi-constraint example: 'Nicol Bolas' in name, power==4,
        color identity containing R
        """
        # color_identity containing R => query set is {R} subset of the card's CI
        results = self.atomic_cards.filter_cards(
            name_query="Nicol Bolas",
            color_identity=["R"],
            color_mode="contains",
            power_value=4,
            power_op="=="
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].name, "Nicol Bolas, the Ravager")

if __name__ == "__main__":
    unittest.main()
