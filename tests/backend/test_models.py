"""
Test card models and related components.

These tests validate:
- Card model creation and properties
- Printing model relationships
- Deck model operations
- Deck analyzer functionality
"""

import pytest
from unittest.mock import MagicMock
from typing import Dict, Any, cast, List

from mtg_deck_builder.models.deck import Deck


@pytest.fixture
def sample_deck_data():
    """Sample deck data for testing."""
    return {
        "name": "Test Deck",
        "cards": {},
        "session": None
    }


class TestDeck:
    """Test Deck model."""

    def test_deck_creation(self, sample_deck_data):
        """Test creating a deck instance."""
        deck = Deck(**sample_deck_data)
        
        assert deck.name == "Test Deck"
        assert deck.cards == {}
        assert deck.inventory == {}
        assert deck.session is None

    def test_deck_default_values(self):
        """Test deck with default values."""
        deck = Deck(name="Test Deck")
        
        assert deck.name == "Test Deck"
        assert deck.cards == {}
        assert deck.inventory == {}
        assert deck.session is None

    def test_deck_with_cards_dict(self):
        """Test deck creation with cards dictionary."""
        from mtg_deck_builder.db.mtgjson_models.cards import MTGJSONSummaryCard
        
        mock_card1 = MagicMock(spec=MTGJSONSummaryCard)
        mock_card1.name = "Lightning Bolt"
        mock_card2 = MagicMock(spec=MTGJSONSummaryCard)
        mock_card2.name = "Serra Angel"
        
        cards_dict = cast(Dict[str, MTGJSONSummaryCard], {
            "Lightning Bolt": mock_card1,
            "Serra Angel": mock_card2
        })
        
        deck = Deck(cards=cards_dict, name="Test Deck")
        
        assert deck.name == "Test Deck"
        assert len(deck.cards) == 2
        assert "Lightning Bolt" in deck.cards
        assert "Serra Angel" in deck.cards
        assert deck.inventory["Lightning Bolt"] == 1
        assert deck.inventory["Serra Angel"] == 1

    def test_deck_with_cards_list(self):
        """Test deck creation with cards list."""
        from mtg_deck_builder.db.mtgjson_models.cards import MTGJSONSummaryCard
        
        mock_card1 = MagicMock(spec=MTGJSONSummaryCard)
        mock_card1.name = "Lightning Bolt"
        mock_card2 = MagicMock(spec=MTGJSONSummaryCard)
        mock_card2.name = "Serra Angel"
        
        cards_list = cast(List[MTGJSONSummaryCard], [mock_card1, mock_card2])
        
        deck = Deck(cards=cards_list, name="Test Deck")
        
        assert deck.name == "Test Deck"
        assert len(deck.cards) == 2
        assert "Lightning Bolt" in deck.cards
        assert "Serra Angel" in deck.cards
        assert deck.inventory["Lightning Bolt"] == 1
        assert deck.inventory["Serra Angel"] == 1

    def test_deck_card_operations(self):
        """Test deck card operations."""
        deck = Deck(name="Test Deck")
        card = MagicMock()
        card.name = "Test Card"
        
        # Test adding cards
        deck.insert_card(card, 2)
        assert len(deck.cards) == 1
        assert "Test Card" in deck.cards
        assert deck.inventory["Test Card"] == 2
        
        # Test adding more of the same card
        deck.insert_card(card, 1)
        assert deck.inventory["Test Card"] == 3

    def test_deck_card_counting(self):
        """Test deck card counting."""
        deck = Deck(name="Test Deck")
        card1 = MagicMock()
        card1.name = "Card 1"
        card2 = MagicMock()
        card2.name = "Card 2"
        
        deck.insert_card(card1, 3)
        deck.insert_card(card2, 2)
        
        assert deck.get_quantity("Card 1") == 3
        assert deck.get_quantity("Card 2") == 2
        assert deck.get_quantity("Card 3") == 0
        assert deck.size() == 5

    def test_deck_size(self):
        """Test deck size calculation."""
        deck = Deck(name="Test Deck")
        card1 = MagicMock()
        card1.name = "Card 1"
        card2 = MagicMock()
        card2.name = "Card 2"
        
        deck.insert_card(card1, 3)
        deck.insert_card(card2, 2)
        
        assert deck.size() == 5

    def test_deck_cards_by_type(self):
        """Test filtering cards by type."""
        deck = Deck(name="Test Deck")
        
        # Create mock cards with types
        creature = MagicMock()
        creature.name = "Creature"
        creature.types = ["Creature"]
        
        instant = MagicMock()
        instant.name = "Instant"
        instant.types = ["Instant"]
        
        deck.insert_card(creature, 1)
        deck.insert_card(instant, 1)
        
        creatures = deck.cards_by_type("Creature")
        assert len(creatures) == 1
        assert creatures[0].name == "Creature"
        
        instants = deck.cards_by_type("Instant")
        assert len(instants) == 1
        assert instants[0].name == "Instant"

    def test_deck_search_cards(self):
        """Test searching cards by text."""
        deck = Deck(name="Test Deck")
        
        # Create mock cards with names and text
        bolt = MagicMock()
        bolt.name = "Lightning Bolt"
        bolt.oracle_text = "Deal 3 damage to any target"
        
        angel = MagicMock()
        angel.name = "Serra Angel"
        angel.oracle_text = "Flying"
        
        deck.insert_card(bolt, 1)
        deck.insert_card(angel, 1)
        
        # Search by name
        results = deck.search_cards("Lightning")
        assert len(results) == 1
        assert results[0].name == "Lightning Bolt"
        
        # Search by text
        results = deck.search_cards("damage")
        assert len(results) == 1
        assert results[0].name == "Lightning Bolt"

    def test_deck_sample_hand(self):
        """Test drawing a sample hand."""
        deck = Deck(name="Test Deck")
        
        card1 = MagicMock()
        card1.name = "Card 1"
        card2 = MagicMock()
        card2.name = "Card 2"
        card3 = MagicMock()
        card3.name = "Card 3"
        
        deck.insert_card(card1, 2)
        deck.insert_card(card2, 2)
        deck.insert_card(card3, 2)
        
        hand = deck.sample_hand(3)
        assert len(hand) == 3
        
        # Test that hand size can't exceed deck size
        with pytest.raises(ValueError):
            deck.sample_hand(10)

    def test_deck_to_dict(self):
        """Test converting deck to dictionary."""
        deck = Deck(name="Test Deck")
        
        card1 = MagicMock()
        card1.name = "Card 1"
        card2 = MagicMock()
        card2.name = "Card 2"
        
        deck.insert_card(card1, 2)
        deck.insert_card(card2, 1)
        
        deck_dict = deck.to_dict()
        
        assert deck_dict["name"] == "Test Deck"
        assert "cards" in deck_dict
        assert "Card 1" in deck_dict["cards"]
        assert "Card 2" in deck_dict["cards"]
        assert deck_dict["cards"]["Card 1"]["quantity"] == 2
        assert deck_dict["cards"]["Card 2"]["quantity"] == 1

    def test_deck_repr(self):
        """Test deck string representation."""
        deck = Deck(name="Test Deck")
        card = MagicMock()
        card.name = "Test Card"
        deck.insert_card(card, 2)
        
        repr_str = repr(deck)
        assert "Test Deck" in repr_str
        assert "1" in repr_str  # unique cards
        assert "2" in repr_str  # total cards


