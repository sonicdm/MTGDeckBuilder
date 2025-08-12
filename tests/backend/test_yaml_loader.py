from pathlib import Path
from unittest.mock import MagicMock

import pytest

from mtg_deck_builder.models.deck_config import DeckConfig, DeckMeta, PriorityCardEntry
from mtg_deck_builder.yaml_builder.deck_build_classes import (
    BuildContext,
    DeckBuildContext,
)
from mtg_deck_builder.yaml_builder.helpers.deck_building import _handle_priority_cards
from mtg_deck_builder.yaml_builder.yaml_deckbuilder import (
    build_deck_from_yaml,
    load_yaml_config,
)


def test_yaml_migration_color_mode():
    yaml_text = """
deck:
  name: Test
  colors: [r, g]
  color_mode: subset
"""
    cfg = load_yaml_config(yaml_text)
    assert cfg.deck.color_match_mode == "subset"


def test_invalid_color_match_mode():
    bad_yaml = """
deck:
  color_match_mode: bananas
"""
    with pytest.raises(ValueError):
        load_yaml_config(bad_yaml)


class DeckStub:
    def __init__(self) -> None:
        self.inventory = {}

    def insert_card(self, card, quantity: int = 1) -> None:
        self.inventory[card.name] = self.inventory.get(card.name, 0) + quantity


def test_priority_dedupe_and_warning():
    repo = MagicMock()
    card = MagicMock(name="Opt")
    repo.find_by_name.side_effect = lambda n: card if n == "Opt" else None

    deck_config = DeckConfig(
        deck=DeckMeta(name="Test", colors=["U"]),
        priority_cards=[
            PriorityCardEntry(name="Opt", min_copies=3),
            PriorityCardEntry(name="Opt", min_copies=4),
            PriorityCardEntry(name="Missing", min_copies=2),
        ],
    )
    deck = DeckStub()
    ctx = DeckBuildContext(config=deck_config, deck=deck, summary_repo=repo)
    build_ctx = BuildContext(
        deck_config=deck_config, summary_repo=repo, deck_build_context=ctx
    )
    _handle_priority_cards(build_ctx)
    assert ctx.get_card_quantity("Opt") == 4
    assert any(
        log.get("warning") == "priority_missing:Missing" for log in build_ctx.build_log
    )


def test_deterministic_build():
    repo = MagicMock()
    card = MagicMock()
    card.name = "Shock"
    card.type_line = ""
    repo.find_by_name.return_value = card

    yaml_text = """
deck:
  name: Seeded
  colors: [R]
  size: 60
  max_card_copies: 4
priority_cards:
  - name: Shock
    min_copies: 2
"""
    deck1 = build_deck_from_yaml(yaml_text, repo)
    deck2 = build_deck_from_yaml(yaml_text, repo)
    assert deck1 and deck2
    assert deck1.inventory == deck2.inventory
