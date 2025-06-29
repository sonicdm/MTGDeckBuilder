"""
Tests for Gradio UI components in the MTG Deck Builder application.

These tests validate:
- UI component creation and rendering
- Component state management
- Event handling and callbacks
- UI abstraction layer functionality
- Component interactions and updates
"""

import pytest
import gradio as gr
from unittest.mock import MagicMock, patch, PropertyMock
import sys
import os
from pathlib import Path
import pandas as pd
import json

# Make sure the mtg_deckbuilder_ui module is in the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Mock app_config before importing it
with patch.dict("sys.modules", {"mtg_deckbuilder_ui.app_config": MagicMock()}):
    from mtg_deckbuilder_ui.app_config import app_config, PROJECT_ROOT

    # Configure mock app_config
    def mock_get_path(key):
        # Use a real Path object relative to a mock project root for consistency
        mock_root = Path("/mock_project")
        paths = {
            "database": mock_root / "test_cards.db",
            "inventory": mock_root / "test_inventory",
            "decks": mock_root / "test_decks",
            "keywords": mock_root / "test_mtgjson" / "Keywords.json",
            "cardtypes": mock_root / "test_mtgjson" / "CardTypes.json",
            "mtgjson": mock_root / "test_mtgjson",
        }
        if key not in paths:
            raise KeyError(f"Mock path for '{key}' not found.")
        return paths[key]

    app_config.get_path.side_effect = mock_get_path
    app_config.get_list.return_value = ["standard", "modern", "commander"]
    app_config.get_bool.return_value = False  # Default for boolean checks
    app_config.get.return_value = ""  # Default for simple string gets

# Import UI components after mocking
from mtg_deckbuilder_ui.ui.ui_objects import UIElement, UISection, UITab
from mtg_deckbuilder_ui.ui.tabs.deckbuilder_components import create_deck_identity_section
from mtg_deckbuilder_ui.ui.tabs.collection_viewer_components import create_collection_viewer_components
from mtg_deckbuilder_ui.ui.tabs.inventory_manager_components import create_inventory_manager_components


@pytest.fixture
def create_test_json_files(tmp_path):
    """Create test JSON files for MTG keywords and card types."""
    mtgjson_dir = tmp_path / "test_mtgjson"
    mtgjson_dir.mkdir()

    # Create Keywords.json
    keywords_data = {
        "data": {
            "abilityWords": ["Landfall", "Threshold"],
            "keywordAbilities": ["Flying", "Vigilance", "Trample"],
            "keywordActions": ["Sacrifice", "Scry"],
        }
    }
    with open(mtgjson_dir / "Keywords.json", "w") as f:
        json.dump(keywords_data, f)

    # Create CardTypes.json
    cardtypes_data = {
        "data": {
            "creature": {"subTypes": ["Angel", "Human", "Warrior"]},
            "artifact": {"subTypes": ["Equipment", "Vehicle"]},
        }
    }
    with open(mtgjson_dir / "CardTypes.json", "w") as f:
        json.dump(cardtypes_data, f)

    # Update mock_get_path to use the temp directory
    app_config.get_path.side_effect = lambda key: (
        tmp_path / "test_mtgjson"
        if key == "mtgjson"
        else (
            tmp_path / "test_mtgjson" / "Keywords.json"
            if key == "keywords"
            else (
                tmp_path / "test_mtgjson" / "CardTypes.json"
                if key == "cardtypes"
                else mock_get_path(key)
            )
        )
    )

    return mtgjson_dir


class MockCard:
    """Mock card object for testing."""
    def __init__(self, **kwargs):
        # Default values for all attributes that might be accessed
        self.name = kwargs.get("name", "")
        self.text = kwargs.get("text", "")
        self.type = kwargs.get("type", "")
        self.power = kwargs.get("power", "")
        self.toughness = kwargs.get("toughness", "")
        self.colors = kwargs.get("colors", [])
        self.color_identity = kwargs.get("color_identity", [])
        self.mana_cost = kwargs.get("mana_cost", "")
        self.converted_mana_cost = kwargs.get("converted_mana_cost", 0)
        self.rarity = kwargs.get("rarity", "")
        self.keywords = kwargs.get("keywords", [])
        self.owned_qty = kwargs.get("owned_qty", 0)
        self.flavor_text = kwargs.get("flavor_text", "")
        self.abilities = kwargs.get("abilities", [])
        self.legalities = kwargs.get("legalities", {})
        self.newest_printing_uid = kwargs.get("newest_printing_uid", "")
        self.card_type = kwargs.get("card_type", "")
        self.set = kwargs.get("set", None)

        # Set up newest_printing relationship
        self.newest_printing_rel = kwargs.get("newest_printing", None)
        if hasattr(self, "newest_printing"):
            self.newest_printing_rel = self.newest_printing

        # Add required methods
        self.matches_color_identity = lambda colors, mode: True


