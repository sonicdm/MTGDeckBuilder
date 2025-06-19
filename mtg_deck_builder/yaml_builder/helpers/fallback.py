"""Fallback strategy handling.

This module provides functions for:
- Handling fallback strategies when deck building
- Filling remaining slots with available cards
"""

import logging
from typing import Optional
from mtg_deck_builder.yaml_builder.deck_build_classes import BuildContext
from .card_scoring import score_card

logger = logging.getLogger(__name__)


def _handle_fallback_strategy(build_context: BuildContext) -> None:
    """Handle fallback strategy for filling remaining slots.

    Args:
        build_context: Build context containing deck config and card repository
    """
    if not build_context.deck_build_context:
        return

    context = build_context.deck_build_context
    config = build_context.config
    fallback = config.fallback_strategy

    if not fallback:
        return

    # Calculate available slots for non-land cards
    target_size = config.deck.size
    target_lands = 0
    if build_context.mana_base and hasattr(build_context.mana_base, "land_count"):
        target_lands = build_context.mana_base.land_count
    available_slots = target_size - target_lands

    # Check current non-land card count
    current_size = context.get_total_cards()
    logger.info(
        f"Fallback strategy: current non-land cards: {current_size}/{available_slots}"
    )

    # Calculate total target from categories
    total_category_target = sum(cat.target for cat in config.categories.values())
    logger.info(f"Fallback strategy: category targets total: {total_category_target}")

    # Only run fallback if categories are not filled to their targets
    if current_size >= total_category_target:
        logger.info(
            f"Categories are filled to target ({current_size}/{total_category_target}), skipping fallback strategy"
        )
        return

    # Calculate how many more cards we need to reach category targets
    remaining_for_categories = total_category_target - current_size
    logger.info(
        f"Fallback strategy: need {remaining_for_categories} more cards to reach category targets"
    )

    # Also check if we have room in available slots
    remaining_slots = available_slots - current_size
    if remaining_slots <= 0:
        logger.warning(
            f"No slots available for fallback strategy: {current_size}/{available_slots}"
        )
        return

    # Use the smaller of the two limits
    cards_to_add = min(remaining_for_categories, remaining_slots)
    logger.info(f"Fallback strategy: will add {cards_to_add} cards")

    if cards_to_add <= 0:
        logger.info("No cards to add in fallback strategy")
        return

    # Get remaining cards
    remaining_cards = [
        card
        for card in build_context.summary_repo.get_all_cards()
        if card.name not in context.used_cards
    ]

    logger.info(f"Found {len(remaining_cards)} remaining cards for fallback")

    # Score remaining cards
    scored_cards = []
    for card in remaining_cards:
        score = score_card(card, config.scoring_rules, context)
        scored_cards.append((score, card))

    scored_cards.sort(key=lambda x: x[0], reverse=True)

    # Add cards until we reach the limit
    added_count = 0
    for score, card in scored_cards:
        if added_count >= cards_to_add:
            break

        # Calculate copies to add
        copies_to_add = min(cards_to_add - added_count, config.deck.max_card_copies)

        if copies_to_add <= 0:
            break

        # Add the card
        success = context.add_card(
            card, "Fallback fill", "fallback_strategy", copies_to_add
        )

        if success and score is not None:
            context.cards[-1].score = score
            context.cards[-1].add_reason(f"score: {score}")
            added_count += copies_to_add

    # Check final result
    current_size = context.get_total_cards()
    logger.info(
        f"Fallback strategy added {added_count} cards. Final non-land count: {current_size}/{available_slots}"
    )

    if current_size < total_category_target and not fallback.allow_less_than_target:
        logger.warning(
            f"Could not fill categories to target: {current_size}/{total_category_target}"
        )
    elif current_size < total_category_target and fallback.allow_less_than_target:
        logger.info(
            f"Categories not fully filled but allow_less_than_target is true: {current_size}/{total_category_target}"
        )
