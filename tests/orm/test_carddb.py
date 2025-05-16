import unittest
from datetime import date
from mtg_deck_builder.db.models import CardDB, CardPrintingDB, CardSetDB

class TestCardDB(unittest.TestCase):
    def setUp(self):
        # Create a fake set
        self.set1 = CardSetDB(
            set_code="SET1",
            set_name="Alpha",
            release_date=date(2020, 1, 1),
            block="BlockA",
            set_metadata={}
        )
        self.set2 = CardSetDB(
            set_code="SET2",
            set_name="Beta",
            release_date=date(2021, 1, 1),
            block="BlockB",
            set_metadata={}
        )

        # Create printings
        self.printing1 = CardPrintingDB(
            uid="uid1",
            card_name="Test Card",
            artist="Artist1",
            number="001",
            set_code="SET1",
            card_type="Creature — Elf",
            rarity="Common",
            mana_cost="{1}{G}",
            power="2",
            toughness="2",
            abilities=["Trample"],
            flavor_text="A test card.",
            text="Trample",
            colors=["G"],
            legalities={"standard": "Legal"},
            rulings=["Ruling1"],
            foreign_data={"es": "Carta de prueba"},
        )
        self.printing1.set = self.set1

        self.printing2 = CardPrintingDB(
            uid="uid2",
            card_name="Test Card",
            artist="Artist2",
            number="002",
            set_code="SET2",
            card_type="Creature — Elf Warrior",
            rarity="Uncommon",
            mana_cost="{2}{G}{G}",
            power="3",
            toughness="3",
            abilities=["Trample", "Reach"],
            flavor_text="A better test card.",
            text="Trample, Reach",
            colors=["G"],
            legalities={"modern": "Legal"},
            rulings=["Ruling2"],
            foreign_data={"fr": "Carte de test"},
        )
        self.printing2.set = self.set2

        # CardDB with two printings
        self.card = CardDB(name="Test Card")
        self.card.printings = [self.printing1, self.printing2]

    def test_newest_printing(self):
        # Newest printing should be from set2 (2021)
        self.assertEqual(self.card.newest_printing, self.printing2)

    def test_type_property(self):
        self.assertEqual(self.card.type, "Creature — Elf Warrior")

    def test_rarity_property(self):
        self.assertEqual(self.card.rarity, "Uncommon")

    def test_mana_cost_property(self):
        self.assertEqual(self.card.mana_cost, "{2}{G}{G}")

    def test_power_toughness_properties(self):
        self.assertEqual(self.card.power, "3")
        self.assertEqual(self.card.toughness, "3")

    def test_abilities_property(self):
        self.assertEqual(self.card.abilities, ["Trample", "Reach"])

    def test_flavor_text_property(self):
        self.assertEqual(self.card.flavor_text, "A better test card.")

    def test_text_property(self):
        self.assertEqual(self.card.text, "Trample, Reach")

    def test_colors_property(self):
        self.assertEqual(self.card.colors, ["G"])

    def test_legalities_property(self):
        self.assertEqual(self.card.legalities, {"modern": "Legal"})

    def test_rulings_property(self):
        self.assertEqual(self.card.rulings, ["Ruling2"])

    def test_foreign_data_property(self):
        self.assertEqual(self.card.foreign_data, {"fr": "Carte de test"})

    def test_converted_mana_cost(self):
        self.assertEqual(self.card.converted_mana_cost, 4)

    def test_matches_type(self):
        self.assertTrue(self.card.matches_type("creature"))
        self.assertTrue(self.card.matches_type("Elf"))
        self.assertFalse(self.card.matches_type("Artifact"))

    def test_matches_color_identity(self):
        # Subset (default)
        self.assertTrue(self.card.matches_color_identity(["G"]))
        self.assertTrue(self.card.matches_color_identity(["G", "U"]))
        self.assertFalse(self.card.matches_color_identity(["U"]))
        # Any
        self.assertTrue(self.card.matches_color_identity(["G"], match_mode="any"))
        self.assertFalse(self.card.matches_color_identity(["U"], match_mode="any"))
        # Exact
        self.assertTrue(self.card.matches_color_identity(["G"], match_mode="exact"))
        self.assertFalse(self.card.matches_color_identity(["G", "U"], match_mode="exact"))

    def test_is_basic_land(self):
        self.card.printings[0].card_type = "Basic Land — Forest"
        self.card.printings[1].card_type = "Basic Land — Forest"
        self.assertTrue(self.card.is_basic_land())

    def test_get_preferred_printing(self):
        self.assertEqual(self.card.get_preferred_printing(), self.printing2)

    def test_owned_qty_default(self):
        # Should be 0 by default
        self.assertEqual(self.card.owned_qty, 0)

    def test_str_and_repr(self):
        self.assertEqual(str(self.card), "Test Card")
        self.assertIn("Test Card", repr(self.card))

    def test_colorless_card(self):
        # No colors, but has mana cost
        self.card.printings[0].colors = []
        self.card.printings[1].colors = []
        self.card.printings[1].mana_cost = "{3}"
        self.assertTrue(self.card.matches_color_identity(["C"]))
        self.assertFalse(self.card.matches_color_identity(["G"]))

    def test_invalid_match_mode(self):
        with self.assertRaises(ValueError):
            self.card.matches_color_identity(["G"], match_mode="invalid")

if __name__ == "__main__":
    unittest.main()
