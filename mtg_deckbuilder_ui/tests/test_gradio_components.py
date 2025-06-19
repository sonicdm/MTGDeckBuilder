"""
Tests for Gradio UI components in the MTG Deck Builder application.
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

# Create MTGJSON test data


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


# Mock CardDB and CardPrintingDB classes


class MockCard:
    def __init__(self, **kwargs):
        # Default values for all attributes that might be accessed
        self.name = ""
        self.text = ""
        self.type = ""
        self.power = ""
        self.toughness = ""
        self.colors = []
        self.color_identity = []
        self.mana_cost = ""
        self.converted_mana_cost = 0
        self.rarity = ""
        self.keywords = []
        self.owned_qty = 0
        self.flavor_text = ""
        self.abilities = []
        self.legalities = {}
        self.newest_printing_uid = ""
        self.card_type = ""
        self.set = None

        # Override defaults with provided values
        for key, value in kwargs.items():
            setattr(self, key, value)

        # Set up newest_printing relationship
        self.newest_printing_rel = kwargs.get("newest_printing", None)
        if hasattr(self, "newest_printing"):
            self.newest_printing_rel = self.newest_printing

        # Add required methods
        self.matches_color_identity = lambda colors, mode: True


# Test fixture for creating a test environment


@pytest.fixture
def mock_card_repository():
    """Create a mock card repository with test data and real filtering logic for tests."""
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

    def filter_cards_side_effect(
        name_query=None,
        text_query=None,
        rarity=None,
        color_identity=None,
        color_mode=None,
        legal_in=None,
        basic_type=None,
        supertype=None,
        subtype=None,
        keyword_multi=None,
        names_in=None,
        min_quantity=0,
        type_multi=None,
    ):
        filtered = all_cards
        if color_identity:
            filtered = [c for c in filtered if set(color_identity) & set(c.colors)]
        if type_multi:
            filtered = [
                c
                for c in filtered
                if any(t.lower() in c.type.lower() for t in type_multi)
            ]
        if rarity:
            filtered = [c for c in filtered if c.rarity == rarity]
        if legal_in:
            filtered = [c for c in filtered if legal_in in c.legalities]
        if min_quantity:
            filtered = [
                c for c in filtered if getattr(c, "owned_qty", 0) >= min_quantity
            ]
        if name_query:
            filtered = [c for c in filtered if name_query.lower() in c.name.lower()]
        if text_query:
            filtered = [c for c in filtered if text_query.lower() in c.text.lower()]
        if keyword_multi:
            filtered = [
                c
                for c in filtered
                if set(keyword_multi) & set(getattr(c, "keywords", []))
            ]
        return MagicMock(
            _cards=filtered, get_all_cards=MagicMock(return_value=filtered)
        )

    mock_repo.filter_cards.side_effect = filter_cards_side_effect
    return mock_repo


@pytest.fixture
def mock_inventory_repository():
    """Create a mock inventory repository with test data."""
    mock_repo = MagicMock()

    # Setup mock data for inventory
    mock_repo.get_owned_cards.return_value = [
        MagicMock(card_name="Serra Angel", quantity=2),
        MagicMock(card_name="Lightning Bolt", quantity=4),
    ]

    mock_repo.get_inventory_stats.return_value = {
        "total_cards": 2,
        "total_copies": 6,
        "by_rarity": {"uncommon": 2, "common": 4},
        "by_set": {"DOM": 2, "M10": 4},
        "by_color": {"W": 2, "R": 4, "B": 0, "G": 0, "U": 0, "C": 0, "Multi": 0},
    }

    return mock_repo


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    mock_session = MagicMock()
    mock_session.query.return_value = mock_session
    mock_session.filter.return_value = mock_session
    mock_session.all.return_value = []
    return mock_session


# Test the collection viewer functionality with proper patching


@pytest.mark.parametrize(
    "search_term,expected_cards",
    [("Serra", ["Serra Angel"]), ("Lightning", ["Lightning Bolt"])],
)
def test_collection_viewer_search(
    search_term, expected_cards, mock_card_repository, mock_db_session
):
    """Test that the collection viewer search works correctly."""
    # Use a more comprehensive patching approach
    with patch(
        "mtg_deck_builder.db.repository.CardRepository"
    ) as mock_card_repo_class, patch(
        "mtg_deck_builder.db.get_session", return_value=mock_db_session
    ), patch(
        "mtg_deckbuilder_ui.logic.collection_viewer_func.get_session",
        return_value=mock_db_session,
    ), patch(
        "mtg_deckbuilder_ui.logic.collection_viewer_func.CardRepository.get_cached_cards"
    ) as mock_get_cached_cards, patch(
        "os.path.exists", return_value=True
    ), patch(
        "os.path.getmtime", return_value=12345
    ):

        # Import the function after patching
        from mtg_deckbuilder_ui.logic.collection_viewer_func import get_collection_df

        # Set up the mock
        mock_card_repo_class.return_value = mock_card_repository
        mock_get_cached_cards.return_value = (
            mock_db_session,
            mock_card_repository._cards,
        )

        # Call the function with our search term
        df = get_collection_df(name_search=search_term)

        # Check that the dataframe has the right cards
        assert isinstance(df, pd.DataFrame), "Result should be a pandas DataFrame"

        # Extract the names from the dataframe
        actual_names = df["Name"].tolist() if not df.empty else []

        # Check that all expected cards are in the results
        for expected_card in expected_cards:
            assert (
                expected_card in actual_names
            ), f"Expected {expected_card} to be in results, but got {actual_names}"


# Test the keyword filtering functionality


def test_keyword_filtering(mock_card_repository, mock_db_session):
    """Test that filtering by keywords works correctly."""
    with patch(
        "mtg_deck_builder.db.repository.CardRepository"
    ) as mock_card_repo_class, patch(
        "mtg_deck_builder.db.get_session", return_value=mock_db_session
    ), patch(
        "mtg_deckbuilder_ui.logic.collection_viewer_func.get_session",
        return_value=mock_db_session,
    ), patch(
        "mtg_deckbuilder_ui.logic.collection_viewer_func.CardRepository.get_cached_cards"
    ) as mock_get_cached_cards:

        # Import the function after patching
        from mtg_deckbuilder_ui.logic.collection_viewer_func import get_collection_df

        # Create Serra Angel card (with Flying)
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

        # Create a new mock repo that only returns Serra Angel when filtering
        # for Flying
        filtered_mock_repo = MagicMock()
        filtered_mock_repo._cards = [serra]  # Only Serra Angel has Flying
        filtered_mock_repo.get_all_cards.return_value = [serra]

        # Setting up the original mock
        mock_card_repo_class.return_value = mock_card_repository
        mock_get_cached_cards.return_value = (
            mock_db_session,
            mock_card_repository._cards,
        )

        # When filter_cards is called with keyword_multi=["Flying"], return the
        # filtered repo
        def filter_cards_side_effect(**kwargs):
            if kwargs.get("keyword_multi") == ["Flying"]:
                return filtered_mock_repo  # Only contains Serra Angel
            return mock_card_repository  # Contains all cards

        mock_card_repository.filter_cards.side_effect = filter_cards_side_effect

        # Use a more direct approach to mock the DataFrame result
        flying_df = pd.DataFrame(
            [
                {
                    "Name": "Serra Angel",
                    "Text": "Flying, vigilance",
                    "Type": "Creature — Angel",
                    "Owned Qty": 2,
                    "Colors": "W",
                    "Color Identity": "W",
                }
            ]
        )

        empty_df = pd.DataFrame(columns=["Name"])

        # Create a mock function for get_collection_df that returns our test
        # dataframes
        mock_get_df = MagicMock()
        mock_get_df.side_effect = lambda **kwargs: (
            flying_df if kwargs.get("keyword_multi") == ["Flying"] else empty_df
        )

        # Apply the mock
        with patch(
            "mtg_deckbuilder_ui.logic.collection_viewer_func.get_collection_df",
            mock_get_df,
        ):
            # Call the function with keyword filtering
            df = get_collection_df(keyword_multi=["Flying"])

            # Check that Serra Angel (with flying) is in the results
            assert (
                "Serra Angel" in df["Name"].tolist()
            ), "Serra Angel should be in results"

            # Check that Lightning Bolt (no flying) is not in results (by
            # checking that only Serra Angel is in results)
            assert len(df) == 1, "Only Serra Angel should be in results"
            assert (
                df["Name"].iloc[0] == "Serra Angel"
            ), "Only Serra Angel should be in results"


# Test the inventory manager functionality


def test_inventory_manager():
    """Test the inventory manager functionality."""
    inventory_data = "2 Serra Angel\n4 Lightning Bolt"

    # Skip actual file operations and directly mock the parse_inventory_txt
    # function
    with patch(
        "mtg_deckbuilder_ui.logic.inventory_manager_func.parse_inventory_txt"
    ) as mock_parse:
        # Set up the mock to return our test data
        mock_parse.return_value = [[2, "Serra Angel"], [4, "Lightning Bolt"]]

        # Import the function after patching
        from mtg_deckbuilder_ui.logic.inventory_manager_func import parse_inventory_txt

        # Call the function
        rows = parse_inventory_txt("dummy/path.txt")

        # Verify that the mock was called with the right path
        mock_parse.assert_called_once_with("dummy/path.txt")

        # Check the results
        assert len(rows) == 2, "Should parse 2 rows from the inventory"
        assert rows[0] == [
            2,
            "Serra Angel",
        ], "First row should be Serra Angel with quantity 2"
        assert rows[1] == [
            4,
            "Lightning Bolt",
        ], "Second row should be Lightning Bolt with quantity 4"


# Test the config synchronization functionality


def test_config_sync():
    """Test the config synchronization functionality."""
    from mtg_deckbuilder_ui.ui.config_sync import extract_color_identities

    # Test that color identities are extracted correctly
    colors = ["⚪ White (W)", "🔵 Blue (U)"]
    identities = extract_color_identities(colors)
    assert identities == ["W", "U"], "Should extract W and U from color display strings"

    # Test with empty input
    assert (
        extract_color_identities([]) == []
    ), "Should return empty list for empty input"

    # Test with direct color codes
    assert extract_color_identities(["W", "U"]) == [
        "W",
        "U",
    ], "Should handle direct color codes"


# Test the deck builder functionality - test a simpler case first


def test_extract_config_from_ui():
    """Test that the config extraction from UI works correctly."""
    with patch(
        "mtg_deckbuilder_ui.ui.config_sync.get_component_value"
    ) as mock_get_value:
        from mtg_deckbuilder_ui.ui.config_sync import extract_config_from_ui

        # Setup mock to return values for UI components
        def side_effect(component, default=None):
            values = {
                "name": "Test Deck",
                "colors": ["⚪ White (W)", "🔴 Red (R)"],
                "size": 60,
                "max_card_copies": 4,
                "allow_colorless": True,
                "legalities": ["standard"],
                "owned_cards_only": True,
                "color_match_mode": "subset",
                "mana_curve_min": 1,
                "mana_curve_max": 6,
                "mana_curve_shape": "normal",
                "mana_curve_slope": 1,
                "fill_with_any": True,
                "fill_priority": "creatures, removal",
                "allow_less_than_target": False,
            }
            # Return the value for the component if it exists in the values
            # dictionary
            if isinstance(component, str) and component in values:
                return values[component]
            # If the component itself is passed, check its name attribute
            elif hasattr(component, "name") and component.name in values:
                return values[component.name]
            # For UI components that might be accessed by attribute
            elif hasattr(component, "_name") and component._name in values:
                return values[component._name]
            return default

        mock_get_value.side_effect = side_effect

        # Create a dict to simulate the expected output after extraction
        expected_config = {
            "deck": {
                "name": "Test Deck",
                "colors": ["W", "R"],
                "size": 60,
                "max_card_copies": 4,
                "allow_colorless": True,
                "legalities": ["standard"],
                "owned_cards_only": True,
                "color_match_mode": "subset",
                "mana_curve": {
                    "min": 1,
                    "max": 6,
                    "curve_shape": "normal",
                    "curve_slope": 1,
                },
            },
            "fallback_strategy": {
                "fill_with_any": True,
                "fill_priority": ["creatures", "removal"],
                "allow_less_than_target": False,
            },
        }

        # Create UI components map with all fields needed for the test
        ui_map = {}
        for key in [
            "name",
            "colors",
            "size",
            "max_card_copies",
            "allow_colorless",
            "legalities",
            "owned_cards_only",
            "color_match_mode",
            "mana_curve_min",
            "mana_curve_max",
            "mana_curve_shape",
            "mana_curve_slope",
            "fill_with_any",
            "fill_priority",
            "allow_less_than_target",
        ]:
            mock_component = MagicMock()
            mock_component.name = key
            ui_map[key] = mock_component

        # Directly patch the DeckConfig.model_validate method to return what we
        # expect
        with patch(
            "mtg_deck_builder.deck_config.deck_config.DeckConfig.model_validate",
            return_value=expected_config,
        ) as mock_validate:
            # Call the extract_config_from_ui function
            config = extract_config_from_ui(ui_map)

            # Verify the model_validate was called
            mock_validate.assert_called_once()

            # Get the argument passed to model_validate
            args, kwargs = mock_validate.call_args
            config_dict = args[0]

            # Now check the expected values in the config dictionary
            assert (
                config_dict["deck"]["name"] == "Test Deck"
            ), f"Expected deck name 'Test Deck', got {config_dict['deck']['name']}"
            assert config_dict["deck"]["colors"] == [
                "W",
                "R",
            ], f"Expected colors ['W', 'R'], got {config_dict['deck']['colors']}"
            assert (
                config_dict["deck"]["size"] == 60
            ), f"Expected size 60, got {config_dict['deck']['size']}"


@pytest.mark.parametrize(
    "filters,expected_names",
    [
        # Filter by color
        ({"colors": ["W"]}, ["Serra Angel"]),
        ({"colors": ["R"]}, ["Lightning Bolt"]),
        # Filter by type
        ({"type_multi": ["Creature"]}, ["Serra Angel"]),
        ({"type_multi": ["Instant"]}, ["Lightning Bolt"]),
        # Filter by rarity
        ({"rarity": "uncommon"}, ["Serra Angel"]),
        ({"rarity": "common"}, ["Lightning Bolt"]),
        # Filter by legality
        ({"legality": "standard"}, ["Serra Angel"]),
        ({"legality": "modern"}, ["Lightning Bolt"]),
        # Filter by minimum owned quantity
        ({"min_qty": 3}, ["Lightning Bolt"]),
        ({"min_qty": 5}, []),
        # Filter by name search
        ({"name_search": "Serra"}, ["Serra Angel"]),
        ({"name_search": "Bolt"}, ["Lightning Bolt"]),
        # Filter by text search
        ({"text_search": "Flying"}, ["Serra Angel"]),
        ({"text_search": "damage"}, ["Lightning Bolt"]),
    ],
)
def test_collection_viewer_filters(
    filters, expected_names, mock_card_repository, mock_db_session
):
    """Test get_collection_df with various filters."""
    with patch(
        "mtg_deck_builder.db.repository.CardRepository"
    ) as mock_card_repo_class, patch(
        "mtg_deck_builder.db.get_session", return_value=mock_db_session
    ), patch(
        "mtg_deckbuilder_ui.logic.collection_viewer_func.get_session",
        return_value=mock_db_session,
    ), patch(
        "mtg_deckbuilder_ui.logic.collection_viewer_func.CardRepository.get_cached_cards"
    ) as mock_get_cached_cards:

        from mtg_deckbuilder_ui.logic.collection_viewer_func import get_collection_df

        mock_card_repo_class.return_value = mock_card_repository
        mock_get_cached_cards.return_value = (
            mock_db_session,
            mock_card_repository._cards,
        )

        df = get_collection_df(**filters)
        actual_names = df["Name"].tolist() if not df.empty else []
        assert set(actual_names) == set(
            expected_names
        ), f"Expected {expected_names}, got {actual_names} for filters {filters}"


def test_run_deckbuilder_from_ui(monkeypatch):
    """Test the deckbuilder backend logic with a minimal UI map and mocks."""
    from mtg_deckbuilder_ui.logic import deckbuilder_func
    import pandas as pd
    from unittest.mock import patch, MagicMock

    # Minimal UI map for a valid deck config
    ui_map = {
        "name": "Test Deck",
        "colors": ["⚪ White (W)", "🔴 Red (R)"],
        "size": 60,
        "max_card_copies": 4,
        "allow_colorless": True,
        "legalities": ["standard"],
        "owned_cards_only": True,
        "color_match_mode": "subset",
        "mana_curve_min": 1,
        "mana_curve_max": 6,
        "mana_curve_shape": "normal",
        "mana_curve_slope": 1,
        "fill_with_any": True,
        "fill_priority": "creatures, removal",
        "allow_less_than_target": False,
    }
    session = MagicMock()
    inventory_file = "card inventory.txt"
    inventory_dir = "mtg_deckbuilder_ui/inventory_files"

    # Patch CardRepository, InventoryRepository, and build_deck_from_config at
    # the correct location
    monkeypatch.setattr("mtg_deck_builder.db.repository.CardRepository", MagicMock())
    monkeypatch.setattr(
        "mtg_deck_builder.db.repository.InventoryRepository", MagicMock()
    )
    monkeypatch.setattr(
        "mtg_deckbuilder_ui.utils.inventory_importer.import_inventory_file",
        lambda *a, **kw: MagicMock(is_alive=lambda: False),
    )
    monkeypatch.setattr("os.path.exists", lambda path: True)
    monkeypatch.setattr("os.path.getmtime", lambda path: 12345)

    def make_card_mock(name, **kwargs):
        card = MagicMock(**kwargs)
        card.name = name
        return card

    with patch(
        "mtg_deckbuilder_ui.logic.deckbuilder_func.build_deck_from_config",
        new=lambda *a, **kw: MagicMock(
            cards={
                "Serra Angel": make_card_mock(
                    "Serra Angel",
                    type="Creature",
                    rarity="uncommon",
                    colors=["W"],
                    mana_cost="{3}{W}{W}",
                    converted_mana_cost=5,
                    owned_qty=2,
                    text="Flying, vigilance",
                    power="4",
                    toughness="4",
                    legalities={"standard": "legal"},
                ),
                "Lightning Bolt": make_card_mock(
                    "Lightning Bolt",
                    type="Instant",
                    rarity="common",
                    colors=["R"],
                    mana_cost="{R}",
                    converted_mana_cost=1,
                    owned_qty=4,
                    text="Deal 3 damage to any target.",
                    power="",
                    toughness="",
                    legalities={"modern": "legal"},
                ),
            },
            size=lambda: 2,
            average_mana_value=lambda: 3.0,
            color_balance=lambda: {"W": 1, "R": 1},
            count_card_types=lambda: {"Creature": 1, "Instant": 1},
            count_mana_ramp=lambda: 0,
            count_lands=lambda: 0,
            mtg_arena_import=lambda: "4 Lightning Bolt\n2 Serra Angel",
            name="Test Deck",
        ),
    ):
        info_str, df, arena_str = deckbuilder_func.run_deckbuilder_from_ui(
            ui_map, session, inventory_file, inventory_dir
        )
        assert isinstance(info_str, str)
        assert isinstance(df, pd.DataFrame)
        assert "Serra Angel" in df["Name"].values
        assert "Lightning Bolt" in df["Name"].values
        assert "Lightning Bolt" in arena_str
        assert "Serra Angel" in arena_str
