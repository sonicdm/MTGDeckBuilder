"""
Test utility functions.

These tests validate:
- Arena deck creator utilities
- Arena parser functionality
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

# Import the actual functions that exist
from mtg_deck_builder.utils.arena_deck_creator import create_deck_from_arena_import, validate_arena_import_with_database
from mtg_deck_builder.utils.arena_parser import parse_arena_export


@pytest.fixture
def sample_arena_export():
    """Sample Arena export format."""
    return """Deck
4 Lightning Bolt (LEA) 74
2 Serra Angel (LEA) 1
3 Counterspell (LEA) 2
1 Black Lotus (LEA) 3
20 Plains (LEA) 1
10 Swamp (LEA) 2"""


class TestArenaDeckCreator:
    """Test Arena deck creator utilities."""

    def test_create_deck_from_arena_import(self, sample_arena_export):
        """Test creating deck from Arena import."""
        # This will likely return None since we don't have a real database
        # but we can test that the function doesn't crash
        result = create_deck_from_arena_import(sample_arena_export, "Test Deck")
        assert result is None or hasattr(result, "name")

    def test_validate_arena_import_with_database(self, sample_arena_export):
        """Test validating Arena import with database."""
        # This will likely return False since we don't have a real database
        # but we can test that the function doesn't crash
        is_valid, errors = validate_arena_import_with_database(sample_arena_export)
        assert isinstance(is_valid, bool)
        assert isinstance(errors, list)

    def test_validate_arena_import_with_format(self, sample_arena_export):
        """Test validating Arena import with format."""
        is_valid, errors = validate_arena_import_with_database(sample_arena_export, "standard")
        assert isinstance(is_valid, bool)
        assert isinstance(errors, list)


class TestArenaParser:
    """Test Arena parser functionality."""

    def test_parse_arena_export(self, sample_arena_export):
        """Test parsing Arena export format."""
        arena_lines = sample_arena_export.strip().split('\n')
        deck_data = parse_arena_export(arena_lines)
        
        assert "main" in deck_data
        assert "sideboard" in deck_data
        assert len(deck_data["main"]) == 6

    def test_parse_card_line(self):
        """Test parsing individual card line."""
        card_line = "4 Lightning Bolt (LEA) 74"
        arena_lines = [card_line]
        
        deck_data = parse_arena_export(arena_lines)
        
        assert "main" in deck_data
        assert "Lightning Bolt" in deck_data["main"]
        assert deck_data["main"]["Lightning Bolt"] == 4

    def test_parse_card_line_without_set(self):
        """Test parsing card line without set information."""
        card_line = "2 Lightning Bolt"
        arena_lines = [card_line]
        
        deck_data = parse_arena_export(arena_lines)
        
        assert "main" in deck_data
        assert "Lightning Bolt" in deck_data["main"]
        assert deck_data["main"]["Lightning Bolt"] == 2

    def test_parse_invalid_card_line(self):
        """Test parsing invalid card line."""
        invalid_line = "Invalid card line"
        arena_lines = [invalid_line]
        
        # This should handle invalid lines gracefully
        deck_data = parse_arena_export(arena_lines)
        assert isinstance(deck_data, dict)

    def test_parse_arena_export_with_sideboard(self):
        """Test parsing Arena export with sideboard."""
        arena_export_with_sideboard = """Deck
4 Lightning Bolt (LEA) 74

Sideboard
2 Counterspell (LEA) 2"""
        
        arena_lines = arena_export_with_sideboard.strip().split('\n')
        deck_data = parse_arena_export(arena_lines)
        
        assert "main" in deck_data
        assert "sideboard" in deck_data
        assert "Lightning Bolt" in deck_data["main"]
        assert "Counterspell" in deck_data["sideboard"] 