import pytest
from mtg_deck_builder.models.deck import Deck
from types import SimpleNamespace

class DummyCard:
    def __init__(self, name, colors=None, power=None, toughness=None, cmc=None, types=None):
        self.name = name
        self.colors = colors or []
        self.power = power
        self.toughness = toughness
        self.converted_mana_cost = cmc
        self.owned_qty = 1
        self._types = types or []
    def matches_type(self, t):
        return t.lower() in (x.lower() for x in self._types)

class DummyRepo:
    def __init__(self, cards):
        self._cards = cards
        self.session = None
    def get_all_cards(self):
        return self._cards

@pytest.fixture
def basic_deck():
    c1 = DummyCard("Bolt", colors=["R"], cmc=1, types=["Instant"])
    c2 = DummyCard("Bear", colors=["G"], power="2", toughness="2", cmc=2, types=["Creature"])
    c3 = DummyCard("Angel", colors=["W"], power="4", toughness="4", cmc=5, types=["Creature"])
    return Deck(cards={c.name: c for c in [c1, c2, c3]}, name="Test Deck")

def test_insert_card(basic_deck):
    c = DummyCard("Bear", colors=["G"], power="2", toughness="2", cmc=2, types=["Creature"])
    basic_deck.insert_card(c)
    assert basic_deck._cards["Bear"].owned_qty == 2
    new_card = DummyCard("Elf", colors=["G"], power="1", toughness="1", cmc=1, types=["Creature"])
    basic_deck.insert_card(new_card)
    assert basic_deck._cards["Elf"].owned_qty == 1

def test_sample_hand(basic_deck):
    hand = basic_deck.sample_hand(3)
    assert len(hand) == 3
    with pytest.raises(ValueError):
        basic_deck.sample_hand(20)

def test_average_mana_value(basic_deck):
    assert abs(basic_deck.average_mana_value() - (1+2+5)/3) < 0.01

def test_average_power_toughness(basic_deck):
    avg_pow, avg_tough = basic_deck.average_power_toughness()
    assert abs(avg_pow - 3.0) < 0.01
    assert abs(avg_tough - 3.0) < 0.01

def test_deck_color_identity(basic_deck):
    colors = basic_deck.deck_color_identity()
    assert colors == {"R", "G", "W"}

def test_from_repo():
    cards = [DummyCard("A"), DummyCard("B"), DummyCard("C")]
    repo = DummyRepo(cards)
    deck = Deck.from_repo(repo, limit=2, random_cards=False)
    assert len(deck._cards) == 2
    assert all(card.owned_qty == 1 for card in deck._cards.values())
    with pytest.raises(ValueError):
        Deck.from_repo(DummyRepo([]))

