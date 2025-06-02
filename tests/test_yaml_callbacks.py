import pytest
import logging
from mtg_deck_builder.yaml_builder import callbacks

class DummyCard:
    def __init__(self, name, rarity=None, owned_qty=1):
        self.name = name
        self.rarity = rarity
        self.owned_qty = owned_qty

def test_log_summary_logs(caplog):
    cards = {
        "A": DummyCard("A", owned_qty=2),
        "B": DummyCard("B", owned_qty=3)
    }
    with caplog.at_level(logging.INFO):
        callbacks.log_summary(cards)
    assert any("Deck so far" in r.getMessage() for r in caplog.records)
    assert any("A x2" in r.getMessage() or "B x3" in r.getMessage() for r in caplog.records)

def test_assert_no_commons_pass():
    cards = {"A": DummyCard("A", rarity="uncommon")}
    callbacks.assert_no_commons(cards)

def test_assert_no_commons_fail():
    cards = {"A": DummyCard("A", rarity="common")}
    with pytest.raises(AssertionError):
        callbacks.assert_no_commons(cards)

def test_ensure_card_present_pass():
    cards = {"A": DummyCard("A", owned_qty=2)}
    cb = callbacks.ensure_card_present("A", min_copies=2)
    cb(cards)

def test_ensure_card_present_missing():
    cards = {"A": DummyCard("A", owned_qty=2)}
    cb = callbacks.ensure_card_present("B", min_copies=1)
    with pytest.raises(AssertionError):
        cb(cards)

def test_ensure_card_present_not_enough():
    cards = {"A": DummyCard("A", owned_qty=1)}
    cb = callbacks.ensure_card_present("A", min_copies=2)
    with pytest.raises(AssertionError):
        cb(cards)

def test_limit_card_copies_pass():
    cards = {"A": DummyCard("A", owned_qty=2)}
    cb = callbacks.limit_card_copies(max_allowed=4)
    cb(cards)

def test_limit_card_copies_fail():
    cards = {"A": DummyCard("A", owned_qty=5)}
    cb = callbacks.limit_card_copies(max_allowed=4)
    with pytest.raises(AssertionError):
        cb(cards)

def test_log_special_lands_logs(caplog):
    lands = [DummyCard("Plains"), DummyCard("Island")]
    with caplog.at_level(logging.INFO):
        callbacks.log_special_lands(lands)
    assert any("Special lands" in r.getMessage() for r in caplog.records)