class TestCardMeta:
    """Test card metadata utilities."""

    def test_card_types_data_creation(self):
        """Test creating CardTypesData."""
        from mtg_deck_builder.models.card_meta import CardTypesData, TypeEntry
        
        creature_entry = TypeEntry(subTypes=["Human", "Warrior"], superTypes=["Legendary"])
        instant_entry = TypeEntry(subTypes=[], superTypes=[])
        
        card_types = CardTypesData(
            data={
                "creature": creature_entry,
                "instant": instant_entry
            }
        )
        
        assert "creature" in card_types.data
        assert "instant" in card_types.data
        assert card_types.data["creature"].subTypes == ["Human", "Warrior"]
        assert card_types.data["creature"].superTypes == ["Legendary"]

    def test_card_types_data_methods(self):
        """Test CardTypesData utility methods."""
        from mtg_deck_builder.models.card_meta import CardTypesData, TypeEntry
        
        creature_entry = TypeEntry(subTypes=["Human", "Warrior"], superTypes=["Legendary"])
        instant_entry = TypeEntry(subTypes=[], superTypes=[])
        
        card_types = CardTypesData(
            data={
                "creature": creature_entry,
                "instant": instant_entry
            }
        )
        
        # Test get_subtypes
        assert card_types.get_subtypes("creature") == ["Human", "Warrior"]
        assert card_types.get_subtypes("instant") == []
        assert card_types.get_subtypes("nonexistent") == []
        
        # Test get_supertypes
        assert card_types.get_supertypes("creature") == ["Legendary"]
        assert card_types.get_supertypes("instant") == []
        
        # Test all_types
        all_types = card_types.all_types()
        assert "creature" in all_types
        assert "instant" in all_types
        assert len(all_types) == 2

    def test_keywords_data_creation(self):
        """Test creating KeywordsData."""
        from mtg_deck_builder.models.card_meta import KeywordsData
        
        keywords = KeywordsData(
            data={
                "keywordAbilities": ["Flying", "Deathtouch"],
                "keywordActions": ["Scry"],
                "abilityWords": ["Battalion"]
            }
        )
        
        assert "keywordAbilities" in keywords.data
        assert "keywordActions" in keywords.data
        assert "abilityWords" in keywords.data
        assert "Flying" in keywords.data["keywordAbilities"]
        assert "Deathtouch" in keywords.data["keywordAbilities"]

    def test_keywords_data_methods(self):
        """Test KeywordsData utility methods."""
        from mtg_deck_builder.models.card_meta import KeywordsData
        
        keywords = KeywordsData(
            data={
                "keywordAbilities": ["Flying", "Deathtouch"],
                "keywordActions": ["Scry"],
                "abilityWords": ["Battalion"]
            }
        )
        
        # Test get methods
        assert keywords.get_keyword_abilities() == ["Flying", "Deathtouch"]
        assert keywords.get_keyword_actions() == ["Scry"]
        assert keywords.get_ability_words() == ["Battalion"]
        
        # Test is methods
        assert keywords.is_keyword_ability("Flying") is True
        assert keywords.is_keyword_ability("Scry") is False
        assert keywords.is_keyword_action("Scry") is True
        assert keywords.is_keyword_action("Flying") is False
        assert keywords.is_ability_word("Battalion") is True
        assert keywords.is_ability_word("Flying") is False 