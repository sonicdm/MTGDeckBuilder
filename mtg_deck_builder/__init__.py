"""MTG Deck Builder library public API.

This package provides deck building, analysis, Arena import/export,
and snapshot utilities. Keep web/UI code out of this namespace.
"""

from .db import get_engine, get_session, get_card_types, get_keywords
from .db.repository import SummaryCardRepository
from .models.deck import Deck
from .models.deck_analyzer import DeckAnalyzer
from .models.deck_exporter import DeckExporter
from .models.deck_config import DeckConfig
from .yaml_builder.yaml_deckbuilder import (
    build_deck_from_yaml,
    build_deck_from_config,
    load_yaml_config,
)
from .arena_io import (
    ArenaParseResult,
    ResolutionReport,
    parse_arena_export_text,
    build_deck_from_arena,
    deck_to_arena,
)
from .snapshot_io import (
    SNAPSHOT_VERSION,
    deck_to_snapshot,
    save_snapshot,
    load_snapshot,
    reconstruct_deck_from_snapshot,
)

__all__ = [
    "get_engine",
    "get_session",
    "get_card_types",
    "get_keywords",
    "SummaryCardRepository",
    "Deck",
    "DeckAnalyzer",
    "DeckExporter",
    "DeckConfig",
    "build_deck_from_yaml",
    "build_deck_from_config",
    "load_yaml_config",
    "ArenaParseResult",
    "ResolutionReport",
    "parse_arena_export_text",
    "build_deck_from_arena",
    "deck_to_arena",
    "SNAPSHOT_VERSION",
    "deck_to_snapshot",
    "save_snapshot",
    "load_snapshot",
    "reconstruct_deck_from_snapshot",
]
