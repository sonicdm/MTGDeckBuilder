import pytest
from mtg_deck_builder.models.deck import Deck

def test_deck_json_roundtrip():
    # Create a minimal Deck with dummy cards
    class DummyCard:
        def __init__(self, name, owned_qty=1):
            self.name = name
            self.owned_qty = owned_qty
            self.type = "Creature"
            self.colors = ["G"]
            self.mana_cost = "{G}"
            self.rarity = "common"
            self.text = "Test card."
        def matches_type(self, type_string):
            return type_string.lower() in (self.type or '').lower()
        @property
        def converted_mana_cost(self):
            return 1
    cards = {
        'Forest': DummyCard('Forest', owned_qty=10),
        'Llanowar Elves': DummyCard('Llanowar Elves', owned_qty=4),
    }
    deck = Deck(cards=cards, name="Test Deck")
    # Deck to JSON
    if hasattr(deck, 'to_json') and hasattr(deck.__class__, 'from_json'):
        deck_json = deck.to_json()
        deck2 = deck.__class__.from_json(deck_json)
        assert deck.name == deck2.name
        assert deck.cards.keys() == deck2.cards.keys()
        # If Deck has config, check config round-trip
        if hasattr(deck, 'config') and hasattr(deck.config, 'model_dump_json'):
            config_json = deck.config.model_dump_json()
            config2 = deck.config.__class__.model_validate_json(config_json)
            assert deck.config == config2 