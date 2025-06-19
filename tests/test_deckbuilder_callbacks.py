import os
import pytest
from unittest.mock import MagicMock

from mtg_deck_builder.deck_config import DeckConfig
from mtg_deck_builder.yaml_builder.yaml_deckbuilder import build_deck_from_config
from mtg_deck_builder.yaml_builder.callbacks import (
    assert_no_commons,
    limit_card_copies,
    ensure_card_present,
    log_summary,
    log_special_lands,
)
from tests.helpers import get_sample_data_path
from tests.fixtures import DummyCard

TEST_SAMPLE = get_sample_data_path("yaml_test_template.yaml")  # Deck colors: [B, R]


@pytest.fixture
def sample_deck_config_fixture():
    assert os.path.exists(TEST_SAMPLE), f"Missing sample file: {TEST_SAMPLE}"
    return DeckConfig.from_yaml(TEST_SAMPLE)


# Helper to create basic lands for B/R config and set up common mock behaviors
def setup_mock_repos_for_br_deck(mock_card_repo, mock_inventory_repo, test_specific_cards=None):
    test_specific_cards = test_specific_cards or []

    # Define all 5 basic lands, REMOVING type kwarg
    plains = DummyCard("Plains", text="Basic Land - Plains", rarity="common")
    island = DummyCard("Island", text="Basic Land - Island", rarity="common")
    swamp = DummyCard("Swamp", text="Basic Land - Swamp", rarity="common", colors=['B'])  # B/R deck
    mountain = DummyCard("Mountain", text="Basic Land - Mountain", rarity="common", colors=['R'])  # B/R deck
    forest = DummyCard("Forest", text="Basic Land - Forest", rarity="common")

    basic_lands_for_general_pool = [swamp, mountain]
    all_available_cards = test_specific_cards + basic_lands_for_general_pool

    def find_by_name_side_effect(name_arg):
        if name_arg == "Plains": return plains
        if name_arg == "Island": return island
        if name_arg == "Swamp": return swamp
        if name_arg == "Mountain": return mountain
        if name_arg == "Forest": return forest
        return next((c for c in test_specific_cards if c.name == name_arg), None)

    mock_card_repo.filter_cards.return_value = mock_card_repo
    mock_card_repo.get_all_cards.return_value = all_available_cards
    mock_card_repo.__iter__.return_value = iter(all_available_cards)
    mock_card_repo.find_by_name.side_effect = find_by_name_side_effect

    # Inventory mock for owned_cards_only: true
    def inventory_side_effect(card_name_arg):
        if card_name_arg in ["Plains", "Island", "Swamp", "Mountain", "Forest"]:
            return (100, True)  # Basic lands are effectively infinite and owned

        card_in_test_specific = next((c for c in test_specific_cards if c.name == card_name_arg), None)
        if card_in_test_specific:
            return (card_in_test_specific.owned_qty, False)  # Use DummyCard's own qty, not infinite
        return (0, False)  # Default: card not in inventory if not specified

    mock_inventory_repo.get_inventory_for_card.side_effect = inventory_side_effect


def test_basic_build_runs(sample_deck_config_fixture):
    mock_card_repo = MagicMock()
    mock_inventory_repo = MagicMock()

    num_non_lands = sample_deck_config_fixture.deck.size - sample_deck_config_fixture.mana_base.land_count
    # Ensure these dummy cards have colors consistent with the deck if color filtering is strict
    any_cards_for_deck_fill = [DummyCard(f"AnyCard{i}", owned_qty=1, colors=['B']) for i in range(num_non_lands)]

    setup_mock_repos_for_br_deck(mock_card_repo, mock_inventory_repo, any_cards_for_deck_fill)

    deck = build_deck_from_config(sample_deck_config_fixture, mock_card_repo, mock_inventory_repo)
    assert deck is not None
    assert sum(c.owned_qty for c in deck.cards.values()) == sample_deck_config_fixture.deck.size