@pytest.fixture
def mock_card_repository():
    """Create a mock card repository with test data."""
    mock_repo = MagicMock()

    serra = MockCard(
        name="Serra Angel",
        text="Flying, vigilance",
        type="Creature — Angel",
        power="4",
        toughness="4",
        colors=["W"],
        color_identity=["W"],
        mana_cost="{3}{W}{W}",
        converted_mana_cost=5,
        rarity="uncommon",
        keywords=["Flying", "Vigilance"],
        owned_qty=2,
        flavor_text="",
        abilities=[],
        legalities={"standard": "legal"},
    )
    serra.newest_printing = MockCard(
        set_code="DOM",
        artist="Douglas Shuler",
        number="33",
        color_identity=["W"],
        keywords=["Flying", "Vigilance"],
        supertypes=[],
        subtypes=["Angel"],
        card_type="Creature",
    )

    bolt = MockCard(
        name="Lightning Bolt",
        text="Deal 3 damage to any target.",
        type="Instant",
        colors=["R"],
        color_identity=["R"],
        mana_cost="{R}",
        converted_mana_cost=1,
        rarity="common",
        owned_qty=4,
        flavor_text="",
        abilities=[],
        legalities={"modern": "legal"},
    )
    bolt.newest_printing = MockCard(
        set_code="M10",
        artist="Christopher Moeller",
        number="146",
        color_identity=["R"],
        keywords=[],
        supertypes=[],
        subtypes=[],
        card_type="Instant",
    )

    all_cards = [serra, bolt]
    mock_repo._cards = all_cards
    mock_repo.get_all_cards.return_value = all_cards

    def filter_cards_side_effect(**kwargs):
        # Simple filtering logic for testing
        filtered_cards = all_cards.copy()
        
        if 'name_query' in kwargs and kwargs['name_query']:
            filtered_cards = [c for c in filtered_cards if kwargs['name_query'].lower() in c.name.lower()]
        
        if 'colors' in kwargs and kwargs['colors']:
            filtered_cards = [c for c in filtered_cards if any(color in c.colors for color in kwargs['colors'])]
        
        if 'rarity' in kwargs and kwargs['rarity']:
            filtered_cards = [c for c in filtered_cards if c.rarity == kwargs['rarity']]
        
        return filtered_cards

    mock_repo.filter_cards.side_effect = filter_cards_side_effect
    return mock_repo


@pytest.fixture
def mock_inventory_repository():
    """Create a mock inventory repository."""
    mock_repo = MagicMock()
    mock_repo.get_owned_cards.return_value = []
    mock_repo.get_inventory_files.return_value = ["test_inventory.txt"]
    return mock_repo


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    session = MagicMock()
    session.query.return_value.filter.return_value.all.return_value = []
    return session


class TestUIElement:
    """Test the UIElement class."""

    def test_ui_element_creation(self):
        """Test creating a UIElement."""
        element = UIElement("test_element", gr.Textbox())
        
        assert element.name == "test_element"
        assert element.component is not None
        assert element.get_name() == "test_element"

    def test_ui_element_get_component(self):
        """Test getting component from UIElement."""
        component = gr.Textbox()
        element = UIElement("test", component)
        
        assert element.get_component() == component

    def test_ui_element_get_state(self):
        """Test getting state from UIElement."""
        element = UIElement("test", gr.Textbox())
        
        # Test with various input types
        assert element.get_state("test_value") == "test_value"
        assert element.get_state(None) is None
        assert element.get_state(42) == 42


class TestUISection:
    """Test the UISection class."""

    def test_ui_section_creation(self):
        """Test creating a UISection."""
        section = UISection("test_section")
        
        assert section.name == "test_section"
        assert section.elements == {}
        assert section.get_name() == "test_section"

    def test_ui_section_add_element(self):
        """Test adding elements to a UISection."""
        section = UISection("test_section")
        element = UIElement("test_element", gr.Textbox())
        
        section.add_element(element)
        
        assert "test_element" in section.elements
        assert section.get_element("test_element") == element

    def test_ui_section_get_components(self):
        """Test getting components from a UISection."""
        section = UISection("test_section")
        element1 = UIElement("element1", gr.Textbox())
        element2 = UIElement("element2", gr.Button())
        
        section.add_element(element1)
        section.add_element(element2)
        
        components = section.get_components()
        
        assert "element1" in components
        assert "element2" in components
        assert isinstance(components["element1"], gr.Textbox)
        assert isinstance(components["element2"], gr.Button)

    def test_ui_section_get_elements(self):
        """Test getting elements from a UISection."""
        section = UISection("test_section")
        element = UIElement("test_element", gr.Textbox())
        
        section.add_element(element)
        
        elements = section.get_elements()
        
        assert "test_element" in elements
        assert elements["test_element"] == element


