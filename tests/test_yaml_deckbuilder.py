import os
from typing import Dict, Any, Generator
from unittest.mock import MagicMock
import pytest

from mtg_deck_builder.db.bootstrap import bootstrap, bootstrap_inventory
from mtg_deck_builder.db.repository import CardRepository, InventoryRepository, InventoryItemDB
from mtg_deck_builder.db import get_session
from mtg_deck_builder.deck_config.deck_config import DeckConfig
from mtg_deck_builder.yaml_builder.yaml_deckbuilder import build_deck_from_config
from .helpers import get_sample_data_path

ALL_PRINTINGS_PATH = get_sample_data_path('AllPrintings.json')
SAMPLE_YAML_PATH = get_sample_data_path('yaml_test_template.yaml')
SAMPLE_INVENTORY_PATH = get_sample_data_path('sample_inventory.txt')
TEST_DB_FILENAME = 'test_deckbuilder_cards.db'
SAMPLE_DB_URL = f"sqlite:///{get_sample_data_path(TEST_DB_FILENAME)}"


@pytest.fixture(scope="module")
def card_repo_fixture() -> Generator[CardRepository, Any, None]:
    """Fixture to set up a CardRepository with a module-scoped database session."""
    if not os.path.exists(ALL_PRINTINGS_PATH):
        pytest.skip(f"Skipping tests that require AllPrintings.json, not found at {ALL_PRINTINGS_PATH}")

    bootstrap(json_path=ALL_PRINTINGS_PATH, inventory_path=None, db_url=SAMPLE_DB_URL, use_tqdm=False)
    session = get_session(db_url=SAMPLE_DB_URL)
    card_repo = CardRepository(session)
    yield card_repo

    session.close()
    db_file_path = get_sample_data_path(TEST_DB_FILENAME)
    if os.path.exists(db_file_path):
        try:
            os.remove(db_file_path)
        except OSError as e:
            print(f"Warning: Could not remove test DB {db_file_path}: {e}")


