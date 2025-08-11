# This file contains pytest fixtures and dummy classes for testing.

import os
import tempfile
import pytest
from pathlib import Path

class DummyCard:
    def __init__(self, name, colors=None, owned_qty=1, rarity=None, legalities=None, text=None, converted_mana_cost=0, type=None, power=None, toughness=None):
        self.name = name
        self.colors = colors or []
        self.owned_qty = owned_qty
        self.rarity = rarity or "common"
        self.legalities = legalities or {}
        self.text = text or ""
        self.converted_mana_cost = converted_mana_cost
        self.type = type or "Creature"
        self.power = power
        self.toughness = toughness
        
    def matches_color_identity(self, allowed, mode):
        return set(self.colors) <= set(allowed)
        
    def matches_type(self, type_str):
        return type_str.lower() in self.type.lower()
        
    def is_basic_land(self):
        return self.type.lower() == "basic land"
        
    def __repr__(self):
        return f"DummyCard({self.name}, CMC={self.converted_mana_cost}, Type={self.type})"

class DummyRepo:
    def __init__(self, cards):
        self._cards = cards
        self.session = None
    def get_all_cards(self):
        return self._cards
    def find_by_name(self, name):
        for c in self._cards:
            if c.name == name:
                return c
        return None
    def filter_cards(self, color_identity=None, color_mode=None, legal_in=None):
        # For test purposes, just return self (no filtering)
        return self
    def __iter__(self):
        return iter(self._cards)

class DummyInventoryRepo:
    def __init__(self):
        pass

# Card model fixtures
@pytest.fixture
def sample_printing_data():
    """Sample printing data for testing."""
    return {
        "uuid": "test-uuid-123",
        "name": "Lightning Bolt",
        "setCode": "LEA",
        "artist": "Christopher Rush",
        "artistIds": [],
        "attractionLights": [],
        "availability": [],
        "boosterTypes": [],
        "borderColor": "black",
        "cardParts": [],
        "colorIdentity": [],
        "colorIndicator": [],
        "colors": ["R"],
        "defense": None,
        "duelDeck": None,
        "edhrecRank": None,
        "edhrecSaltiness": None,
        "faceConvertedManaCost": None,
        "faceFlavorName": None,
        "faceManaValue": None,
        "faceName": None,
        "finishes": [],
        "flavorName": None,
        "flavorText": "The sparkmage shrieked, calling on the rage of the storms...",
        "frameEffects": [],
        "frameVersion": "2015",
        "hand": None,
        "hasAlternativeDeckLimit": None,
        "hasContentWarning": None,
        "hasFoil": None,
        "hasNonFoil": None,
        "isAlternative": None,
        "isFullArt": None,
        "isFunny": None,
        "isGameChanger": None,
        "isOnlineOnly": None,
        "isOversized": None,
        "isPromo": None,
        "isRebalanced": None,
        "isReprint": None,
        "isReserved": None,
        "isStarter": None,
        "isStorySpotlight": None,
        "isTextless": None,
        "isTimeshifted": None,
        "keywords": ["damage"],
        "language": "English",
        "layout": "normal",
        "leadershipSkills": {},
        "life": None,
        "loyalty": None,
        "manaCost": "{R}",
        "manaValue": 1.0,
        "number": "74",
        "originalPrintings": [],
        "originalReleaseDate": None,
        "originalText": None,
        "originalType": None,
        "otherFaceIds": [],
        "power": None,
        "printings": [],
        "promoTypes": [],
        "rarity": "Common",
        "rebalancedPrintings": [],
        "relatedCards": [],
        "securityStamp": None,
        "side": None,
        "signature": None,
        "sourceProducts": [],
        "subsets": [],
        "supertypes": [],
        "subtypes": [],
        "text": "Lightning Bolt deals 3 damage to any target.",
        "toughness": None,
        "type": "Instant",
        "types": ["Instant"],
        "variations": [],
        "watermark": None
    }

@pytest.fixture
def sample_summary_card_data():
    """Sample summary card data for testing."""
    return {
        "name": "Lightning Bolt",
        "set_code": "LEA",
        "rarity": "Common",
        "type": "Instant",
        "mana_cost": "{R}",
        "converted_mana_cost": 1.0,
        "power": "",
        "toughness": "",
        "loyalty": "",
        "text": "Lightning Bolt deals 3 damage to any target.",
        "flavor_text": "The sparkmage shrieked, calling on the rage of the storms...",
        "artist": "Christopher Rush",
        "printing_set_codes": ["LEA", "LEB", "2ED"],
        "color_identity": ["R"],
        "colors": ["R"],
        "types": ["Instant"],
        "supertypes": [],
        "subtypes": [],
        "keywords": ["damage"],
        "legalities": {"standard": "legal", "modern": "legal"}
    }

@pytest.fixture
def sample_inventory_item_data():
    """Sample inventory item data for testing."""
    return {
        "name": "Lightning Bolt",
        "quantity": 4
    }
