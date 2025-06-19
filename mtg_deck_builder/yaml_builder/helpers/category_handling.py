"""Category handling functions for deck building.

This module provides functions for:
- Filling categories with appropriate cards
- Pruning overfilled categories
- Matching cards to category requirements
"""

from collections import defaultdict
import logging
from typing import List, Dict, Optional, Any, Union, Set, Tuple
from mtg_deck_builder.yaml_builder.deck_build_classes import BuildContext, LandStub
from mtg_deck_builder.db.mtgjson_models.cards import MTGJSONSummaryCard
from mtg_deck_builder.models.deck_config import CategoryDefinition
from mtg_deck_builder.yaml_builder.types import DeckBuildCategorySummary, ScoredCard
from .card_scoring import score_card

logger = logging.getLogger(__name__)


def category_matches(
    card: Union[MTGJSONSummaryCard, LandStub],
    category: CategoryDefinition,
) -> bool:
    """Check if a card matches a category's requirements.

    Args:
        card: Card to check (either MTGJSONSummaryCard or LandStub)
        category: Category definition to match against

    Returns:
        True if card matches category requirements
    """
    # Get card types and text
    card_types = getattr(card, "types", []) or []
    card_text = getattr(card, "text", "") or getattr(card, "oracle_text", "") or ""

    # Initialize match flags
    keywords_match = False
    priority_text_match = False
    type_match = False

    # Check if card matches any preferred keyword
    if category.preferred_keywords:
        if isinstance(card, MTGJSONSummaryCard):
            keywords_match = card.has_keywords(category.preferred_keywords)
        else:  # LandStub
            keywords_match = any(
                kw.lower() in [k.lower() for k in card.keywords]
                for kw in category.preferred_keywords
            )

    # Check if card matches any priority text
    if category.priority_text:
        priority_text_match = any(
            text.lower() in card_text.lower() for text in category.priority_text
        )

    # Check if card matches any preferred type
    if category.preferred_basic_type_priority:
        type_match = any(
            type_name.lower() in [t.lower() for t in card_types]
            for type_name in category.preferred_basic_type_priority
        )

    # Card matches if it satisfies any of the criteria
    return keywords_match or priority_text_match or type_match


