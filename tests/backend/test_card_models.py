"""
Test card models.

These tests validate:
- Card model creation and validation
- Card relationships and properties
- Card filtering and matching methods
"""

import pytest
from unittest.mock import MagicMock
from mtg_deck_builder.models.card import Printing, SummaryCard, InventoryItem

# Import fixtures from shared fixtures file
pytest_plugins = ["tests.fixtures"]


class TestPrinting:
    """Test Printing model."""

    def test_printing_creation(self, sample_printing_data):
        """Test creating Printing instance."""
        printing = Printing(**sample_printing_data)
        
        assert printing.name == "Lightning Bolt"
        assert printing.setCode == "LEA"
        assert printing.manaCost == "{R}"
        assert printing.manaValue == 1.0
        assert printing.colors == ["R"]
        assert printing.type == "Instant"
        assert printing.text == "Lightning Bolt deals 3 damage to any target."
        assert printing.rarity == "Common"
        assert printing.keywords == ["damage"]

    def test_printing_defaults(self):
        """Test Printing with minimal data."""
        minimal_data = {
            "uuid": "test-uuid",
            "name": "Test Card",
            "setCode": "TEST",
            "artist": None,
            "artistIds": [],
            "attractionLights": [],
            "availability": [],
            "boosterTypes": [],
            "borderColor": None,
            "cardParts": [],
            "colorIdentity": [],
            "colorIndicator": [],
            "colors": [],
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
            "flavorText": None,
            "frameEffects": [],
            "frameVersion": None,
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
            "keywords": [],
            "language": None,
            "layout": None,
            "leadershipSkills": {},
            "life": None,
            "loyalty": None,
            "manaCost": None,
            "manaValue": None,
            "number": None,
            "originalPrintings": [],
            "originalReleaseDate": None,
            "originalText": None,
            "originalType": None,
            "otherFaceIds": [],
            "power": None,
            "printings": [],
            "promoTypes": [],
            "rarity": None,
            "rebalancedPrintings": [],
            "relatedCards": [],
            "securityStamp": None,
            "side": None,
            "signature": None,
            "sourceProducts": [],
            "subsets": [],
            "supertypes": [],
            "subtypes": [],
            "text": None,
            "toughness": None,
            "type": None,
            "types": [],
            "variations": [],
            "watermark": None
        }
        
        printing = Printing(**minimal_data)
        
        assert printing.name == "Test Card"
        assert printing.setCode == "TEST"
        assert printing.artistIds == []
        assert printing.colors == []
        assert printing.keywords == []

    def test_printing_list_field_parsing(self):
        """Test parsing of list fields."""
        data = {
            "uuid": "test-uuid",
            "name": "Test Card",
            "setCode": "TEST",
            "artist": None,
            "artistIds": [],
            "attractionLights": [],
            "availability": [],
            "boosterTypes": [],
            "borderColor": None,
            "cardParts": [],
            "colorIdentity": [],
            "colorIndicator": [],
            "colors": '["R", "G"]',
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
            "flavorText": None,
            "frameEffects": [],
            "frameVersion": None,
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
            "keywords": '["haste", "trample"]',
            "language": None,
            "layout": None,
            "leadershipSkills": {},
            "life": None,
            "loyalty": None,
            "manaCost": None,
            "manaValue": None,
            "number": None,
            "originalPrintings": [],
            "originalReleaseDate": None,
            "originalText": None,
            "originalType": None,
            "otherFaceIds": [],
            "power": None,
            "printings": [],
            "promoTypes": [],
            "rarity": None,
            "rebalancedPrintings": [],
            "relatedCards": [],
            "securityStamp": None,
            "side": None,
            "signature": None,
            "sourceProducts": [],
            "subsets": [],
            "supertypes": [],
            "subtypes": [],
            "text": None,
            "toughness": None,
            "type": None,
            "types": '["Creature"]',
            "variations": [],
            "watermark": None
        }
        
        printing = Printing(**data)
        
        assert printing.colors == ["R", "G"]
        assert printing.keywords == ["haste", "trample"]
        assert printing.types == ["Creature"]

    def test_printing_dict_field_parsing(self):
        """Test parsing of dict fields."""
        data = {
            "uuid": "test-uuid",
            "name": "Test Card",
            "setCode": "TEST",
            "artist": None,
            "artistIds": [],
            "attractionLights": [],
            "availability": [],
            "boosterTypes": [],
            "borderColor": None,
            "cardParts": [],
            "colorIdentity": [],
            "colorIndicator": [],
            "colors": [],
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
            "flavorText": None,
            "frameEffects": [],
            "frameVersion": None,
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
            "keywords": [],
            "language": None,
            "layout": None,
            "leadershipSkills": '{"commander": "legal"}',
            "life": None,
            "loyalty": None,
            "manaCost": None,
            "manaValue": None,
            "number": None,
            "originalPrintings": [],
            "originalReleaseDate": None,
            "originalText": None,
            "originalType": None,
            "otherFaceIds": [],
            "power": None,
            "printings": [],
            "promoTypes": [],
            "rarity": None,
            "rebalancedPrintings": [],
            "relatedCards": [],
            "securityStamp": None,
            "side": None,
            "signature": None,
            "sourceProducts": [],
            "subsets": [],
            "supertypes": [],
            "subtypes": [],
            "text": None,
            "toughness": None,
            "type": None,
            "types": [],
            "variations": [],
            "watermark": None
        }
        
        printing = Printing(**data)
        
        assert printing.leadershipSkills == {"commander": "legal"}

    def test_printing_repr(self, sample_printing_data):
        """Test Printing string representation."""
        printing = Printing(**sample_printing_data)
        
        repr_str = repr(printing)
        assert "Lightning Bolt" in repr_str
        assert "LEA" in repr_str


