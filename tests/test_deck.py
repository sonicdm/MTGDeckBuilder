"""
Unit tests for mtg_deck_builder.models.deck
"""
import pytest
from mtg_deck_builder.models.deck import Deck

class DummyCard:
    # Dummy class to simulate a card with the needed attributes for Deck
    def __init__(self, name, mana_cost=None, rarity=None, colors=None, type_line=None, power=None, toughness=None, owned_qty=1):
        self.name = name
        self.mana_cost = mana_cost
        self.rarity = rarity
        self.colors = colors or []
        self.type = type_line
        self.power = power
        self.toughness = toughness
        self.owned_qty = owned_qty
        self.text = "Add {G}. Search your library for a land."
    def matches_type(self, type_string):
        return type_string.lower() in (self.type or '').lower()
    @property
    def converted_mana_cost(self):
        if not self.mana_cost:
            return 0
        import re
        total = 0
        for symbol in re.findall(r'\{([^}]+)\}', self.mana_cost):
            if symbol.isdigit():
                total += int(symbol)
            else:
                total += 1
        return total

@pytest.fixture
def sample_deck():
    cards = {
        'Forest': DummyCard('Forest', mana_cost=None, rarity='common', colors=[], type_line='Basic Land', owned_qty=10),
        'Llanowar Elves': DummyCard('Llanowar Elves', mana_cost='{G}', rarity='common', colors=['G'], type_line='Creature', power='1', toughness='1', owned_qty=4),
        'Rampant Growth': DummyCard('Rampant Growth', mana_cost='{1}{G}', rarity='common', colors=['G'], type_line='Sorcery', owned_qty=2),
        'Giant Growth': DummyCard('Giant Growth', mana_cost='{G}', rarity='common', colors=['G'], type_line='Instant', owned_qty=2),
    }
    return Deck(cards=cards)

def test_deck_size(sample_deck):
    assert sample_deck.size() == 18

def test_deck_color_identity(sample_deck):
    assert sample_deck.deck_color_identity() == {'G'}

def test_deck_average_mana_value(sample_deck):
    assert sample_deck.average_mana_value() > 0

def test_deck_average_power_toughness(sample_deck):
    avg_power, avg_toughness = sample_deck.average_power_toughness()
    assert avg_power > 0
    assert avg_toughness > 0

def test_deck_count_card_types(sample_deck):
    type_counts = sample_deck.count_card_types()
    assert type_counts['Land'] == 10
    assert type_counts['Creature'] == 4
    assert type_counts['Instant'] == 2
    assert type_counts['Sorcery'] == 2

def test_deck_count_mana_ramp(sample_deck):
    assert sample_deck.count_mana_ramp() >= 1

def test_deck_sample_hand(sample_deck):
    hand = sample_deck.sample_hand(7)
    assert len(hand) == 7
    assert all(hasattr(card, 'name') for card in hand)

def test_deck_mtg_arena_import(sample_deck):
    arena_str = sample_deck.mtg_arena_import()
    assert 'Forest' in arena_str
    assert 'Llanowar Elves' in arena_str

