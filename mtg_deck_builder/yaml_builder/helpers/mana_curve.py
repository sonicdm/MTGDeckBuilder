"""Mana curve handling functions.

This module provides functions for:
- Generating target mana curves
- Handling mana curve requirements
- Computing mana symbol distribution
"""

import logging
from typing import Dict, Optional
from mtg_deck_builder.yaml_builder.deck_build_classes import BuildContext
from mtg_deck_builder.models.deck_config import ManaCurveMeta

logger = logging.getLogger(__name__)


def generate_target_curve(
    min_mv: int,
    max_mv: int,
    total_cards: int,
    curve_shape: str = "linear",
    curve_slope: str = "steep",
) -> Dict[int, int]:
    """Generate a target mana curve based on configuration.

    Args:
        min_mv: Minimum mana value
        max_mv: Maximum mana value
        total_cards: Total number of cards to distribute
        curve_shape: Shape of the curve ("linear", "bell", "inverse", or "flat")
        curve_slope: Slope of the curve ("steep" or "gentle")

    Returns:
        Dictionary mapping mana values to target card counts
    """
    curve: Dict[int, int] = {}

    # Number of distinct mana values
    span = max_mv - min_mv + 1

    # Generate relative weights based on curve shape
    weights = []
    if curve_shape == "linear":
        weights = [span - (mv - min_mv) for mv in range(min_mv, max_mv + 1)]
    elif curve_shape == "inverse":
        weights = [1 + (mv - min_mv) for mv in range(min_mv, max_mv + 1)]
    elif curve_shape == "flat":
        weights = [1 for _ in range(span)]
    elif curve_shape == "bell":
        mid = (min_mv + max_mv) / 2
        for mv in range(min_mv, max_mv + 1):
            distance = abs(mv - mid)
            weights.append(span - distance)
    else:
        # Fallback to linear distribution
        weights = [span - (mv - min_mv) for mv in range(min_mv, max_mv + 1)]

    total_weight = sum(weights)
    allocated = 0
    for mv, weight in zip(range(min_mv, max_mv + 1), weights):
        count = int(round((weight / total_weight) * total_cards))
        curve[mv] = count
        allocated += count

    # Adjust for rounding errors
    diff = total_cards - allocated
    idx = 0
    values = list(range(min_mv, max_mv + 1))
    while diff > 0:
        curve[values[idx % span]] += 1
        diff -= 1
        idx += 1
    while diff < 0:
        mv = values[idx % span]
        if curve[mv] > 0:
            curve[mv] -= 1
            diff += 1
        idx += 1

    return curve


def _handle_mana_curve(
    build_context: BuildContext,
) -> None:
    """Handle mana curve requirements.

    Args:
        build_context: Build context containing deck config and card repository
    """
    logger.info("Handling mana curve requirements...")
    config = build_context.deck_config

    # Get configuration values
    mana_curve = config.deck.mana_curve
    if not mana_curve:
        logger.info("No mana curve configuration")
        return

    # Generate target curve
    target_curve = generate_target_curve(
        mana_curve.min,
        mana_curve.max,
        config.deck.size,
        mana_curve.curve_shape,
        mana_curve.curve_slope,
    )
    logger.info(f"Target mana curve: {target_curve}")

    # Store in context
    if build_context.deck_build_context:
        build_context.deck_build_context.meta["target_curve"] = target_curve


def _compute_mana_symbols(
    build_context: BuildContext,
) -> None:
    """Compute mana symbol distribution across the finalized spell pool.

    Args:
        build_context: Build context containing deck config and card repository
    """
    logger.info("Computing mana symbol distribution...")
    if not build_context.deck_build_context:
        return

    context = build_context.deck_build_context

    # Initialize symbol counts
    symbol_counts = {}
    total_symbols = 0

    # Count symbols in each card
    for card in context.cards:
        if "Land" in (getattr(card.card, "types", []) or []):
            continue

        # Get mana cost
        mana_cost = getattr(card.card, "mana_cost", "") or ""
        if not mana_cost:
            continue

        # Count each symbol
        for symbol in mana_cost.split("{"):
            if not symbol:
                continue
            symbol = symbol.strip("}")
            if symbol in ["W", "U", "B", "R", "G"]:
                symbol_counts[symbol] = symbol_counts.get(symbol, 0) + card.quantity
                total_symbols += card.quantity

    # Store in context
    context.meta["mana_symbols"] = symbol_counts
    context.meta["total_symbols"] = total_symbols

    # Log distribution
    if total_symbols > 0:
        logger.info("Mana symbol distribution:")
        for symbol, count in symbol_counts.items():
            percentage = (count / total_symbols) * 100
            logger.info(f"  {symbol}: {count} ({percentage:.1f}%)")
    else:
        logger.warning("No mana symbols found in deck")
