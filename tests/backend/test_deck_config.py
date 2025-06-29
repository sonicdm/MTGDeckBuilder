"""
Test the DeckConfig class from mtg_deck_builder.

These tests validate:
- YAML configuration parsing and validation
- Deck identity and constraints
- Category definitions and rules
- Mana base configuration
- Scoring rules and fallback strategies
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from mtg_deck_builder.models.deck_config import DeckConfig


@pytest.fixture
def sample_deck_config():
    """Create a sample deck configuration for testing."""
    return {
        "deck": {
            "name": "Test Deck",
            "colors": ["W", "B"],
            "size": 60,
            "max_card_copies": 4,
            "legalities": ["standard"],
            "color_match_mode": "subset",
            "owned_cards_only": True,
        },
        "categories": {
            "creatures": {
                "target": 24,
                "preferred_keywords": ["Flying", "Deathtouch"],
                "preferred_types": ["Creature"],
            },
            "spells": {
                "target": 12,
                "preferred_types": ["Instant", "Sorcery"],
            }
        },
        "mana_base": {
            "land_count": 24,
            "special_lands": {
                "Plains": 8,
                "Swamp": 8,
            }
        },
        "scoring_rules": {
            "keyword_bonuses": {
                "Flying": 2,
                "Deathtouch": 1,
            },
            "type_bonuses": {
                "Creature": 1,
                "Instant": 1,
            }
        },
        "fallback_strategy": {
            "fill_with_any_cards": True,
            "allow_fewer_cards": False,
        }
    }


@pytest.fixture
def temp_yaml_file(sample_deck_config):
    """Create a temporary YAML file with test configuration."""
    import yaml
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(sample_deck_config, f)
        temp_path = Path(f.name)
    
    yield temp_path
    
    # Cleanup
    temp_path.unlink(missing_ok=True)


class TestDeckConfig:
    """Test the DeckConfig class."""

    def test_deck_config_creation_from_dict(self, sample_deck_config):
        """Test creating DeckConfig from dictionary."""
        config = DeckConfig(**sample_deck_config)
        
        assert config.deck.name == "Test Deck"
        assert config.deck.colors == ["W", "B"]
        assert config.deck.size == 60
        assert config.deck.max_card_copies == 4
        assert config.deck.legalities == ["standard"]
        assert config.deck.color_match_mode == "subset"
        assert config.deck.owned_cards_only is True

    def test_deck_config_creation_from_yaml_file(self, temp_yaml_file):
        """Test creating DeckConfig from YAML file."""
        config = DeckConfig.from_yaml_file(temp_yaml_file)
        
        assert config.deck.name == "Test Deck"
        assert config.deck.colors == ["W", "B"]
        assert config.deck.size == 60

    def test_deck_config_validation_valid(self, sample_deck_config):
        """Test that valid configuration passes validation."""
        config = DeckConfig(**sample_deck_config)
        
        # Should not raise any exceptions
        assert config is not None
        assert config.validate() is True

    def test_deck_config_validation_invalid_deck_size(self, sample_deck_config):
        """Test validation with invalid deck size."""
        sample_deck_config["deck"]["size"] = 30  # Invalid size
        
        with pytest.raises(ValueError, match="Deck size must be"):
            DeckConfig(**sample_deck_config)

    def test_deck_config_validation_invalid_colors(self, sample_deck_config):
        """Test validation with invalid colors."""
        sample_deck_config["deck"]["colors"] = ["X"]  # Invalid color
        
        with pytest.raises(ValueError, match="Invalid color"):
            DeckConfig(**sample_deck_config)

    def test_deck_config_categories(self, sample_deck_config):
        """Test category configuration."""
        config = DeckConfig(**sample_deck_config)
        
        assert "creatures" in config.categories
        assert "spells" in config.categories
        
        creatures_cat = config.categories["creatures"]
        assert creatures_cat.target == 24
        assert "Flying" in creatures_cat.preferred_keywords
        assert "Creature" in creatures_cat.preferred_types

    def test_deck_config_mana_base(self, sample_deck_config):
        """Test mana base configuration."""
        config = DeckConfig(**sample_deck_config)
        
        assert config.mana_base.land_count == 24
        assert config.mana_base.special_lands["Plains"] == 8
        assert config.mana_base.special_lands["Swamp"] == 8

    def test_deck_config_scoring_rules(self, sample_deck_config):
        """Test scoring rules configuration."""
        config = DeckConfig(**sample_deck_config)
        
        assert config.scoring_rules.keyword_bonuses["Flying"] == 2
        assert config.scoring_rules.keyword_bonuses["Deathtouch"] == 1
        assert config.scoring_rules.type_bonuses["Creature"] == 1

    def test_deck_config_fallback_strategy(self, sample_deck_config):
        """Test fallback strategy configuration."""
        config = DeckConfig(**sample_deck_config)
        
        assert config.fallback_strategy.fill_with_any_cards is True
        assert config.fallback_strategy.allow_fewer_cards is False

    def test_deck_config_to_dict(self, sample_deck_config):
        """Test converting DeckConfig back to dictionary."""
        config = DeckConfig(**sample_deck_config)
        config_dict = config.to_dict()
        
        assert config_dict["deck"]["name"] == "Test Deck"
        assert config_dict["deck"]["colors"] == ["W", "B"]
        assert config_dict["deck"]["size"] == 60

    def test_deck_config_to_yaml(self, sample_deck_config):
        """Test converting DeckConfig to YAML string."""
        config = DeckConfig(**sample_deck_config)
        yaml_str = config.to_yaml()
        
        assert "Test Deck" in yaml_str
        assert "W" in yaml_str
        assert "B" in yaml_str

    def test_deck_config_save_to_file(self, sample_deck_config, temp_path):
        """Test saving DeckConfig to YAML file."""
        config = DeckConfig(**sample_deck_config)
        output_file = temp_path / "test_output.yaml"
        
        config.save_to_file(output_file)
        
        assert output_file.exists()
        with open(output_file, 'r') as f:
            content = f.read()
            assert "Test Deck" in content

    def test_deck_config_priority_cards(self, sample_deck_config):
        """Test priority cards configuration."""
        sample_deck_config["priority_cards"] = {
            "Lightning Bolt": 4,
            "Serra Angel": 2
        }
        
        config = DeckConfig(**sample_deck_config)
        
        assert "Lightning Bolt" in config.priority_cards
        assert config.priority_cards["Lightning Bolt"] == 4
        assert config.priority_cards["Serra Angel"] == 2

    def test_deck_config_constraints(self, sample_deck_config):
        """Test deck constraints configuration."""
        sample_deck_config["constraints"] = {
            "max_cmc": 4,
            "min_rarity": "common",
            "exclude_types": ["Land"]
        }
        
        config = DeckConfig(**sample_deck_config)
        
        assert config.constraints.max_cmc == 4
        assert config.constraints.min_rarity == "common"
        assert "Land" in config.constraints.exclude_types

    def test_deck_config_invalid_yaml_file(self):
        """Test handling of invalid YAML file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content: [")
            temp_path = Path(f.name)
        
        try:
            with pytest.raises(Exception):
                DeckConfig.from_yaml_file(temp_path)
        finally:
            temp_path.unlink(missing_ok=True)

    def test_deck_config_missing_required_fields(self):
        """Test handling of missing required fields."""
        incomplete_config = {
            "deck": {
                "name": "Test Deck"
                # Missing required fields
            }
        }
        
        with pytest.raises(ValueError):
            DeckConfig(**incomplete_config)

    def test_deck_config_default_values(self):
        """Test that default values are properly set."""
        minimal_config = {
            "deck": {
                "name": "Test Deck",
                "colors": ["W"],
                "size": 60
            }
        }
        
        config = DeckConfig(**minimal_config)
        
        # Check default values
        assert config.deck.max_card_copies == 4
        assert config.deck.color_match_mode == "exact"
        assert config.deck.owned_cards_only is False


@pytest.fixture
def temp_path(tmp_path):
    """Provide a temporary path for file operations."""
    return tmp_path 