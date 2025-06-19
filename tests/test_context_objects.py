"""
Pytest suite for DeckBuildContext and ContextCard classes.

This module contains tests for the deck building context system, including:
- Card addition and replacement
- Quantity management
- Color counting
- Logging and condition tracking
- Context queries and exports
"""

import pytest
import yaml
from pathlib import Path
from mtg_deck_builder.yaml_builder.helpers import DeckBuildContext, ContextCard

# --- Fixtures ---
@pytest.fixture(scope="module")
def deck_config():
    """Load a real deck config from cobra-kai.yaml."""
    config_path = Path(__file__).parent / "sample_data" / "sample_deck_configs" / "cobra-kai.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    # Simulate DeckConfig-like object for DeckBuildContext
    class DeckConfigShim:
        def __init__(self, d):
            deck = d["deck"]
            self.max_card_copies = deck.get("max_card_copies", 4)
            self.size = deck.get("size", 60)
            self.colors = deck.get("colors", [])
            self.color_match_mode = deck.get("color_match_mode", "subset")
            self.legalities = deck.get("legalities", ["modern"])
            self.owned_cards_only = deck.get("owned_cards_only", False)
            self.allow_colorless = deck.get("allow_colorless", True)
            self.mana_curve = deck.get("mana_curve", None)
            self.name = deck.get("name", "Test Deck")
    return DeckConfigShim(config)

@pytest.fixture
def context(deck_config):
    return DeckBuildContext(deck_config)

# --- MockCard for ContextCard tests ---
class MockCard:
    def __init__(self, name, colors=None):
        self.name = name
        self.colors = colors or []
        self.type = "Creature"
        self.text = ""
        self.rarity = "common"
        self.converted_mana_cost = 3
        self.owned_qty = 4

# --- ContextCard tests ---
def test_context_card_initialization():
    card = MockCard("Lightning Bolt", ["R"])
    context_card = ContextCard(base_card=card)
    assert context_card.name == "Lightning Bolt"
    assert context_card.quantity == 1
    assert len(context_card.reasons) == 0
    assert len(context_card.sources) == 0
    assert context_card.score is None

def test_context_card_add_reason():
    card = MockCard("Lightning Bolt", ["R"])
    context_card = ContextCard(base_card=card)
    context_card.add_reason("High priority removal")
    assert any("High priority removal" in r for r in context_card.reasons)

def test_context_card_add_source():
    card = MockCard("Lightning Bolt", ["R"])
    context_card = ContextCard(base_card=card)
    context_card.add_source("priority_list")
    assert "priority_list" in context_card.sources

def test_context_card_set_quantity():
    card = MockCard("Lightning Bolt", ["R"])
    context_card = ContextCard(base_card=card)
    context_card.set_quantity(4)
    assert context_card.quantity == 4
    context_card.set_quantity(0)
    assert context_card.quantity == 1

def test_context_card_mark_replaced():
    card = MockCard("Lightning Bolt", ["R"])
    context_card = ContextCard(base_card=card)
    context_card.mark_replaced("Shock")
    assert context_card.replaced_by == "Shock"
    assert context_card.replaced_at is not None

def test_context_card_to_dict():
    card = MockCard("Lightning Bolt", ["R"])
    context_card = ContextCard(base_card=card)
    context_card.add_reason("Test reason")
    context_card.add_source("test_source")
    context_card.score = 5
    data = context_card.to_dict()
    assert data["name"] == "Lightning Bolt"
    assert data["quantity"] == 1
    assert any("Test reason" in r for r in data["reasons"])
    assert "test_source" in data["sources"]
    assert data["score"] == 5

# --- DeckBuildContext tests using real config ---
def test_add_card(context):
    card = MockCard("Primeval Titan", ["G"])  # Use a card from the config
    success = context.add_card(card, "Test reason", "test_source", 4)
    assert success
    assert context.get_total_cards() == 4
    # Test duplicate handling
    success = context.add_card(card, "Another reason", "test_source", 2)
    assert success
    assert context.get_card_quantity("Primeval Titan") == 4

def test_replace_card(context):
    card1 = MockCard("Urza's Saga", ["C"])  # Use a card from the config
    card2 = MockCard("Amulet of Vigor", ["C"])  # Use a card from the config
    context.add_card(card1, "Initial", "test_source", 4)
    success = context.replace_card("Urza's Saga", card2, "Better option")
    assert success
    assert len(context.get_replaced_cards()) == 1
    assert len(context.get_active_cards()) == 1

def test_color_counts(context):
    card1 = MockCard("Primeval Titan", ["G"])
    card2 = MockCard("Counterspell", ["U"])
    card3 = MockCard("Opt", ["U"])
    context.add_card(card1, "Green card", "test_source", 4)
    context.add_card(card2, "Blue card", "test_source", 4)
    context.add_card(card3, "Another blue", "test_source", 1)
    color_counts = context.get_color_counts()
    assert color_counts.get("G", 0) == 1
    assert color_counts.get("U", 0) == 2

def test_context_queries(context):
    card1 = MockCard("Primeval Titan", ["G"])
    card2 = MockCard("Counterspell", ["U"])
    card3 = MockCard("Opt", ["U"])
    context.add_card(card1, "Priority ramp", "priority_list", 4)
    context.add_card(card2, "Core counter", "priority_list", 4)
    context.add_card(card3, "Cantrip", "category_fill", 1)
    priority_cards = context.get_cards_by_source("priority_list")
    assert len(priority_cards) == 2
    removal_cards = context.get_cards_by_reason("ramp")
    assert len(removal_cards) == 1

def test_logging_and_conditions(context):
    context.log("Test message")
    context.record_unmet_condition("Test condition")
    assert len(context.logs) == 1
    assert len(context.unmet_conditions) == 1

def test_export_summary(context):
    card = MockCard("Primeval Titan", ["G"])
    context.add_card(card, "Test card", "test_source", 4)
    summary = context.export_summary()
    assert "cards" in summary
    assert "total_cards" in summary
    assert summary["total_cards"] == 4

def test_clear(context):
    card = MockCard("Primeval Titan", ["G"])
    context.add_card(card, "Test", "test_source", 4)
    context.log("Test message")
    context.record_unmet_condition("Test condition")
    context.clear()
    assert len(context.get_active_cards()) == 0
    assert len(context.logs) == 0
    assert len(context.unmet_conditions) == 0 