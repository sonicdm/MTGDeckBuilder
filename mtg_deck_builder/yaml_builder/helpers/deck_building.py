"""Deck building process functions.

This module provides functions for:
- Handling priority cards
- Handling lands
- Finalizing deck
- Filtering and constraining cards
"""

import logging
from typing import Optional, List, Dict, Any, Union
from mtg_deck_builder.yaml_builder.deck_build_classes import BuildContext, LandStub
from mtg_deck_builder.models.deck import Deck
from mtg_deck_builder.db.mtgjson_models.cards import MTGJSONSummaryCard
from mtg_deck_builder.models.deck_config import PriorityCardEntry
from mtg_deck_builder.yaml_builder.types import ScoredCard
from .validation import _check_color_identity, _check_legalities, _check_ownership

logger = logging.getLogger(__name__)


def _handle_priority_cards(build_context: BuildContext) -> None:
    if not build_context.deck_build_context:
        return

    context = build_context.deck_build_context
    deck_config = build_context.deck_config

    if not deck_config.priority_cards:
        return

    for priority in deck_config.priority_cards:
        card = build_context.summary_repo.find_by_name(priority.name)
        if not card:
            logger.warning(f"Priority card not found: {priority.name}")
            continue

        success = context.add_card(card, "Priority Card", "priority", getattr(priority, "quantity", 1))

        if success:
            logger.debug(f"Added priority card: {priority.name}")


def _handle_basic_lands(build_context: BuildContext) -> None:
    if not build_context.deck_build_context:
        return

    context = build_context.deck_build_context
    deck_config = build_context.deck_config
    target_lands = deck_config.mana_base.land_count
    current_size = context.get_total_cards()
    available_slots = deck_config.deck.size - current_size
    land_target = target_lands - context.get_land_count()

    if available_slots < land_target:
        land_target = available_slots

    if land_target <= 0:
        return

    mana_symbols = context.meta.get("mana_symbols", {})
    if not mana_symbols:
        colors = deck_config.deck.colors
        if not colors:
            return
        mana_symbols = {color: 1 for color in colors}

    total_symbols = sum(mana_symbols.values())
    if total_symbols == 0:
        return

    land_distribution = {}
    remaining_lands = land_target

    for color, count in mana_symbols.items():
        if color in ["W", "U", "B", "R", "G"]:
            land_count = int((count / total_symbols) * land_target)
            land_distribution[color] = land_count
            remaining_lands -= land_count

    if remaining_lands > 0:
        sorted_colors = sorted(
            [c for c in mana_symbols.keys() if c in ["W", "U", "B", "R", "G"]],
            key=lambda c: mana_symbols[c],
            reverse=True,
        )
        for color in sorted_colors:
            if remaining_lands <= 0:
                break
            land_distribution[color] += 1
            remaining_lands -= 1

    total_added = 0
    for color, count in land_distribution.items():
        if count <= 0:
            continue

        land_name = {
            "W": "Plains",
            "U": "Island",
            "B": "Swamp",
            "R": "Mountain",
            "G": "Forest",
        }.get(color)

        if not land_name:
            continue

        land = LandStub(name=land_name, color=color, type="Basic Land", color_identity=[color])
        context.add_land_card(land, f"Basic {land_name}", "basic_land", count)
        total_added += count
        logger.debug(f"Added {count} {land_name} (total added: {total_added})")


def _handle_special_lands(build_context: BuildContext) -> int:
    if not build_context.deck_build_context or not build_context.mana_base:
        return 0

    context = build_context.deck_build_context
    mana_base = build_context.mana_base

    if not mana_base.special_lands:
        return 0

    preferred = mana_base.special_lands.prefer or []
    avoid = mana_base.special_lands.avoid or []
    target_count = mana_base.special_lands.count or 0

    if target_count <= 0:
        return 0

    if context.empty_slots < target_count:
        return 0

    filtered_repo = build_context.summary_repo.filter_cards(type_query="Land")
    land_cards = filtered_repo.get_all_cards()
    non_basic_lands = [card for card in land_cards if not card.is_basic_land()]

    scored_lands = []
    for card in non_basic_lands:
        if card.name in context.used_cards:
            continue
        scored_land = ScoredCard(card=card, score=0)
        for pattern in preferred:
            if pattern.lower() in (card.text or "").lower():
                scored_land.increase_score(1, "preferred_pattern", pattern)
        for pattern in avoid:
            if pattern.lower() in (card.text or "").lower():
                scored_land.increase_score(-2, "avoided_pattern", pattern)
        scored_lands.append(scored_land)

    scored_lands.sort(reverse=True)
    added_count = 0

    for scored_land in scored_lands:
        if added_count >= target_count:
            break
        if context.empty_slots <= 0:
            break
        quantity = min(context.empty_slots, target_count - added_count, 1)
        if quantity <= 0:
            break
        context.add_land_card(
            scored_land.card,
            "Special Land",
            "special_land",
            quantity,
        )
        added_count += quantity

    return added_count