class TestSummaryCard:
    """Test SummaryCard model."""

    def test_summary_card_creation(self, sample_summary_card_data):
        """Test creating SummaryCard instance."""
        card = SummaryCard(**sample_summary_card_data)
        
        assert card.name == "Lightning Bolt"
        assert card.set_code == "LEA"
        assert card.mana_cost == "{R}"
        assert card.converted_mana_cost == 1.0
        assert card.colors == ["R"]
        assert card.type == "Instant"
        assert card.text == "Lightning Bolt deals 3 damage to any target."
        assert card.rarity == "Common"
        assert card.keywords == ["damage"]

    def test_summary_card_defaults(self):
        """Test SummaryCard with minimal data."""
        minimal_data = {
            "name": "Test Card"
        }
        
        card = SummaryCard(**minimal_data)
        
        assert card.name == "Test Card"
        assert card.set_code == ""
        assert card.rarity == ""
        assert card.type == ""
        assert card.mana_cost == ""
        assert card.converted_mana_cost == 0.0
        assert card.colors == []
        assert card.keywords == []

    def test_summary_card_properties(self, sample_summary_card_data):
        """Test SummaryCard properties."""
        card = SummaryCard(**sample_summary_card_data)
        
        # Test quantity property
        assert card.quantity == 0  # No inventory item set
        
        # Test list properties
        assert card.colors_list == ["R"]
        assert card.color_identity_list == ["R"]
        assert card.supertypes_list == []
        assert card.subtypes_list == []
        assert card.keywords_list == ["damage"]

    def test_summary_card_matching_methods(self, sample_summary_card_data):
        """Test SummaryCard matching methods."""
        card = SummaryCard(**sample_summary_card_data)
        
        # Test color identity matching
        assert card.matches_color_identity(["R"], mode="subset")
        assert card.matches_color_identity(["R", "G"], mode="subset")
        assert not card.matches_color_identity(["G"], mode="subset")
        
        # Test color matching
        assert card.matches_colors(["R"], mode="subset")
        assert card.matches_colors(["R", "G"], mode="subset")
        assert not card.matches_colors(["G"], mode="subset")
        
        # Test keyword matching
        assert card.has_keywords(["damage"])
        assert not card.has_keywords(["flying"])

    def test_summary_card_type_methods(self, sample_summary_card_data):
        """Test SummaryCard type checking methods."""
        card = SummaryCard(**sample_summary_card_data)
        
        # Test basic land check
        assert not card.is_basic_land()
        
        # Test land check
        assert not card.is_land()
        
        # Test creature check
        assert not card.is_creature()
        
        # Test type matching
        assert card.matches_type("Instant")
        assert not card.matches_type("Creature")

    def test_summary_card_owned_quantity(self, sample_summary_card_data):
        """Test SummaryCard owned quantity property."""
        card = SummaryCard(**sample_summary_card_data)
        
        # Test without inventory item
        assert card.owned_qty == 0
        
        # Test with inventory item
        mock_inventory = MagicMock()
        mock_inventory.quantity = 4
        card.inventory_item = mock_inventory
        
        assert card.owned_qty == 4

    def test_summary_card_to_dict(self, sample_summary_card_data):
        """Test SummaryCard to_dict method."""
        card = SummaryCard(**sample_summary_card_data)
        
        card_dict = card.to_dict()
        
        assert card_dict["name"] == "Lightning Bolt"
        assert card_dict["set_code"] == "LEA"
        assert card_dict["mana_cost"] == "{R}"
        assert card_dict["converted_mana_cost"] == 1.0

    def test_summary_card_repr(self, sample_summary_card_data):
        """Test SummaryCard string representation."""
        card = SummaryCard(**sample_summary_card_data)
        
        repr_str = repr(card)
        assert "Lightning Bolt" in repr_str


class TestInventoryItem:
    """Test InventoryItem model."""

    def test_inventory_item_creation(self, sample_inventory_item_data):
        """Test creating InventoryItem instance."""
        item = InventoryItem(**sample_inventory_item_data)
        
        assert item.name == "Lightning Bolt"
        assert item.quantity == 4

    def test_inventory_item_defaults(self):
        """Test InventoryItem with minimal data."""
        minimal_data = {
            "name": "Test Card",
            "quantity": 1
        }
        
        item = InventoryItem(**minimal_data)
        
        assert item.name == "Test Card"
        assert item.quantity == 1

    def test_inventory_item_validation(self):
        """Test InventoryItem validation."""
        # The Pydantic model doesn't have validation for quantity or condition
        # So we just test that it accepts valid data
        item = InventoryItem(name="Lightning Bolt", quantity=0)
        assert item.name == "Lightning Bolt"
        assert item.quantity == 0
        
        # Test with negative quantity (should work since no validation)
        item = InventoryItem(name="Lightning Bolt", quantity=-1)
        assert item.quantity == -1

    def test_inventory_item_repr(self, sample_inventory_item_data):
        """Test InventoryItem string representation."""
        item = InventoryItem(**sample_inventory_item_data)
        
        repr_str = repr(item)
        assert "Lightning Bolt" in repr_str 