def _fill_categories(build_context: BuildContext, available_slots: int) -> None:
    """Fill categories with cards based on their definitions.

    Args:
        build_context: Build context containing deck config and card repository
        available_slots: Number of slots available for non-land cards
    """
    if not build_context.deck_build_context:
        return

    context = build_context.deck_build_context
    deck_config = build_context.deck_config

    # Calculate total target cards from categories
    total_target = sum(cat.target for cat in deck_config.categories.values())
    logger.info(
        f"Category filling: total target {total_target}, available slots {available_slots}"
    )

    # Log original targets
    original_targets = {
        name: cat.target for name, cat in deck_config.categories.items()
    }
    logger.info(f"Original category targets: {original_targets}")

    # Adjust targets if they exceed available slots
    if total_target > available_slots:
        # Calculate scaling factor
        scale = available_slots / total_target
        logger.info(f"Scaling categories by factor {scale:.3f}")
        # Scale down each category's target
        for card_type in deck_config.categories.values():
            old_target = card_type.target
            card_type.target = max(1, int(card_type.target * scale))
            logger.debug(f"Scaled category target: {old_target} -> {card_type.target}")
    else:
        logger.info("No scaling needed - targets fit within available slots")

    # Log scaled targets
    scaled_targets = {name: cat.target for name, cat in deck_config.categories.items()}
    logger.info(f"Scaled category targets: {scaled_targets}")
    cards = build_context.summary_repo.get_all_cards()
    category_summary = {}
    # Fill each category
    for category_name, category in deck_config.categories.items():
        category_free_slots = category.target
        scored_cards = [
            score_card(card, deck_config.scoring_rules, context) for card in cards
        ]
        # additional score for cards that match the categories preferred basic type priority
        card_category_weights = {}
        cat_weight = 1
        for card_type in sorted(category.preferred_basic_type_priority, reverse=True):
            card_category_weights[card_type] = cat_weight
            cat_weight += 1
        for scored_card in scored_cards:
            card = scored_card.card
            if card.name in context.used_cards:
                continue
            for card_type, weight in card_category_weights.items():
                if card.matches_type(card_type):
                    scored_card.increase_score(
                        score=weight,
                        source="category_handling",
                        reason=f"Preferred basic type priority: {card_type}",
                    )
            keywords_score = len(
                set(card.keywords).intersection(category.preferred_keywords)
            )
            if keywords_score > 0:
                scored_card.increase_score(
                    score=keywords_score,
                    source="category_handling",
                    reason=f"Preferred keywords: {category.preferred_keywords} ({keywords_score})",
                )
            # score on priority text
            for text in category.priority_text:
                if text.lower() in (getattr(card, "text", "") or "").lower():
                    scored_card.increase_score(
                        score=1,
                        source="category_handling",
                        reason=f"Priority text: {text}",
                    )
            # score on category matches
            if category_matches(card, category):
                scored_card.increase_score(
                    score=1,
                    source="category_handling",
                    reason=f"Category matches: {category_name}",
                )
        # sort the cards by score
        scored_cards = sorted(scored_cards, reverse=True)

        current_total = context.get_total_cards()
        if current_total >= available_slots:
            logger.info(
                f"Skipping {category_name} - deck already full ({current_total}/{available_slots})"
            )
            break

        # Add cards up to target, respecting available slots
        added_count = 0

        for scored_card in scored_cards:
            # Stop if we've reached category target or run out of slots
            if added_count >= category.target or category_free_slots <= 0:
                logger.info(
                    f"Skipping {scored_card.card.name} - category target reached ({added_count}/{category.target}) or no remaining slots ({category_free_slots})"
                )
                break

            # Calculate how many copies we can add
            min_score = (
                getattr(deck_config.scoring_rules, "min_score_to_flag", 6)
                if deck_config.scoring_rules
                else 0
            )
            max_copies = 1  # Default to 1 copy

            if scored_card.score >= min_score:
                # Calculate how many copies we can add
                max_copies = min(
                    deck_config.deck.max_card_copies,  # Max copies per card
                    category.target - added_count,  # Remaining category target
                    category_free_slots,  # Available deck slots
                )

            if max_copies > 0:
                # Add the card
                success = context.add_card(
                    scored_card.card,
                    f"Category: {category_name} (score: {scored_card.score:.1f})",
                    category_name,
                    max_copies,
                )

                if success:
                    added_count += max_copies
                    category_free_slots -= max_copies

        category_summary[category_name] = DeckBuildCategorySummary(
            target=category.target,
            added=added_count,
            remaining=category_free_slots,
            scored_cards=scored_cards,
        )

        logger.info(
            f"Added {added_count}/{category.target} cards to {category_name} (total: {context.get_total_cards()}/{available_slots})"
        )

        # Log if we couldn't meet the target
        if added_count < category.target:
            logger.warning(
                f"Could not meet target for {category_name}: "
                f"added {added_count}/{category.target} cards"
            )

    # Final check and prune if necessary
    current_size = context.get_total_cards()
    if current_size > available_slots:
        logger.warning(
            f"Deck overfilled: {current_size}/{available_slots} cards, pruning..."
        )
        _prune_overfilled_categories(build_context, available_slots)
    context.category_summary = category_summary
    logger.info(f"Category summary: {context.category_summary}")


def _prune_overfilled_categories(build_context: BuildContext, target_size: int) -> None:
    """Prune cards from overfilled categories to reach target size.

    Args:
        build_context: Build context containing deck config and card repository
        target_size: Target deck size to reach
    """
    if not build_context.deck_build_context:
        return

    context = build_context.deck_build_context

    # Get current size
    current_size = context.get_total_cards()
    if current_size <= target_size:
        return

    logger.info(f"Pruning deck from {current_size} to {target_size} cards")

    # Get all non-land cards
    non_land_cards = [c for c in context.cards if not c.card.is_basic_land()]

    # Sort by score (highest first, so we keep the best cards)
    non_land_cards.sort(key=lambda c: c.score or 0, reverse=True)

    # Keep only the highest scoring cards up to target size
    cards_to_keep = non_land_cards[:target_size]
    cards_to_remove = non_land_cards[target_size:]

    # Remove the lowest scoring cards
    for card in cards_to_remove:
        context.cards.remove(card)

    logger.info(
        f"Pruned {len(cards_to_remove)} cards, kept {len(cards_to_keep)} cards. Final size: {context.get_total_cards()}"
    )
