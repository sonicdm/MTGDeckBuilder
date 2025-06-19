import pytest
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import date

from mtg_deck_builder.deck_config.deck_config import DeckConfig
from mtg_deck_builder.yaml_builder.yaml_deckbuilder import build_deck_from_config
from mtg_deck_builder.db.repository import CardRepository, InventoryRepository
from mtg_deck_builder.db import get_session
from mtg_deck_builder.db.models import CardDB, CardPrintingDB
from mtg_deck_builder.models.deck import Deck

# Test data
TEST_DECK_CONFIG = {
    'deck': {
        'name': "Test Deck",
        'colors': ["W", "U"],
        'size': 60,
        'max_card_copies': 4,
        'allow_colorless': True,
        'legalities': ["standard"],
        'owned_cards_only': False,
        'mana_curve': {
            'min': 1,
            'max': 5,
            'curve_shape': "bell",
            'curve_slope': "down"
        }
    },
    'priority_cards': [
        {
            'name': "Stadium Headliner",
            'min_copies': 3
        },
        {
            'name': "Twinferno",
            'min_copies': 2
        }
    ],
    'mana_base': {
        'land_count': 24,
        'special_lands': {
            'count': 4,
            'prefer': ["add {w}", "add {u}"]
        },
        'balance': {
            'adjust_by_mana_symbols': True
        }
    },
    'categories': {
        'creatures': {
            'target': 24,
            'preferred_keywords': ["flying", "first strike"],
            'priority_text': ["when this enters", "when this attacks"],
            'preferred_basic_type_priority': ["creature"]
        },
        'removal': {
            'target': 8,
            'priority_text': ["destroy target", "exile target"],
            'preferred_basic_type_priority': ["instant", "sorcery"]
        },
        'card_draw': {
            'target': 3,
            'priority_text': [
                "draw a card",
                "loot",
                "when this dies",
                "discard then draw",
                "impulse"
            ],
            'preferred_basic_type_priority': ["creature", "enchantment", "instant", "sorcery"]
        },
        'buffs': {
            'target': 4,
            'priority_text': ["+x/+0", "until end of turn", "double strike", "rage", "fury"],
            'preferred_basic_type_priority': ["creature", "instant", "sorcery"]
        },
        'utility': {
            'target': 2,
            'priority_text': ["treasure", "scry", "return target creature card"],
            'preferred_basic_type_priority': ["creature", "enchantment", "instant", "sorcery"]
        }
    },
    'card_constraints': {
        'rarity_boost': {
            'common': 1,
            'uncommon': 2,
            'rare': 2,
            'mythic': 1
        },
        'exclude_keywords': ["defender", "lifelink", "hexproof", "vehicle", "mount"]
    },
    'scoring_rules': {
        'keyword_abilities': {
            'flying': 2,
            'first strike': 2
        },
        'keyword_actions': {
            'scry': 1,
            'fight': 2,
            'exile': 3,
            'create': 2,
            'sacrifice': 2
        },
        'ability_words': {
            'raid': 2,
            'landfall': 1
        },
        'text_matches': {
            "when this enters": 2,
            "when this attacks": 2
        },
        'type_bonus': {
            'basic_types': {
                'creature': 2,
                'instant': 1,
                'sorcery': 1
            },
            'sub_types': {
                'warrior': 3,
                'cleric': 1
            },
            'super_types': {
                'legendary': 1
            }
        },
        'rarity_bonus': {
            'rare': 2,
            'mythic': 1
        },
        'mana_penalty': {
            'threshold': 5,
            'penalty_per_point': 1
        },
        'min_score_to_flag': 6
    },
    'fallback_strategy': {
        'fill_with_any': True,
        'fill_priority': ["removal", "creatures"],
        'allow_less_than_target': True
    }
}

def card_to_dict(card: CardDB) -> Dict[str, Any]:
    """Convert a CardDB instance to a serializable dictionary."""
    newest_printing = card.newest_printing
    return {
        'card_name': card.card_name,  # Primary key
        'name': card.name,
        'type': card.type,
        'types': card.types,
        'basic_type': card.basic_type,
        'subtypes': card.subtypes,
        'subtype': card.subtype,
        'supertypes': card.supertypes,
        'supertype': card.supertype,
        'mana_cost': card.mana_cost,
        'colors': card.colors,
        'color_identity': card.color_identity,
        'rarity': card.rarity,
        'power': card.power,
        'toughness': card.toughness,
        'text': card.text,
        'abilities': card.get_abilities(),
        'converted_mana_cost': card.converted_mana_cost,
        'legalities': card.legalities,
        'rulings': card.rulings,
        'foreign_data': card.foreign_data,
        'owned_qty': card.owned_qty,
        'newest_printing_uid': card.newest_printing_uid,
        'release_date': card.release_date.isoformat() if card.release_date else None
    }