class TestUITab:
    """Test the UITab class."""

    def test_ui_tab_creation(self):
        """Test creating a UITab."""
        tab = UITab("test_tab")
        
        assert tab.name == "test_tab"
        assert tab.sections == {}
        assert tab.get_name() == "test_tab"

    def test_ui_tab_add_section(self):
        """Test adding sections to a UITab."""
        tab = UITab("test_tab")
        section = UISection("test_section")
        
        tab.add_section(section)
        
        assert "test_section" in tab.sections
        assert tab.get_section("test_section") == section

    def test_ui_tab_get_components(self):
        """Test getting components from a UITab."""
        tab = UITab("test_tab")
        section = UISection("test_section")
        element = UIElement("test_element", gr.Textbox())
        
        section.add_element(element)
        tab.add_section(section)
        
        components = tab.get_components()
        
        assert "test_element" in components
        assert isinstance(components["test_element"], gr.Textbox)

    def test_ui_tab_get_elements(self):
        """Test getting elements from a UITab."""
        tab = UITab("test_tab")
        section = UISection("test_section")
        element = UIElement("test_element", gr.Textbox())
        
        section.add_element(element)
        tab.add_section(section)
        
        elements = tab.get_elements()
        
        assert "test_element" in elements
        assert elements["test_element"] == element

    def test_ui_tab_get_state(self):
        """Test getting state from a UITab."""
        tab = UITab("test_tab")
        section = UISection("test_section")
        element = UIElement("test_element", gr.Textbox())
        
        section.add_element(element)
        tab.add_section(section)
        
        values = {"test_element": "test_value"}
        state = tab.get_state(values)
        
        assert "test_section" in state
        assert state["test_section"]["test_element"] == "test_value"


class TestDeckIdentitySection:
    """Test the deck identity section components."""

    def test_create_deck_identity_section(self):
        """Test creating deck identity section."""
        section = create_deck_identity_section()
        
        assert isinstance(section, UISection)
        assert section.name == "deck_identity"
        
        # Check that required elements exist
        elements = section.get_elements()
        expected_elements = ["deck_name", "deck_colors", "deck_size", "max_copies"]
        
        for element_name in expected_elements:
            assert element_name in elements
            assert elements[element_name].get_component() is not None


class TestCollectionViewerComponents:
    """Test the collection viewer components."""

    def test_create_collection_viewer_components(self):
        """Test creating collection viewer components."""
        components = create_collection_viewer_components()
        
        assert isinstance(components, dict)
        
        # Check that required components exist
        expected_components = ["search_box", "filter_panel", "card_table"]
        
        for component_name in expected_components:
            assert component_name in components
            assert components[component_name] is not None


class TestInventoryManagerComponents:
    """Test the inventory manager components."""

    def test_create_inventory_manager_components(self):
        """Test creating inventory manager components."""
        components = create_inventory_manager_components()
        
        assert isinstance(components, dict)
        
        # Check that required components exist
        expected_components = ["file_upload", "import_button", "status_display"]
        
        for component_name in expected_components:
            assert component_name in components
            assert components[component_name] is not None


class TestComponentInteractions:
    """Test component interactions and updates."""

    def test_component_value_updates(self):
        """Test that component values can be updated."""
        element = UIElement("test", gr.Textbox())
        
        # Test updating component value
        update = gr.update(value="new_value")
        assert update["value"] == "new_value"

    def test_component_visibility_updates(self):
        """Test that component visibility can be updated."""
        element = UIElement("test", gr.Textbox())
        
        # Test updating component visibility
        update = gr.update(visible=False)
        assert update["visible"] is False

    def test_component_interactivity_updates(self):
        """Test that component interactivity can be updated."""
        element = UIElement("test", gr.Textbox())
        
        # Test updating component interactivity
        update = gr.update(interactive=False)
        assert update["interactive"] is False


class TestUIStateManagement:
    """Test UI state management functionality."""

    def test_section_state_management(self):
        """Test state management within a section."""
        section = UISection("test_section")
        element1 = UIElement("element1", gr.Textbox())
        element2 = UIElement("element2", gr.Number())
        
        section.add_element(element1)
        section.add_element(element2)
        
        # Test getting state
        values = {"element1": "test", "element2": 42}
        state = section.get_state(values)
        
        assert state["element1"] == "test"
        assert state["element2"] == 42

    def test_tab_state_management(self):
        """Test state management within a tab."""
        tab = UITab("test_tab")
        section = UISection("test_section")
        element = UIElement("test_element", gr.Textbox())
        
        section.add_element(element)
        tab.add_section(section)
        
        # Test getting state
        values = {"test_element": "test_value"}
        state = tab.get_state(values)
        
        assert "test_section" in state
        assert state["test_section"]["test_element"] == "test_value"


if __name__ == "__main__":
    pytest.main([__file__]) 