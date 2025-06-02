import os
import pytest

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

TEST_SAMPLE = get_sample_data_path("yaml_test_template.yaml")


@pytest.fixture
def sample_deck_config():
    assert os.path.exists(TEST_SAMPLE), f"Missing sample file: {TEST_SAMPLE}"
    return DeckConfig.from_yaml(TEST_SAMPLE)


def test_basic_build_runs(sample_deck_config, test_repositories):
    card_repo, inventory_repo = test_repositories
    deck = build_deck_from_config(sample_deck_config, card_repo, inventory_repo)
    assert deck is not None
    assert sum(c.owned_qty for c in deck.cards.values()) == sample_deck_config.deck.size


def test_callbacks_no_commons_allowed(sample_deck_config, test_repositories, caplog):
    card_repo, inventory_repo = test_repositories
    callbacks = {"after_fallback_fill": assert_no_commons}
    with caplog.at_level("WARNING"):
        build_deck_from_config(sample_deck_config, card_repo, inventory_repo, callbacks=callbacks)
    assert any("Common cards found" in record.message for record in caplog.records)


def test_limit_card_copies_enforced(sample_deck_config, test_repositories):
    card_repo, inventory_repo = test_repositories
    callbacks = {"before_finalize": limit_card_copies(max_allowed=4)}
    deck = build_deck_from_config(sample_deck_config, card_repo, inventory_repo, callbacks=callbacks)

    for card in deck.cards.values():
        # Allow unlimited copies for basic lands
        if hasattr(card, "type") and card.type and "basic land" in card.type.lower():
            continue
        assert card.owned_qty <= 4


def test_require_specific_card(sample_deck_config, test_repositories, caplog):
    card_repo, inventory_repo = test_repositories
    callbacks = {
        "after_category_fill:removal": ensure_card_present("Fatal Push", min_copies=1)
    }
    with caplog.at_level("WARNING"):
        build_deck_from_config(sample_deck_config, card_repo, inventory_repo, callbacks=callbacks)
    assert any("Required card missing" in record.message for record in caplog.records)


def test_debug_log(sample_deck_config, test_repositories, caplog):
    card_repo, inventory_repo = test_repositories
    callbacks = {
        "after_priority_card_select": log_summary,
        "after_special_lands": log_special_lands,
    }
    with caplog.at_level("INFO"):
        build_deck_from_config(sample_deck_config, card_repo, inventory_repo, callbacks=callbacks)
    assert any("Deck so far" in record.getMessage() for record in caplog.records)
    assert any("Special lands" in record.getMessage() for record in caplog.records)