def _finalize_deck(build_context: BuildContext) -> None:
    if not build_context.deck_build_context:
        return

    context = build_context.deck_build_context
    deck_config = build_context.deck_config

    current_size = context.get_total_cards()
    target_size = deck_config.deck.size

    # If deck is too large, remove lowest-scored non-land cards
    if current_size > target_size:
        non_land_cards = [c for c in context.cards if not c.card.is_basic_land()]
        non_land_cards.sort(key=lambda c: c.score or 0)
        while context.get_total_cards() > target_size and non_land_cards:
            card = non_land_cards.pop(0)
            context.cards.remove(card)

    # If deck is too small, add more basic lands
    current_size = context.get_total_cards()
    if current_size < target_size and build_context.mana_base:
        remaining_slots = target_size - current_size
        _handle_basic_lands(build_context)

    # Final check - if still too large, remove more cards
    final_size = context.get_total_cards()
    if final_size > target_size:
        non_land_cards = [c for c in context.cards if not c.card.is_basic_land()]
        non_land_cards.sort(key=lambda c: c.score or 0)
        while context.get_total_cards() > target_size and non_land_cards:
            card = non_land_cards.pop(0)
            context.cards.remove(card)
    
    # If still too small, add more basic lands (emergency fill)
    final_size = context.get_total_cards()
    if final_size < target_size:
        remaining_slots = target_size - final_size
        logger.info(f"Emergency fill: adding {remaining_slots} basic lands to reach target size")
        
        # Add basic lands to fill remaining slots
        colors = deck_config.deck.colors or ["R", "G"]  # Default to RG if no colors specified
        for i in range(remaining_slots):
            color = colors[i % len(colors)]
            land_name = {
                "W": "Plains",
                "U": "Island", 
                "B": "Swamp",
                "R": "Mountain",
                "G": "Forest",
            }.get(color)
            if land_name:
                land = LandStub(name=land_name, color=color, type="Basic Land", color_identity=[color])
                context.add_land_card(land, f"Emergency {land_name}", "emergency_land", 1)
                logger.debug(f"Added emergency {land_name}")
    
    # Final verification
    final_size = context.get_total_cards()
    if final_size != target_size:
        logger.warning(f"Final deck size: {final_size}, target: {target_size}")
    else:
        logger.info(f"Successfully built deck with {final_size} cards")


def _log_deck_composition(build_context: BuildContext) -> None:
    if not build_context.deck_build_context:
        return

    context = build_context.deck_build_context
    total_cards = context.get_total_cards()
    land_count = context.get_land_count()
    color_counts = context.get_color_counts()
    category_counts = {}

    for card in context.cards:
        category = card.source
        category_counts[category] = category_counts.get(category, 0) + card.quantity

    logger.info(f"Total cards: {total_cards}")
    logger.info(f"Land count: {land_count}")
    logger.info(f"Color distribution: {color_counts}")
    logger.info(f"Category distribution: {category_counts}")


def _filter_summary_repository(build_context: BuildContext) -> None:
    if not build_context.deck_build_context:
        return

    deck_config = build_context.deck_config
    summary_repo = build_context.summary_repo

    if deck_config.deck.colors:
        summary_repo = summary_repo.filter_cards(
            color_identity=deck_config.deck.colors,
            color_mode=deck_config.deck.color_match_mode,
            allow_colorless=deck_config.deck.allow_colorless,
        )

    if deck_config.deck.legalities:
        summary_repo = summary_repo.filter_cards(legal_in=deck_config.deck.legalities)

    if deck_config.deck.owned_cards_only:
        summary_repo = summary_repo.filter_by_inventory_quantity(1)

    build_context.summary_repo = summary_repo


def _apply_card_constraints(build_context: BuildContext) -> None:
    if not build_context.deck_build_context:
        return

    deck_config = build_context.deck_config
    card_constraints = getattr(deck_config, "card_constraints", None)
    if not card_constraints:
        return

    rarity_boost = getattr(card_constraints, "rarity_boost", None)
    if not rarity_boost:
        return

    rarity_mappings = [
        ("common", getattr(rarity_boost, "common", 0)),
        ("uncommon", getattr(rarity_boost, "uncommon", 0)),
        ("rare", getattr(rarity_boost, "rare", 0)),
        ("mythic", getattr(rarity_boost, "mythic", 0)),
    ]

    for rarity, boost in rarity_mappings:
        if boost <= 0:
            continue
        filtered_repo = build_context.summary_repo.filter_cards(rarity=rarity)
        cards = filtered_repo.get_all_cards()
        for i, (score, card) in enumerate(build_context.deck_build_context.scored_cards):
            if card in cards:
                build_context.deck_build_context.scored_cards[i] = (score + boost, card)
