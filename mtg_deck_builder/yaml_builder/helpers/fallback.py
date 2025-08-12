"""Fallback strategy handling.

This module provides functions for:
- Handling fallback strategies when deck building
- Filling remaining slots with available cards
"""

import logging
from typing import Optional, List, Tuple, Any
from mtg_deck_builder.yaml_builder.deck_build_classes import BuildContext
from .card_scoring import score_card

logger = logging.getLogger(__name__)


def _calculate_dynamic_threshold(context, config) -> int:
    """Calculate dynamic fallback threshold based on deck quality.
    
    Args:
        context: Build context
        config: Deck configuration
        
    Returns:
        Dynamic threshold value
    """
    base_threshold = config.scoring_rules.min_score_to_flag
    
    # If no cards selected yet, use base threshold
    if not context.cards:
        return base_threshold
    
    # Calculate average score of selected cards
    scores = []
    for card in context.cards:
        if card.score is not None:
            scores.append(card.score)
    
    if not scores:
        return base_threshold
    
    average_score = sum(scores) / len(scores)
    
    # Dynamic threshold: base threshold or average + 1, whichever is higher
    dynamic_threshold = max(base_threshold, int(average_score + 1))
    
    logger.info(f"Dynamic threshold: base={base_threshold}, avg_score={average_score:.1f}, final={dynamic_threshold}")
    
    return dynamic_threshold


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

    # Check current non-land card count (exclude lands)
    current_non_lands = 0
    for cc in context.cards:
        try:
            if getattr(cc.card, 'is_basic_land', lambda: False)() or getattr(cc.card, 'is_land', lambda: False)():
                continue
        except Exception:
            pass
        current_non_lands += cc.quantity
    logger.info(
        f"Fallback strategy: current non-land cards: {current_non_lands}/{available_slots}"
    )

    # Calculate total target from categories
    total_category_target = sum(cat.target for cat in config.categories.values())
    logger.info(f"Fallback strategy: category targets total: {total_category_target}")

    # Only run fallback if categories are not filled to their targets
    # Only run fallback if non-land cards are below the category targets
    if current_non_lands >= total_category_target:
        logger.info(
            f"Categories are filled to target ({current_non_lands}/{total_category_target}), skipping fallback strategy"
        )
        return

    # Calculate how many more cards we need to reach category targets
    remaining_for_categories = total_category_target - current_non_lands
    logger.info(
        f"Fallback strategy: need {remaining_for_categories} more cards to reach category targets"
    )

    # Also check if we have room in available slots
    remaining_slots = available_slots - current_non_lands
    if remaining_slots <= 0:
        logger.warning(
            f"No slots available for fallback strategy: {current_non_lands}/{available_slots}"
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

    # Calculate dynamic threshold based on current deck quality
    dynamic_threshold = _calculate_dynamic_threshold(context, config)
    
    # Score remaining cards with dynamic quality threshold
    scored_cards = _score_cards_with_quality_filter(
        remaining_cards, config, context, "fallback", dynamic_threshold
    )

    # Add cards until we reach the limit
    added_count = 0
    for score, card, reasons in scored_cards:
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
            context.cards[-1].score = int(score)
            context.cards[-1].add_reason(f"score: {score}")
            for reason in reasons:
                context.cards[-1].add_reason(reason)
            added_count += copies_to_add
            
            logger.info(f"Fallback added {card.name} (score: {score:.1f}) - {', '.join(reasons)}")

    # Check final result
    current_size = context.get_total_cards()
    logger.info(
        f"Fallback strategy added {added_count} cards. Final non-land count: {current_size}/{available_slots}"
    )

    if current_non_lands + added_count < total_category_target and not fallback.allow_less_than_target:
        logger.warning(
            f"Could not fill categories to target: {current_non_lands + added_count}/{total_category_target}"
        )
    elif current_non_lands + added_count < total_category_target and fallback.allow_less_than_target:
        logger.info(
            f"Categories not fully filled but allow_less_than_target is true: {current_non_lands + added_count}/{total_category_target}"
        )


def _score_cards_with_quality_filter(
    cards: List, 
    config, 
    context, 
    source: str,
    min_score_threshold: Optional[int] = None
) -> List[Tuple[Optional[float], Any, List[str]]]:
    """Score cards and filter by quality threshold.
    
    Args:
        cards: List of cards to score
        config: Deck configuration
        context: Build context
        source: Source of the scoring (for logging)
        min_score_threshold: Minimum score threshold (uses config default if None)
        
    Returns:
        List of tuples: (score, card, reasons)
    """
    if min_score_threshold is None:
        min_score_threshold = config.scoring_rules.min_score_to_flag
    
    scored_cards = []
    for card in cards:
        scored_card = score_card(card, config.scoring_rules, context)
        if scored_card and scored_card.score is not None:
            # Collect reasons for the score
            reasons = _collect_score_reasons(card, config.scoring_rules, scored_card.score)
            scored_cards.append((scored_card.score, card, reasons))
    
    # Sort by score (highest first)
    scored_cards.sort(key=lambda x: x[0] or 0, reverse=True)
    
    # Filter by quality threshold if specified
    if min_score_threshold and min_score_threshold > 0:
        original_count = len(scored_cards)
        scored_cards = [(score, card, reasons) for score, card, reasons in scored_cards 
                       if score and score >= min_score_threshold]
        filtered_count = len(scored_cards)
        
        if filtered_count < original_count:
            logger.info(f"{source}: Filtered {original_count - filtered_count} cards below threshold {min_score_threshold}")
            
            # Log top 5 highest-scoring cards that were filtered out
            if original_count > filtered_count:
                all_scored = [(score, card, reasons) for score, card, reasons in scored_cards]
                all_scored.sort(key=lambda x: x[0] or 0, reverse=True)
                top_filtered = all_scored[:5]
                logger.info(f"{source}: Top 5 highest-scoring cards that could've been picked:")
                for score, card, reasons in top_filtered:
                    logger.info(f"  {card.name}: {score:.1f} - {', '.join(reasons)}")
    
    return scored_cards


def _collect_score_reasons(card, scoring_rules, score: float) -> List[str]:
    """Collect reasons why a card received its score.
    
    Args:
        card: The card being scored
        scoring_rules: Scoring rules configuration
        score: The final score
        
    Returns:
        List of reason strings
    """
    reasons = []
    
    # Check keyword abilities
    if hasattr(card, 'keywords') and card.keywords:
        for keyword in card.keywords:
            if keyword in scoring_rules.keyword_abilities:
                reasons.append(f"keyword: {keyword}")
    
    # Check text matches
    if hasattr(card, 'oracle_text') and card.oracle_text:
        text = card.oracle_text.lower()
        for pattern, weight in scoring_rules.text_matches.items():
            if pattern.lower() in text:
                reasons.append(f"text: {pattern}")
    
    # Check type bonuses
    if hasattr(card, 'types') and card.types:
        for card_type in card.types:
            if card_type in scoring_rules.type_bonus.get('basic_types', {}):
                reasons.append(f"type: {card_type}")
    
    # Check rarity bonus
    if hasattr(card, 'rarity') and card.rarity:
        if card.rarity in scoring_rules.rarity_bonus:
            reasons.append(f"rarity: {card.rarity}")
    
    # If no specific reasons found, add generic score reason
    if not reasons:
        reasons.append(f"base score: {score:.1f}")
    
    return reasons
