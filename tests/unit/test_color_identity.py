import pytest
from mtg_deck_builder.db.models import CardDB

class DummyPrinting:
    def __init__(self, colors, mana_cost=""):
        self.colors = colors
        self.mana_cost = mana_cost

@pytest.mark.parametrize("card_colors, mana_cost, query_colors, mode, expected", [
    (["R"], "{R}", ["R"], "subset", True),
    (["R"], "{R}", ["R", "G"], "subset", True),
    (["R"], "{R}", ["G"], "subset", False),
    (["R"], "{R}", ["R"], "exact", True),
    (["R"], "{R}", ["R", "G"], "exact", False),
    (["R"], "{R}", ["R", "G"], "any", True),
    (["R"], "{R}", ["G"], "any", False),
    ([], "", ["C"], "subset", True),
    ([], "", ["C"], "exact", True),
    ([], "", ["R"], "subset", False),
    (["G", "R"], "{G}{R}", ["R", "G"], "exact", True),
    (["G", "R"], "{G}{R}", ["R"], "subset", False),
    (["G", "R"], "{G}{R}", ["R", "G", "B"], "subset", True),
    (["G", "R"], "{G}{R}", ["R", "G", "B"], "any", True),
    (["G", "R"], "{G}{R}", ["B"], "any", False),
])
def test_matches_color_identity(card_colors, mana_cost, query_colors, mode, expected):
    card = CardDB(name="TestCard")
    card.newest_printing_rel = DummyPrinting(card_colors, mana_cost)
    assert card.matches_color_identity(query_colors, mode) == expected
