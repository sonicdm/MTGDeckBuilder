"""Category handling functions for deck building.

This module provides functions for:
- Filling categories with appropriate cards
- Pruning overfilled categories
- Matching cards to category requirements
"""

from collections import defaultdict
import re
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

    # Compute scaled targets without mutating config
    scaled_targets = {}
    if total_target > available_slots and total_target > 0:
        scale = available_slots / total_target
        logger.info(f"Scaling categories by factor {scale:.3f}")
        for name, cat in deck_config.categories.items():
            old_target = cat.target
            scaled = max(1, int(old_target * scale))
            scaled_targets[name] = scaled
            logger.debug(f"Scaled category target for {name}: {old_target} -> {scaled}")
    else:
        for name, cat in deck_config.categories.items():
            scaled_targets[name] = cat.target
        logger.info("No scaling needed - targets fit within available slots")

    logger.info(f"Scaled category targets (effective): {scaled_targets}")
    cards = build_context.summary_repo.get_all_cards()
    category_summary = {}
    # Fill each category
    for category_name, category in deck_config.categories.items():
        desired_target = int(scaled_targets.get(category_name, category.target))
        category_free_slots = desired_target
        scored_cards = [
            score_card(card, deck_config.scoring_rules, context) for card in cards
        ]
        # additional score for cards that match the categories preferred basic type priority
        card_category_weights = {}
        priority_types = list(category.preferred_basic_type_priority or [])
        # Preserve the declared priority order: earlier types get higher weight
        for idx, card_type in enumerate(priority_types):
            card_category_weights[card_type] = (len(priority_types) - idx) or 1
        owned_only = bool(getattr(deck_config.deck, 'owned_cards_only', False))
        # Determine if this category requires matching one of the preferred basic types strictly
        requires_type_match = bool(category.preferred_basic_type_priority)

        for scored_card in scored_cards:
            card = scored_card.card
            if card.name in context.used_cards:
                continue
                
            # Skip land cards for all categories (lands are handled by mana base)
            if hasattr(card, "types") and "Land" in (card.types or []):
                continue
            for card_type, weight in card_category_weights.items():
                if card.matches_type(card_type):
                    scored_card.increase_score(
                        score=weight,
                        source="category_handling",
                        reason=f"Preferred basic type priority: {card_type}",
                    )
            try:
                card_keywords = set((card.keywords or []) if isinstance(card.keywords, list) else [])
            except Exception:
                card_keywords = set()
            keywords_score = len(card_keywords.intersection(set(category.preferred_keywords or [])))
            if keywords_score > 0:
                scored_card.increase_score(
                    score=keywords_score,
                    source="category_handling",
                    reason=f"Preferred keywords: {category.preferred_keywords} ({keywords_score})",
                )
            # score on priority text (supports /regex/ notation)
            for text in (category.priority_text or []):
                ctext = (getattr(card, "text", "") or "")
                matched = False
                if isinstance(text, str) and len(text) >= 2 and text.startswith("/") and text.endswith("/"):
                    pattern = text[1:-1]
                    try:
                        if re.search(pattern, ctext, flags=re.IGNORECASE):
                            matched = True
                    except re.error:
                        matched = text.lower() in ctext.lower()
                else:
                    matched = str(text).lower() in ctext.lower()
                if matched:
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
        # sort the cards by score (highest first)
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
            if added_count >= desired_target or category_free_slots <= 0:
                logger.info(
                    f"Skipping {scored_card.card.name} - category target reached ({added_count}/{desired_target}) or no remaining slots ({category_free_slots})"
                )
                break

            # Calculate how many copies we can add
            min_score = (
                getattr(deck_config.scoring_rules, "min_score_to_flag", 6)
                if deck_config.scoring_rules
                else 0
            )
            # Only consider cards that match this category in the normal pass
            if not category_matches(scored_card.card, category):
                continue
            # If category declares preferred_basic_type_priority, enforce at least one type match
            if requires_type_match:
                if not any(scored_card.card.matches_type(t) for t in category.preferred_basic_type_priority):
                    continue
            # Respect inventory when owned_cards_only is True
            owned_qty = int(getattr(scored_card.card, 'quantity', 0) or 0)
            # Default to 1 copy if below threshold and not owned_only; otherwise clamp to ownership
            max_copies = 1 if not owned_only else min(1, owned_qty)

            if scored_card.score >= min_score:
                # Calculate how many copies we can add
                max_copies = min(
                    deck_config.deck.max_card_copies,  # Max copies per card
                    desired_target - added_count,  # Remaining category target
                    category_free_slots,  # Available deck slots
                    owned_qty if owned_only else deck_config.deck.max_card_copies,  # clamp by ownership if required
                )

            # If owned-only and we don't own any, skip entirely
            if owned_only and max_copies <= 0:
                continue

            if max_copies > 0:
                # Add the card
                logging.debug(f"Adding card: {scored_card.card.name} (score: {scored_card.score:.1f}) QTY OWNED: {scored_card.card.quantity}")
                success = context.add_card(
                    scored_card.card,
                    f"Category: {category_name} (score: {scored_card.score:.1f})",
                    category_name,
                    max_copies,
                    score=scored_card.score,
                )

                if success:
                    added_count += max_copies
                    category_free_slots -= max_copies
                    # Merge score reasons and sources into context card for UI/debug
                    try:
                        cc = context.cards[-1]
                        for rs in getattr(scored_card, 'reasons', []) or []:
                            cc.add_reason(rs)
                        for src in getattr(scored_card, 'sources', []) or []:
                            cc.sources.add(src)
                    except Exception:
                        pass

        # Fallback: if we didn't reach the desired target, try below-threshold matches to fill up to desired_target
        if added_count < desired_target and category_free_slots > 0:
            logger.info(
                f"Not enough cards met threshold for {category_name} (added {added_count}/{desired_target}). Using fallback to add below-threshold matches."
            )
            for scored_card in scored_cards:
                if added_count >= desired_target or category_free_slots <= 0:
                    break
                card = scored_card.card
                if card.name in context.used_cards:
                    continue
                if hasattr(card, "types") and "Land" in (card.types or []):
                    continue
                # Only consider cards that actually match the category
                if not category_matches(card, category):
                    continue
                # If category declares preferred types, enforce them in fallback too
                if requires_type_match:
                    if not any(card.matches_type(t) for t in category.preferred_basic_type_priority):
                        continue
                owned_qty = int(getattr(card, 'quantity', 0) or 0)
                max_copies = min(
                    deck_config.deck.max_card_copies,
                    desired_target - added_count,
                    category_free_slots,
                    owned_qty if owned_only else deck_config.deck.max_card_copies,
                )
                if owned_only and max_copies <= 0:
                    continue
                if max_copies > 0:
                    success = context.add_card(
                        card,
                        f"Category fallback: {category_name} (score: {scored_card.score:.1f})",
                        category_name,
                        max_copies,
                        score=scored_card.score,
                    )
                    if success:
                        added_count += max_copies
                        category_free_slots -= max_copies
                        try:
                            cc = context.cards[-1]
                            for rs in getattr(scored_card, 'reasons', []) or []:
                                cc.add_reason(rs)
                            for src in getattr(scored_card, 'sources', []) or []:
                                cc.sources.add(src)
                        except Exception:
                            pass

        category_summary[category_name] = DeckBuildCategorySummary(
            target=desired_target,
            added=added_count,
            remaining=category_free_slots,
            scored_cards=scored_cards,
        )

        logger.info(
            f"Added {added_count}/{desired_target} cards to {category_name} (total: {context.get_total_cards()}/{available_slots})"
        )

        # Log if we couldn't meet the target
        if added_count < desired_target:
            logger.warning(
                f"Could not meet target for {category_name}: "
                f"added {added_count}/{desired_target} cards"
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

    logger.info(f"Pruning deck from {current_size} to {target_size} cards (non-lands)")

    # Build category quotas from summary set earlier in _fill_categories
    category_summary = getattr(context, 'category_summary', {}) or {}
    required_by_category: Dict[str, int] = {
        name: (getattr(summary, 'target', 0) or 0)
        for name, summary in category_summary.items()
    }

    # Count current per-category quantities (non-lands only)
    counts_by_category: Dict[str, int] = defaultdict(int)
    for cc in context.cards:
        try:
            if getattr(cc.card, 'is_basic_land', lambda: False)():
                continue
        except Exception:
            pass
        counts_by_category[cc.source] += cc.quantity

    # Compute how many we must remove
    to_remove = current_size - target_size

    # Build a list of removable candidates (those from categories currently above their required target)
    removable: List[ContextCard] = []
    from mtg_deck_builder.yaml_builder.deck_build_classes import ContextCard as _CC  # type: ignore
    for cc in context.cards:
        try:
            if getattr(cc.card, 'is_basic_land', lambda: False)():
                continue
        except Exception:
            continue
        cur = counts_by_category.get(cc.source, 0)
        req = required_by_category.get(cc.source, 0)
        if cur > req:
            removable.append(cc)

    # If nothing is removable by category quota, fall back to score-only pruning on non-lands
    if not removable:
        non_land_cards = [c for c in context.cards if not getattr(c.card, 'is_basic_land', lambda: False)()]
        non_land_cards.sort(key=lambda c: c.score or 0)  # lowest first
        while to_remove > 0 and non_land_cards:
            card = non_land_cards.pop(0)
            context.cards.remove(card)
            to_remove -= card.quantity
        logger.info(f"Pruned to target using fallback. Remaining to remove: {to_remove}")
        return

    # Sort removable by score ascending (remove lowest quality first)
    removable.sort(key=lambda c: c.score or 0)

    # Remove while respecting per-category minimums
    idx = 0
    removed = 0
    while to_remove > 0 and idx < len(removable):
        cc = removable[idx]
        cur = counts_by_category.get(cc.source, 0)
        req = required_by_category.get(cc.source, 0)
        # Only remove if category stays >= required after removal
        if cur - cc.quantity >= req:
            context.cards.remove(cc)
            counts_by_category[cc.source] = cur - cc.quantity
            to_remove -= cc.quantity
            removed += cc.quantity
        idx += 1

    logger.info(f"Category-aware prune removed {removed} cards. Remaining to remove: {to_remove}")