def dict_to_card(card_dict: Dict[str, Any], session) -> CardDB:
    """Convert a dictionary back to a CardDB instance."""
    card = CardDB()
    card.card_name = card_dict['card_name']
    card.name = card_dict['name']
    
    # Set newest printing if available
    if card_dict.get('newest_printing_uid'):
        card.newest_printing_uid = card_dict['newest_printing_uid']
        card.newest_printing_rel = session.query(CardPrintingDB).get(card_dict['newest_printing_uid'])
    
    # Set owned quantity
    if 'owned_qty' in card_dict:
        card._owned_qty = card_dict['owned_qty']
    
    return card

@pytest.fixture
def deck_config() -> DeckConfig:
    """Create a complete deck configuration for testing using cobra-kai2.yaml fields."""
    complete_config = {
        "deck": {
            "name": "Cobra Kai: No Mercy",
            "colors": ["B", "R"],
            "color_match_mode": "subset",
            "size": 60,
            "max_card_copies": 4,
            "allow_colorless": True,
            "legalities": ["alchemy"],
            "owned_cards_only": False,
            "mana_curve": {
                "min": 1,
                "max": 5,
                "curve_shape": "bell",
                "curve_slope": "down"
            }
        },
        "priority_cards": [
            {"name": "Stadium Headliner", "min_copies": 3},
            {"name": "Twinferno", "min_copies": 2}
        ],
        "mana_base": {
            "land_count": 24,
            "special_lands": {
                "count": 6,
                "prefer": ["add {r}", "add {b}", "deals damage"],
                "avoid": ["vehicle", "mount"]
            },
            "balance": {
                "adjust_by_mana_symbols": True
            }
        },
        "categories": {
            "creatures": {
                "target": 26,
                "preferred_keywords": ["haste", "menace", "first strike", "double strike"],
                "priority_text": ["when this creature attacks", "sacrifice a creature", "/strike/"],
                "preferred_basic_type_priority": ["creature", "planeswalker"]
            },
            "removal": {
                "target": 6,
                "priority_text": [
                    "damage", "destroy", "/-x/-x/", "sacrifice another creature", "each creature",
                    "when this enters", "instant speed", "target creature gets -x/-x",
                    "destroy target creature", "exile target creature"
                ],
                "preferred_basic_type_priority": ["instant", "creature", "sorcery"]
            },
            "card_draw": {
                "target": 3,
                "priority_text": [
                    "draw a card", "loot", "when this dies", "discard then draw", "impulse"
                ],
                "preferred_basic_type_priority": ["creature", "enchantment", "instant", "sorcery"]
            },
            "buffs": {
                "target": 4,
                "priority_text": ["+x/+0", "until end of turn", "double strike", "rage", "fury"],
                "preferred_basic_type_priority": ["creature", "instant", "sorcery"]
            },
            "utility": {
                "target": 2,
                "priority_text": ["treasure", "scry", "return target creature card"],
                "preferred_basic_type_priority": ["creature", "enchantment", "instant", "sorcery"]
            }
        },
        "card_constraints": {
            "rarity_boost": {
                "common": 1,
                "uncommon": 2,
                "rare": 2,
                "mythic": 1
            },
            "exclude_keywords": ["defender", "lifelink", "hexproof", "vehicle", "mount"]
        },
        "scoring_rules": {
            "keyword_abilities": {
                "haste": 2,
                "menace": 2,
                "double strike": 3,
                "deathtouch": 1,
                "flying": 1,
                "hexproof": -5
            },
            "keyword_actions": {
                "scry": 1,
                "fight": 2,
                "exile": 3,
                "create": 2,
                "sacrifice": 2
            },
            "ability_words": {
                "raid": 2,
                "landfall": 1
            },
            "text_matches": {
                "mobilize": 4,
                "create a 1/1": 3,
                "when this creature attacks": 2,
                "/warrior/": 2,
                "sacrifice a creature": 2,
                "when a creature dies": 2,
                "return target creature": 2,
                "/creature.*dies/": 2,
                "+x/+0": 2,
                "double strike": 2,
                "damage": 3,
                "draw a card": 3,
                "impulse": 2,
                "discard then draw": 2,
                "destroy target creature": 4,
                "exile target creature": 3,
                "enters tapped unless": -1
            },
            "type_bonus": {
                "basic_types": {
                    "creature": 2,
                    "instant": 1,
                    "sorcery": 1
                },
                "sub_types": {
                    "warrior": 3,
                    "cleric": 1
                },
                "super_types": {
                    "legendary": 1
                }
            },
            "rarity_bonus": {
                "rare": 2,
                "mythic": 1
            },
            "mana_penalty": {
                "threshold": 5,
                "penalty_per_point": 1
            },
            "min_score_to_flag": 6
        },
        "fallback_strategy": {
            "fill_with_any": True,
            "fill_priority": ["removal", "card_draw", "buffs"],
            "allow_less_than_target": True
        }
    }
    return DeckConfig.model_validate(complete_config)