def test_callbacks_no_commons_allowed(sample_deck_config_fixture, caplog):
    mock_card_repo = MagicMock()
    mock_inventory_repo = MagicMock()

    common_card = DummyCard("Common Card", rarity="common")  # Non-basic common
    uncommon_card = DummyCard("Uncommon Card", rarity="uncommon")
    test_cards = [common_card, uncommon_card]
    setup_mock_repos_for_br_deck(mock_card_repo, mock_inventory_repo, test_cards)

    callbacks = {"after_fallback_fill": assert_no_commons}
    with caplog.at_level("WARNING"):
        build_deck_from_config(sample_deck_config_fixture, mock_card_repo, mock_inventory_repo, callbacks=callbacks)

    # Basic lands (Swamp, Mountain) are common but should be ignored by assert_no_commons.
    # The warning should only trigger for non-basic common cards.
    assert any("Common cards found: Common Card" in record.message for record in caplog.records)
    assert not any("Common cards found: Swamp" in record.message for record in caplog.records)
    assert not any("Common cards found: Mountain" in record.message for record in caplog.records)


def test_limit_card_copies_enforced(sample_deck_config_fixture):
    mock_card_repo = MagicMock()
    mock_inventory_repo = MagicMock()

    card_needing_limit = DummyCard("Limited Card", owned_qty=10)
    # REMOVING type kwarg from another_land_card if it was added
    another_land_card = DummyCard("Forest of Elders", owned_qty=5, text="Non-basic land")
    test_cards = [card_needing_limit, another_land_card]
    setup_mock_repos_for_br_deck(mock_card_repo, mock_inventory_repo, test_cards)

    callbacks = {"before_finalize": limit_card_copies(max_allowed=4)}
    deck = build_deck_from_config(sample_deck_config_fixture, mock_card_repo, mock_inventory_repo, callbacks=callbacks)

    for card_obj in deck.cards.values():
        # Use the DummyCard's is_basic_land method for checking
        is_deck_basic_land = card_obj.is_basic_land() and card_obj.name in ["Swamp", "Mountain"]
        if is_deck_basic_land:
            continue
        assert card_obj.owned_qty <= 4, f"{card_obj.name} has qty {card_obj.owned_qty}, expected <= 4"


def test_require_specific_card(sample_deck_config_fixture, caplog):
    # Scenario 1: Card is missing
    mock_card_repo_s1 = MagicMock()
    mock_inventory_repo_s1 = MagicMock()
    other_card = DummyCard("Other Card")
    setup_mock_repos_for_br_deck(mock_card_repo_s1, mock_inventory_repo_s1, [other_card])
    # find_by_name from setup_mock_repos_for_br_deck will return None for "Fatal Push"

    callbacks_s1 = {"after_category_fill:removal": ensure_card_present("Fatal Push", min_copies=1)}
    with caplog.at_level("WARNING"):
        build_deck_from_config(sample_deck_config_fixture, mock_card_repo_s1, mock_inventory_repo_s1, callbacks=callbacks_s1)
    assert any("Required card missing: Fatal Push" in record.message for record in caplog.records)

    # Scenario 2: Card is present
    caplog.clear()
    mock_card_repo_s2 = MagicMock()
    mock_inventory_repo_s2 = MagicMock()
    # Corrected: DummyCard takes name as first positional argument
    fatal_push_card = DummyCard("Fatal Push", owned_qty=1)
    setup_mock_repos_for_br_deck(mock_card_repo_s2, mock_inventory_repo_s2, [fatal_push_card, other_card])
    # find_by_name from setup_mock_repos_for_br_deck will now find fatal_push_card

    callbacks_s2 = {"after_category_fill:removal": ensure_card_present("Fatal Push", min_copies=1)}
    build_deck_from_config(sample_deck_config_fixture, mock_card_repo_s2, mock_inventory_repo_s2, callbacks=callbacks_s2)
    assert not any("Required card missing: Fatal Push" in record.message for record in caplog.records)


def test_debug_log(sample_deck_config_fixture, caplog):
    mock_card_repo = MagicMock()
    mock_inventory_repo = MagicMock()

    # Corrected: DummyCard takes name as first positional argument
    card1 = DummyCard("Card One For Log")
    card2 = DummyCard("Card Two For Log")
    test_cards = [card1, card2]
    setup_mock_repos_for_br_deck(mock_card_repo, mock_inventory_repo, test_cards)

    callbacks = {
        "after_final_deck_build": log_summary,
        "after_special_lands": log_special_lands,
    }
    with caplog.at_level("INFO"):
        build_deck_from_config(sample_deck_config_fixture, mock_card_repo, mock_inventory_repo, callbacks=callbacks)

    assert any("Deck so far" in record.getMessage() for record in caplog.records)
    assert any("Special lands" in record.getMessage() for record in caplog.records)
