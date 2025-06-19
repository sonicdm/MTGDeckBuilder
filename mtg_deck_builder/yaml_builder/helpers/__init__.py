"""Helper functions for the YAML deck builder.

This package contains helper functions organized by functionality:
- card_scoring: Card scoring and evaluation
- category_handling: Category filling and management
- deck_building: Core deck building process
- fallback: Fallback strategy handling
- mana_curve: Mana curve and symbol handling
- validation: Shared validation utilities
"""

from .card_scoring import score_card
from .category_handling import (
    category_matches,
    _fill_categories,
    _prune_overfilled_categories,
)
from .deck_building import (
    _handle_priority_cards,
    _handle_basic_lands,
    _handle_special_lands,
    _finalize_deck,
    _log_deck_composition,
    _filter_summary_repository,
    _apply_card_constraints,
)
from .fallback import _handle_fallback_strategy
from .mana_curve import generate_target_curve
from .validation import _check_color_identity, _check_legalities, _check_ownership

__all__ = [
    "score_card",
    "category_matches",
    "_fill_categories",
    "_prune_overfilled_categories",
    "_handle_priority_cards",
    "_handle_basic_lands",
    "_handle_special_lands",
    "_finalize_deck",
    "_log_deck_composition",
    "_filter_summary_repository",
    "_apply_card_constraints",
    "_handle_fallback_strategy",
    "generate_target_curve",
    "_check_color_identity",
    "_check_legalities",
    "_check_ownership",
]