@pytest.fixture
def deck(deck_config: DeckConfig) -> Deck:
    """Create a test deck with the given configuration."""
    with get_session() as session:
        card_repo = CardRepository(session)
        deck = build_deck_from_config(deck_config, card_repo, None)
        if not deck:
            raise RuntimeError("Deck could not be built from config; no fallback empty deck should be created.")
        # Ensure all cards are bound to the session
        for card in deck.cards.values():
            session.add(card)
            if card.newest_printing_rel:
                session.add(card.newest_printing_rel)
        session.flush()
        return deck

def test_card_serialization(deck: Deck) -> None:
    """Test that a card can be serialized and deserialized."""
    with get_session() as session:
        # Get a card from the deck
        test_card = next(iter(deck.cards.values()))
        # Serialize
        card_dict = test_card.to_dict(eager=True)
        # Deserialize
        new_card = CardDB.from_dict(card_dict, session)
        # Verify key attributes are preserved
        assert new_card.name == test_card.name
        assert new_card.type == test_card.type
        assert new_card.colors == test_card.colors
        assert new_card.rarity == test_card.rarity

def test_deck_serialization(deck: Deck) -> None:
    """Test that a deck can be serialized to JSON."""
    with get_session() as session:
        deck.session = session
        # Convert deck to dictionary
        deck_dict = deck.to_dict(eager=True)
        # Verify basic structure
        assert 'name' in deck_dict
        assert 'cards' in deck_dict
        assert 'config' in deck_dict
        # Verify content
        assert deck_dict['name'] == deck.name
        assert len(deck_dict['cards']) == len(deck.cards)
        if deck.config:
            assert deck_dict['config'] == deck.config.model_dump()

def test_deck_deserialization(deck: Deck) -> None:
    """Test that a deck can be deserialized from JSON."""
    with get_session() as session:
        deck.session = session
        # First serialize
        deck_dict = deck.to_dict(eager=True)
        # Then deserialize
        new_deck = Deck.from_dict(deck_dict, session)
        # Verify key attributes are preserved
        assert new_deck.name == deck.name
        assert len(new_deck.cards) == len(deck.cards)
        if deck.config:
            assert new_deck.config.model_dump() == deck.config.model_dump()

def test_deck_roundtrip(deck: Deck) -> None:
    """Test that a deck can be serialized and deserialized without data loss."""
    with get_session() as session:
        deck.session = session
        # Serialize
        deck_dict = deck.to_dict(eager=True)
        # Deserialize
        new_deck = Deck.from_dict(deck_dict, session)
        # Serialize again
        new_deck_dict = new_deck.to_dict(eager=True)
        # Compare the two dictionaries
        assert deck_dict == new_deck_dict

def test_deck_config_preservation(deck: Deck) -> None:
    """Test that deck configuration is preserved during serialization."""
    with get_session() as session:
        deck.session = session
        # Serialize
        deck_dict = deck.to_dict(eager=True)
        # Deserialize
        new_deck = Deck.from_dict(deck_dict, session)
        # Verify config is preserved
        if deck.config:
            assert new_deck.config.model_dump() == deck.config.model_dump()
        else:
            assert new_deck.config is None

