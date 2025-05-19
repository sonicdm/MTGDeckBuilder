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

TEST_SAMPLE = get_sample_data_path("b-grave-recursion.yaml")


@pytest.fixture
def sample_deck_config():
    assert os.path.exists(TEST_SAMPLE), f"Missing sample file: {TEST_SAMPLE}"
    return DeckConfig.from_yaml(TEST_SAMPLE)


def test_basic_build_runs(sample_deck_config, test_repositories):
    card_repo, inventory_repo = test_repositories
    deck = build_deck_from_config(sample_deck_config, card_repo, inventory_repo)
    assert deck is not None
    assert sum(c.owned_qty for c in deck.cards.values()) == sample_deck_config.deck.get("size", 60)


def test_callbacks_no_commons_allowed(sample_deck_config, test_repositories):
    card_repo, inventory_repo = test_repositories
    callbacks = {"after_fallback_fill": assert_no_commons}

    with pytest.raises(AssertionError, match="Common cards found"):
        build_deck_from_config(sample_deck_config, card_repo, inventory_repo, callbacks=callbacks)


def test_limit_card_copies_enforced(sample_deck_config, test_repositories):
    card_repo, inventory_repo = test_repositories
    callbacks = {"before_finalize": limit_card_copies(max_allowed=4)}
    deck = build_deck_from_config(sample_deck_config, card_repo, inventory_repo, callbacks=callbacks)

    for card in deck.cards.values():
        assert card.owned_qty <= 4


def test_require_specific_card(sample_deck_config, test_repositories):
    card_repo, inventory_repo = test_repositories
    callbacks = {
        "after_category_fill:removal": ensure_card_present("Fatal Push", min_copies=1)
    }

    with pytest.raises(AssertionError, match="Required card missing"):
        build_deck_from_config(sample_deck_config, card_repo, inventory_repo, callbacks=callbacks)


def test_debug_log(capsys, sample_deck_config, test_repositories):
    card_repo, inventory_repo = test_repositories
    callbacks = {
        "after_priority_card_select": log_summary,
        "after_special_lands": log_special_lands,
    }

    build_deck_from_config(sample_deck_config, card_repo, inventory_repo, callbacks=callbacks)
    output = capsys.readouterr().out
    assert "Deck so far" in output
    assert "Special lands" in output
