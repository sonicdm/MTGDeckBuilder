"""Shared validation utilities.

This module provides functions for:
- Validating card color identity
- Checking card legalities
- Verifying card ownership
"""

import logging
from typing import List
from mtg_deck_builder.db.mtgjson_models.cards import MTGJSONSummaryCard

logger = logging.getLogger(__name__)


def _check_color_identity(
    card: MTGJSONSummaryCard,
    colors: List[str],
    color_match_mode: str,
) -> bool:
    """Check if a card's color identity matches the deck's colors.

    Args:
        card: Card to check
        colors: List of allowed colors
        color_match_mode: How to match colors ("exact", "subset", or "superset")

    Returns:
        True if card's colors match the requirements
    """
    if not colors:
        return True

    card_colors = set(getattr(card, "color_identity_list", []) or [])
    deck_colors = set(colors)

    if color_match_mode == "exact":
        return card_colors == deck_colors
    elif color_match_mode == "subset":
        return card_colors.issubset(deck_colors)
    else:  # superset
        return card_colors.issuperset(deck_colors)


def _check_ownership(
    card: MTGJSONSummaryCard,
) -> bool:
    """Check if a card is owned.

    Args:
        card: Card to check

    Returns:
        True if card is owned
    """
    owned_qty = getattr(card, "owned_qty", 0) or 0
    return bool(owned_qty > 0)
