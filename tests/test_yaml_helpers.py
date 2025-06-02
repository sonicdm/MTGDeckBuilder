import pytest
import logging
from mtg_deck_builder.yaml_builder import helpers

class DummyCard:
    def __init__(self, name, colors=None, text=None, rarity=None, legalities=None, owned_qty=1):
        self.name = name
        self.colors = colors or []
        self.text = text or ""
        self.rarity = rarity
        self.legalities = legalities or {}
        self.owned_qty = owned_qty
    def matches_color_identity(self, allowed, mode):
        return set(self.colors) <= set(allowed)
    def matches_type(self, t):
        return t.lower() in self.name.lower() or t.lower() in self.text.lower()
    def is_basic_land(self):
        return self.name in ["Plains", "Island", "Swamp", "Mountain", "Forest"]

class DummyRepo:
    def __init__(self, cards):
        self._cards = cards
    def get_all_cards(self):
        return self._cards
    def find_by_name(self, name):
        for c in self._cards:
            if c.name == name:
                return c
        return None

def test_run_callback_invokes_and_logs(caplog):
    called = {}
    def cb(**kwargs):
        called["ok"] = True
    helpers._run_callback({"foo": cb}, "foo", x=1)
    assert called["ok"]
    def bad_cb(**kwargs):
        raise ValueError("fail")
    with caplog.at_level(logging.WARNING):
        helpers._run_callback({"bar": bad_cb}, "bar")
    assert any("CALLBACK ERROR" in r.getMessage() for r in caplog.records)

def test_select_priority_cards_color_and_legality(caplog):
    card1 = DummyCard("A", colors=["R"], rarity="rare", legalities={"modern": "legal"})
    card2 = DummyCard("B", colors=["G"], rarity="rare", legalities={"modern": "not_legal"})
    repo = DummyRepo([card1, card2])
    pri = [type("PC", (), {"name": "A", "min_copies": 2})]
    selected = helpers._select_priority_cards(pri, repo, allowed_colors=["R"], color_match_mode=None, legalities=["modern"], max_copies=4)
    assert "A" in selected
    pri2 = [type("PC", (), {"name": "B", "min_copies": 1})]
    selected2 = helpers._select_priority_cards(pri2, repo, allowed_colors=["R"], color_match_mode=None, legalities=["modern"], max_copies=4)
    assert "B" not in selected2
    # Should log a warning for not matching legality
    with caplog.at_level(logging.WARNING):
        helpers._select_priority_cards(pri2, repo, allowed_colors=["R"], color_match_mode=None, legalities=["modern"], max_copies=4)
    assert any("doesn't match color/legality" in r.getMessage() for r in caplog.records)

def test_select_special_lands_callback():
    lands = [DummyCard("Temple", text="Add {R}")]
    called = {}
    def cb(selected=None, **kwargs):
        called["lands"] = selected
    selected = helpers._select_special_lands(lands, ["temple"], [], 1, ["R"], callbacks={"after_special_lands": cb})
    assert called["lands"] == selected
    assert selected[0].name == "Temple"

def test_distribute_basic_lands_distribution():
    selected = {}
    basics = [DummyCard("Plains", colors=["W"]), DummyCard("Island", colors=["U"])]
    helpers._distribute_basic_lands(selected, basics, allowed_colors=["W", "U"], num_basic_needed=4)
    assert "Plains" in selected or "Island" in selected
    total = sum(c.owned_qty for c in selected.values())
    assert total == 4

def test_distribute_basic_lands_no_basics():
    with pytest.raises(RuntimeError):
        helpers._distribute_basic_lands({}, [], allowed_colors=["W"], num_basic_needed=2)

def test_match_priority_text_regex_and_substring():
    card = DummyCard("Bolt", text="Deal 3 damage to any target.")
    assert helpers._match_priority_text(card, ["/damage/"])
    assert helpers._match_priority_text(card, ["3 damage"])
    assert not helpers._match_priority_text(card, ["lifelink"])