def test_minimal_deck_config() -> None:
    """Test that a complete deck configuration can be created and serialized."""
    complete_config = {
        "deck": {
            "name": "Cobra Kai: No Mercy",
            "colors": ["B", "R"],
            "color_match_mode": "subset",
            "size": 60,
            "max_card_copies": 4,
            "allow_colorless": True,
            "legalities": ["alchemy"],
            "owned_cards_only": False,
            "mana_curve": {
                "min": 1,
                "max": 5,
                "curve_shape": "bell",
                "curve_slope": "down"
            }
        },
        "priority_cards": [
            {"name": "Stadium Headliner", "min_copies": 3},
            {"name": "Twinferno", "min_copies": 2}
        ],
        "mana_base": {
            "land_count": 24,
            "special_lands": {
                "count": 6,
                "prefer": ["add {r}", "add {b}", "deals damage"],
                "avoid": ["vehicle", "mount"]
            },
            "balance": {
                "adjust_by_mana_symbols": True
            }
        },
        "categories": {
            "creatures": {
                "target": 26,
                "preferred_keywords": ["haste", "menace", "first strike", "double strike"],
                "priority_text": ["when this creature attacks", "sacrifice a creature", "/strike/"],
                "preferred_basic_type_priority": ["creature", "planeswalker"]
            },
            "removal": {
                "target": 6,
                "priority_text": [
                    "damage", "destroy", "/-x/-x/", "sacrifice another creature", "each creature",
                    "when this enters", "instant speed", "target creature gets -x/-x",
                    "destroy target creature", "exile target creature"
                ],
                "preferred_basic_type_priority": ["instant", "creature", "sorcery"]
            },
            "card_draw": {
                "target": 3,
                "priority_text": [
                    "draw a card", "loot", "when this dies", "discard then draw", "impulse"
                ],
                "preferred_basic_type_priority": ["creature", "enchantment", "instant", "sorcery"]
            },
            "buffs": {
                "target": 4,
                "priority_text": ["+x/+0", "until end of turn", "double strike", "rage", "fury"],
                "preferred_basic_type_priority": ["creature", "instant", "sorcery"]
            },
            "utility": {
                "target": 2,
                "priority_text": ["treasure", "scry", "return target creature card"],
                "preferred_basic_type_priority": ["creature", "enchantment", "instant", "sorcery"]
            }
        },
        "card_constraints": {
            "rarity_boost": {
                "common": 1,
                "uncommon": 2,
                "rare": 2,
                "mythic": 1
            },
            "exclude_keywords": ["defender", "lifelink", "hexproof", "vehicle", "mount"]
        },
        "scoring_rules": {
            "keyword_abilities": {
                "haste": 2,
                "menace": 2,
                "double strike": 3,
                "deathtouch": 1,
                "flying": 1,
                "hexproof": -5
            },
            "keyword_actions": {
                "scry": 1,
                "fight": 2,
                "exile": 3,
                "create": 2,
                "sacrifice": 2
            },
            "ability_words": {
                "raid": 2,
                "landfall": 1
            },
            "text_matches": {
                "mobilize": 4,
                "create a 1/1": 3,
                "when this creature attacks": 2,
                "/warrior/": 2,
                "sacrifice a creature": 2,
                "when a creature dies": 2,
                "return target creature": 2,
                "/creature.*dies/": 2,
                "+x/+0": 2,
                "double strike": 2,
                "damage": 3,
                "draw a card": 3,
                "impulse": 2,
                "discard then draw": 2,
                "destroy target creature": 4,
                "exile target creature": 3,
                "enters tapped unless": -1
            },
            "type_bonus": {
                "basic_types": {
                    "creature": 2,
                    "instant": 1,
                    "sorcery": 1
                },
                "sub_types": {
                    "warrior": 3,
                    "cleric": 1
                },
                "super_types": {
                    "legendary": 1
                }
            },
            "rarity_bonus": {
                "rare": 2,
                "mythic": 1
            },
            "mana_penalty": {
                "threshold": 5,
                "penalty_per_point": 1
            },
            "min_score_to_flag": 6
        },
        "fallback_strategy": {
            "fill_with_any": True,
            "fill_priority": ["removal", "card_draw", "buffs"],
            "allow_less_than_target": True
        }
    }
    # Create and validate config
    config = DeckConfig.model_validate(complete_config)
    # Create minimal deck with a dummy card
    with get_session() as session:
        # Create a dummy CardDB
        dummy_card = CardDB()
        dummy_card.card_name = config.deck.name
        dummy_card.name = config.deck.name
        dummy_card._owned_qty = 1
        # Create a dummy CardPrintingDB for the newest printing
        dummy_printing = CardPrintingDB()
        dummy_printing.card_type = "Creature"
        dummy_printing.colors = config.deck.colors
        dummy_printing.rarity = "common"
        dummy_printing.uid = "dummy_uid"
        dummy_printing.card_name = dummy_card.card_name
        dummy_printing.set_code = "dummy_set"
        # Set the newest printing relationship
        dummy_card.newest_printing_rel = dummy_printing
        # Create the deck with the dummy card
        deck = Deck(cards={dummy_card.name: dummy_card}, session=session, name=config.deck.name)
        deck.config = config
        # Serialize and verify
        deck_dict = deck.to_dict(eager=False)
        assert deck_dict['name'] == "Cobra Kai: No Mercy"
        assert deck_dict['config'] == config.model_dump() 