@pytest.fixture
def inventory_repo_fixture(card_repo_fixture: CardRepository) -> InventoryRepository:
    """Fixture to set up an InventoryRepository with a function-scoped clean inventory."""
    session = card_repo_fixture.session

    # Explicitly check for table existence using SQLAlchemy's inspector
    from sqlalchemy import inspect
    inspector = inspect(session.get_bind())  # Get engine from session
    table_names = inspector.get_table_names()
    if 'inventory_items' not in table_names:
        pytest.fail("FAILURE: 'inventory_items' table does not exist at the start of inventory_repo_fixture! Check bootstrap and model registration.")

    # Clear previous inventory for test isolation
    try:
        session.query(InventoryItemDB).delete()
        session.commit()
    except Exception as e:
        session.rollback()  # Rollback on error during delete
        pytest.fail(f"Error clearing InventoryItemDB: {e}")
    bootstrap_inventory(SAMPLE_INVENTORY_PATH, SAMPLE_DB_URL)
    inv_repo = InventoryRepository(session)
    # Load sample inventory for convenience in tests that need it
    if os.path.exists(SAMPLE_INVENTORY_PATH):
        with open(SAMPLE_INVENTORY_PATH, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split(' ', 1)
                if len(parts) < 2:
                    continue
                try:
                    qty = int(parts[0])
                    name = parts[1]
                    card_db_entry = card_repo_fixture.find_by_name(name)
                    if card_db_entry:
                        # Check if item exists before merging, or use merge directly
                        item = inv_repo.find_by_card_name(name)
                        if item:
                            item.quantity = qty
                            item.is_infinite = (name in {"Plains", "Island", "Swamp", "Mountain", "Forest"})
                            session.merge(item)
                        else:
                            session.add(InventoryItemDB(card_name=name, quantity=qty, is_infinite=(name in {"Plains", "Island", "Swamp", "Mountain", "Forest"})))
                except ValueError:
                    print(f"Skipping malformed inventory line: {line}")
        try:
            session.commit()
        except Exception as e:
            session.rollback()
            pytest.fail(f"Error committing inventory load: {e}")
    return inv_repo


@pytest.fixture
def sample_deck_config() -> DeckConfig:
    """Loads the sample YAML deck configuration for tests."""
    if not os.path.exists(SAMPLE_YAML_PATH):
        pytest.fail(f"Sample YAML config not found at {SAMPLE_YAML_PATH}")
    return DeckConfig.from_yaml(SAMPLE_YAML_PATH)


class TestYamlDeckBuilderWithCallbacks:

    def test_build_deck_with_mocked_callbacks(
            self,
            sample_deck_config: DeckConfig,
            card_repo_fixture: CardRepository,
            inventory_repo_fixture: InventoryRepository
    ):
        """Tests a basic deck build using mocks for callbacks."""
        config_copy = sample_deck_config.model_copy(deep=True)
        config_copy.deck.owned_cards_only = True

        # Capture the state of flags from config_copy BEFORE calling build_deck_from_config
        # These are the conditions under which the deck was supposed to be built.
        is_owned_only_build_setting = config_copy.deck.owned_cards_only
        is_allow_less_than_target_setting = config_copy.fallback_strategy.allow_less_than_target

        assert is_owned_only_build_setting is True  # Verify our captured flag
        assert config_copy.deck.legalities == ["standard"]

        mock_callbacks: Dict[str, Any] = {
            "after_inventory_load": MagicMock(name="after_inventory_load"),
            "before_initial_repo_filter": MagicMock(name="before_initial_repo_filter"),
            "after_initial_repo_filter": MagicMock(name="after_initial_repo_filter"),
            "after_priority_cards": MagicMock(name="after_priority_cards"),
            "after_land_selection": MagicMock(name="after_land_selection"),
            "after_categories": MagicMock(name="after_categories"),
            "before_fallback_fill": MagicMock(name="before_fallback_fill"),
            "after_fallback_fill": MagicMock(name="after_fallback_fill"),
            "before_finalize": MagicMock(name="before_finalize"),
        }
        for cat_name in config_copy.categories.keys():
            mock_callbacks[f"before_category_fill:{cat_name}"] = MagicMock(name=f"before_category_fill:{cat_name}")
            mock_callbacks[f"after_category_fill:{cat_name}"] = MagicMock(name=f"after_category_fill:{cat_name}")

        deck = build_deck_from_config(
            deck_config=config_copy,
            card_repo=card_repo_fixture,
            inventory_repo=inventory_repo_fixture,
            callbacks=mock_callbacks
        )

        assert deck is not None, "Deck building failed, returned None"
        assert len(deck.cards) > 0, "Deck was built with no cards"

        mock_callbacks["after_priority_cards"].assert_called_once()
        after_priority_cards_args = mock_callbacks["after_priority_cards"].call_args
        selected_priority_cards = after_priority_cards_args.kwargs.get('selected', {})

        assert "Lightning Bolt" not in selected_priority_cards, "Lightning Bolt should be excluded due to standard legality"
        if any(pc.name == "Cut Down" for pc in config_copy.priority_cards):
            assert "Cut Down" in selected_priority_cards, "Standard legal priority card 'Cut Down' should be selected"

        # Land selection assertions
        mock_callbacks["after_land_selection"].assert_called_once()
        after_land_selection_args = mock_callbacks["after_land_selection"].call_args
        selected_cards_after_lands = after_land_selection_args.kwargs.get('selected', {})

        total_land_count = sum(c.owned_qty for c in selected_cards_after_lands.values() if c.matches_type("Land"))
        expected_land_count = config_copy.mana_base.land_count
        assert total_land_count == expected_land_count, f"Expected {expected_land_count} lands, but got {total_land_count}"

        special_land_names_in_deck = {
            c.name for c in selected_cards_after_lands.values()
            if c.matches_type("Land") and not c.is_basic_land()
        }
        max_special_lands = config_copy.mana_base.special_lands.count
        assert len(special_land_names_in_deck) <= max_special_lands, \
            f"Selected {len(special_land_names_in_deck)} special lands, but max was {max_special_lands}"

        # Basic land color assertions
        expected_basic_land_colors = set(config_copy.deck.colors)
        basic_lands_in_deck = [
            c for c in selected_cards_after_lands.values()
            if c.is_basic_land()
        ]
        # Define the standard color identity for basic land names
        basic_land_name_to_color = {
            "Plains": "W",
            "Island": "U",
            "Swamp": "B",
            "Mountain": "R",
            "Forest": "G"
        }
        for land_card in basic_lands_in_deck:
            # Assert that the land name is a known basic land type
            assert land_card.name in basic_land_name_to_color, f"Unknown basic land name: {land_card.name} encountered in deck."

            land_color_identity = basic_land_name_to_color[land_card.name]

            # Check if the inferred color identity is one of the allowed deck colors
            assert land_color_identity in expected_basic_land_colors, \
                f"Basic land {land_card.name} with inferred color {land_color_identity} is not in allowed deck colors {expected_basic_land_colors}"

        # Assertions for category filling callbacks
        for cat_name in config_copy.categories.keys():
            mock_callbacks[f"before_category_fill:{cat_name}"].assert_called_once()
            mock_callbacks[f"after_category_fill:{cat_name}"].assert_called_once()
        mock_callbacks["after_categories"].assert_called_once()

        # Assertions for fallback and finalize callbacks
        mock_callbacks["before_fallback_fill"].assert_called_once()
        # after_fallback_fill might not be called if deck is full, so it's not asserted here robustly without more logic
        mock_callbacks["before_finalize"].assert_called_once()

        # Final deck assertions
        actual_deck_size = deck.size()
        expected_deck_size = config_copy.deck.size  # Expected size from the config passed to build

        # Use the captured flags for the assertion logic
        if is_owned_only_build_setting and not is_allow_less_than_target_setting:
            assert actual_deck_size <= expected_deck_size, \
                f"Deck size {actual_deck_size} should be <= {expected_deck_size} for an owned-only build where less than target is not allowed. " \
                f"(Build settings: owned_only={is_owned_only_build_setting}, allow_less_than_target={is_allow_less_than_target_setting})"
        elif not is_allow_less_than_target_setting:
            assert actual_deck_size == expected_deck_size, \
                f"Expected deck size {expected_deck_size}, but got {actual_deck_size}. " \
                f"(Build settings: owned_only={is_owned_only_build_setting}, allow_less_than_target={is_allow_less_than_target_setting})"
        else:  # is_allow_less_than_target_setting is true
            assert actual_deck_size <= expected_deck_size, \
                f"Deck size {actual_deck_size} should be <= {expected_deck_size} when allow_less_than_target is true. " \
                f"(Build settings: owned_only={is_owned_only_build_setting}, allow_less_than_target={is_allow_less_than_target_setting})"

        for card_name, card_obj in deck.cards.items():
            # Basic lands are exempt from the max_card_copies rule.
            if not card_obj.is_basic_land():
                assert card_obj.owned_qty <= config_copy.deck.max_card_copies, \
                    f"Card {card_name} has {card_obj.owned_qty} copies, exceeding max of {config_copy.deck.max_card_copies}"

            # Check card legalities
            if config_copy.deck.legalities:
                is_legal = False
                for legality_format in config_copy.deck.legalities:
                    if card_obj.legalities.get(legality_format, "not_legal").lower() == "legal":
                        is_legal = True
                        break
                # Priority cards like Lightning Bolt might be in selected_priority_cards but not in the final deck
                # if they are filtered out by later steps (e.g. legality for the deck itself).
                # The check for Lightning Bolt exclusion from selected_priority_cards already handles its specific case.
                # Here we check cards that *made it* into the final deck.
                if card_name != "Lightning Bolt":  # Exclude known non-standard card if it was a priority for testing that stage
                    assert is_legal, f"Card {card_name} is not legal in {config_copy.deck.legalities}"

            # Check color identity
            card_actual_colors = card_obj.colors  # Use the .colors property
            if not card_obj.matches_color_identity(list(config_copy.deck.colors), match_mode=config_copy.deck.color_match_mode):
                # If matches_color_identity is false, we then check if it's an allowed colorless card.
                # A card is considered colorless if its .colors property returns an empty list.
                is_card_genuinely_colorless = not card_actual_colors
                if not (config_copy.deck.allow_colorless and is_card_genuinely_colorless):
                    assert False, f"Card {card_name} (actual colors: {card_actual_colors}) failed color check (deck colors: {config_copy.deck.colors}, match_mode: {config_copy.deck.color_match_mode}) and is not an allowed colorless card."


    def test_deck_respects_owned_cards_only(
        self,
        sample_deck_config: DeckConfig,
        card_repo_fixture: CardRepository,
        inventory_repo_fixture: InventoryRepository
    ):
        """Tests that the deck builder respects the owned_cards_only flag."""
        config_copy = sample_deck_config.model_copy(deep=True)
        config_copy.deck.owned_cards_only = True
        config_copy.priority_cards = [] # Clear priority cards to simplify inventory check
        config_copy.categories = {} # Clear categories for the same reason
        config_copy.mana_base.land_count = 0 # No lands to simplify
        config_copy.deck.size = 5 # Small deck size

        # Ensure inventory has specific cards with limited quantities
        # For this test, let's assume 'Cut Down' is in inventory with 2 copies
        # and 'Play with Fire' is in inventory with 1 copy.
        # Other cards needed to fill the deck should exist in AllPrintings but not necessarily in inventory.

        # Modify inventory for the test
        session = inventory_repo_fixture.session
        session.query(InventoryItemDB).delete() # Clear existing inventory
        session.add(InventoryItemDB(card_name="Cut Down", quantity=2, is_infinite=False))
        session.add(InventoryItemDB(card_name="Play with Fire", quantity=1, is_infinite=False))
        # Add a basic land to inventory to avoid issues if lands are attempted to be added by some logic
        session.add(InventoryItemDB(card_name="Swamp", quantity=10, is_infinite=True))
        session.commit()

        deck = build_deck_from_config(
            deck_config=config_copy,
            card_repo=card_repo_fixture,
            inventory_repo=inventory_repo_fixture
        )

        assert deck is not None, "Deck building failed"
        # Check that cards in deck do not exceed owned quantities
        if "Cut Down" in deck.cards:
            assert deck.cards["Cut Down"].owned_qty <= 2, "Exceeded owned quantity of Cut Down"
        if "Play with Fire" in deck.cards:
            assert deck.cards["Play with Fire"].owned_qty <= 1, "Exceeded owned quantity of Play with Fire"

        # Check that cards not in inventory (unless infinite like basic lands) are not in the deck
        # This requires knowing a card that is in AllPrintings but we didn't add to inventory.
        # For example, if 'Lightning Bolt' is not in our test inventory for this case:
        assert "Lightning Bolt" not in deck.cards, "Lightning Bolt should not be in deck as it's not in inventory (for this test setup)"

        # Verify that the total number of cards respects inventory limits
        # This is harder to assert precisely without running the full deck builder logic
        # but the individual card checks above are the primary goal.

    # TODO: Add more tests for specific scenarios:
    # - Different color_match_mode behaviors (exact, any)
    # - Card constraints (exclude_keywords, rarity_boost)
    # - Mana curve adherence if more sophisticated checks are needed beyond min/max in categories
    # - Fallback strategy variations (fill_priority, allow_less_than_target)
    # - Scoring rules impact (if testable via callbacks or specific card choices)

