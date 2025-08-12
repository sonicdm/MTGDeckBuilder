"""Deck building process functions.

This module provides functions for:
- Handling priority cards
- Handling lands
- Finalizing deck
- Filtering and constraining cards
"""

import logging
from typing import Dict, Optional

from mtg_deck_builder.yaml_builder.deck_build_classes import BuildContext, LandStub

from .fallback import _score_cards_with_quality_filter

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

        success = context.add_card(
            card, "Priority Card", "priority", getattr(priority, "quantity", 1)
        )

        if success:
            logger.debug(f"Added priority card: {priority.name}")


def _handle_basic_lands(
    build_context: BuildContext, additional_slots: Optional[int] = None
) -> None:
    """Add basic lands to the deck.

    Args:
        build_context: Current build context.
        additional_slots: If provided, add this many basic lands regardless of
            the mana base target.
    """
    if not build_context.deck_build_context:
        return

    context = build_context.deck_build_context
    deck_config = build_context.deck_config
    target_lands = deck_config.mana_base.land_count
    current_size = context.get_total_cards()
    available_slots = deck_config.deck.size - current_size

    if additional_slots is not None:
        land_target = min(additional_slots, available_slots)
    else:
        land_target = target_lands - context.get_land_count()
        if available_slots < land_target:
            land_target = available_slots

    if land_target <= 0:
        return

    mana_symbols = context.meta.get("mana_symbols", {})
    weights = deck_config.mana_base.color_weights if deck_config.mana_base else {}
    if weights:
        mana_symbols = weights
    if not mana_symbols:
        colors = deck_config.deck.colors
        if not colors:
            return
        mana_symbols = {color: 1 for color in colors}

    total_symbols = sum(mana_symbols.values())
    if total_symbols == 0:
        return

    land_distribution: Dict[str, int] = {}
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

        land = LandStub(
            name=land_name, color=color, type="Basic Land", color_identity=[color]
        )
        context.add_land_card(land, f"Basic {land_name}", "basic_land", count)
        total_added += count
        logger.debug(f"Added {count} {land_name} (total added: {total_added})")


def _handle_special_lands(build_context: BuildContext) -> int:
    """Handle special lands in the mana base.

    Args:
        build_context: Build context containing deck config and card repository

    Returns:
        Number of special lands added
    """
    if not build_context.deck_build_context:
        return 0

    context = build_context.deck_build_context
    deck_config = build_context.deck_config
    special_lands_config = deck_config.mana_base.special_lands

    if not special_lands_config:
        return 0

    # Calculate dynamic special lands count based on deck complexity
    base_count = special_lands_config.count
    color_count = len(deck_config.deck.colors)

    # Scale special lands based on color count and deck complexity
    if color_count >= 3:
        # Multi-color decks need more fixing
        dynamic_count = max(base_count, color_count * 2)
    elif color_count == 2:
        # Two-color decks can use some fixing
        dynamic_count = max(base_count, 3)
    else:
        # Mono-color decks need minimal fixing
        dynamic_count = min(base_count, 2)

    # Cap at reasonable maximum (half of total lands)
    max_special_lands = deck_config.mana_base.land_count // 2
    target_count = min(dynamic_count, max_special_lands)

    logger.info(
        f"Special lands: base={base_count}, colors={color_count}, dynamic={dynamic_count}, final={target_count}"
    )

    if target_count <= 0:
        return 0

    # Get available special lands
    available_lands = []
    filtered_repo = build_context.summary_repo.filter_cards()
    all_cards = filtered_repo.get_all_cards()

    for card in all_cards:
        if (
            card.name not in context.used_cards
            and "Land" in (getattr(card, "types", []) or [])
            and "Basic" not in (getattr(card, "supertypes", []) or [])
        ):
            available_lands.append(card)

    logger.info(f"Found {len(available_lands)} available special lands")

    # Score and filter special lands by quality
    scored_lands = _score_cards_with_quality_filter(
        available_lands, deck_config, context, "special_lands", min_score_threshold=2
    )

    # Apply prefer/avoid filters
    preferred_lands = []
    avoided_lands = []
    neutral_lands = []

    for score, land, reasons in scored_lands:
        land_name = getattr(land, "name", "")

        # Check if land is preferred
        if any(
            prefer.lower() in land_name.lower()
            for prefer in special_lands_config.prefer
        ):
            preferred_lands.append(
                (score + 2 if score is not None else 2, land, reasons)
            )  # Bonus for preferred
        # Check if land is avoided
        elif any(
            avoid.lower() in land_name.lower() for avoid in special_lands_config.avoid
        ):
            avoided_lands.append((score, land, reasons))
        else:
            neutral_lands.append((score, land, reasons))

    # Combine lists with preferred first, then neutral, then avoided
    all_scored_lands = preferred_lands + neutral_lands + avoided_lands

    # Add special lands
    added_count = 0
    for score, land, reasons in all_scored_lands:
        if added_count >= target_count:
            break

        success = context.add_land_card(land, "Special land", "special_land", 1)
        if success:
            context.cards[-1].score = int(score) if score is not None else None
            context.cards[-1].add_reason(f"score: {score:.1f}")
            for reason in reasons:
                context.cards[-1].add_reason(reason)
            added_count += 1
            logger.debug(
                f"Added special land {land.name} (score: {score:.1f}) - {', '.join(reasons)}"
            )

    logger.info(f"Added {added_count}/{target_count} special lands")
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

    # If still too small and we have room for more lands, add more
    current_size = context.get_total_cards()
    if current_size < target_size:
        remaining_slots = target_size - current_size
        current_land_count = context.get_land_count()
        target_land_count = deck_config.mana_base.land_count

        # Only add more lands if we're under the target land count
        if current_land_count < target_land_count:
            lands_to_add = min(remaining_slots, target_land_count - current_land_count)
            logger.info(
                f"Adding {lands_to_add} more basic lands to reach deck size (land count: {current_land_count}/{target_land_count})"
            )

            # Distribute lands by color - only use deck colors
            colors = deck_config.deck.colors
            if not colors:
                logger.warning(
                    "No deck colors specified, cannot distribute basic lands"
                )
                return

            for i in range(lands_to_add):
                color = colors[i % len(colors)]
                land_name = {
                    "W": "Plains",
                    "U": "Island",
                    "B": "Swamp",
                    "R": "Mountain",
                    "G": "Forest",
                }.get(color)

                if land_name:
                    land = LandStub(
                        name=land_name,
                        color=color,
                        type="Basic Land",
                        color_identity=[color],
                    )
                    context.add_land_card(
                        land, f"Basic {land_name} (fill)", "basic_land", 1
                    )
        else:
            # Land count is at target, but deck is still too small - this shouldn't happen in normal flow
            logger.warning(
                f"Deck is too small ({current_size}/{target_size}) but land count is at target ({current_land_count}/{target_land_count}). This indicates a problem in deck building."
            )
            # Don't add more lands - let emergency fill handle this

    # Final check - if still too large, remove more cards
    final_size = context.get_total_cards()
    if final_size > target_size:
        non_land_cards = [c for c in context.cards if not c.card.is_basic_land()]
        non_land_cards.sort(key=lambda c: c.score or 0)
        while context.get_total_cards() > target_size and non_land_cards:
            card = non_land_cards.pop(0)
            context.cards.remove(card)

    # If still too small, add more cards (emergency fill)
    final_size = context.get_total_cards()
    if final_size < target_size:
        remaining_slots = target_size - final_size
        logger.info(
            f"Emergency fill: adding {remaining_slots} cards to reach target size"
        )

        # Check if we need more lands or more non-land cards
        current_land_count = context.get_land_count()
        target_land_count = (
            deck_config.mana_base.land_count if deck_config.mana_base else 0
        )

        if current_land_count < target_land_count:
            # Need more lands
            logger.info(
                f"Emergency fill: adding {remaining_slots} basic lands (land count: {current_land_count}/{target_land_count})"
            )
            colors = deck_config.deck.colors
            if not colors:
                logger.warning(
                    "No deck colors specified, cannot add basic lands in emergency fill"
                )
                return

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
                    land = LandStub(
                        name=land_name,
                        color=color,
                        type="Basic Land",
                        color_identity=[color],
                    )
                    context.add_land_card(
                        land, f"Basic {land_name} (emergency)", "basic_land", 1
                    )
        else:
            # Need more non-land cards - this shouldn't happen in normal flow
            logger.warning(
                "Emergency fill needed but land count is already at target. This indicates a problem in deck building."
            )
            # Add basic lands anyway to reach deck size
            colors = deck_config.deck.colors
            if not colors:
                logger.warning(
                    "No deck colors specified, cannot add basic lands in emergency fill"
                )
                return

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
                    land = LandStub(
                        name=land_name,
                        color=color,
                        type="Basic Land",
                        color_identity=[color],
                    )
                    context.add_land_card(
                        land, f"Basic {land_name} (emergency)", "basic_land", 1
                    )

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

    # Handle commander logic
    if deck_config.deck.commander:
        logger.info(f"Commander format detected: {deck_config.deck.commander}")

        # Find the commander card
        commander_card = summary_repo.find_by_name(deck_config.deck.commander)
        if commander_card:
            # Set colors from commander's color identity
            commander_colors = getattr(commander_card, "color_identity_list", []) or []
            if commander_colors:
                deck_config.deck.colors = commander_colors
                logger.info(f"Set deck colors from commander: {commander_colors}")

            # Enforce singleton rule (except basic lands)
            deck_config.deck.max_card_copies = 1
            logger.info("Enforced singleton rule for Commander format")

            # Determine format based on legalities
            # Check for Standard Brawl first (more specific)
            is_standard_brawl = any(
                "standardbrawl" in legality.lower()
                for legality in deck_config.deck.legalities
            )
            # Check for Historic Brawl (general "brawl" legality)
            is_historic_brawl = any(
                "brawl" in legality.lower() and "standardbrawl" not in legality.lower()
                for legality in deck_config.deck.legalities
            )
            is_commander = any(
                "commander" in legality.lower()
                for legality in deck_config.deck.legalities
            )

            if is_standard_brawl:
                # Standard Brawl is 60 cards
                deck_config.deck.size = 60
                logger.info("Set deck size to 60 for Standard Brawl format")

                # Adjust land count for Standard Brawl if not already set appropriately
                if deck_config.mana_base and deck_config.mana_base.land_count < 20:
                    deck_config.mana_base.land_count = 24  # Standard for Brawl
                    logger.info(
                        f"Adjusted land count to {deck_config.mana_base.land_count} for Standard Brawl"
                    )

            elif is_historic_brawl:
                # Historic Brawl is 100 cards
                deck_config.deck.size = 100
                logger.info("Set deck size to 100 for Historic Brawl format")

                # Adjust land count for Historic Brawl if not already set appropriately
                if deck_config.mana_base and deck_config.mana_base.land_count < 30:
                    deck_config.mana_base.land_count = 37  # Standard for Historic Brawl
                    logger.info(
                        f"Adjusted land count to {deck_config.mana_base.land_count} for Historic Brawl"
                    )

            elif is_commander:
                # Commander is 100 cards
                deck_config.deck.size = 100
                logger.info("Set deck size to 100 for Commander format")

                # Adjust land count for Commander if not already set appropriately
                if deck_config.mana_base and deck_config.mana_base.land_count < 30:
                    deck_config.mana_base.land_count = 37  # Standard for Commander
                    logger.info(
                        f"Adjusted land count to {deck_config.mana_base.land_count} for Commander"
                    )
            else:
                # Default to Commander format if no specific format detected
                deck_config.deck.size = 100
                logger.info("Set deck size to 100 for Commander format (default)")

                # Adjust land count for Commander if not already set appropriately
                if deck_config.mana_base and deck_config.mana_base.land_count < 30:
                    deck_config.mana_base.land_count = 37  # Standard for Commander
                    logger.info(
                        f"Adjusted land count to {deck_config.mana_base.land_count} for Commander"
                    )

            # Add commander to priority cards if not already present
            commander_in_priority = any(
                pc.name.lower() == deck_config.deck.commander.lower()
                for pc in deck_config.priority_cards
            )
            if not commander_in_priority:
                from mtg_deck_builder.models.deck_config import PriorityCardEntry

                deck_config.priority_cards.append(
                    PriorityCardEntry(name=deck_config.deck.commander, min_copies=1)
                )
                logger.info(
                    f"Added commander {deck_config.deck.commander} to priority cards"
                )
        else:
            logger.warning(
                f"Commander {deck_config.deck.commander} not found in database"
            )

    # Apply deck-wide filters
    filtered_repo = summary_repo.filter_cards(
        color_identity=deck_config.deck.colors,  # Use color_identity for commander decks
        color_mode=deck_config.deck.color_match_mode,
        legal_in=deck_config.deck.legalities,
        allow_colorless=deck_config.deck.allow_colorless,
        min_quantity=1 if deck_config.deck.owned_cards_only else 0,
    )

    build_context.summary_repo = filtered_repo
    logger.info(
        f"Applied deck-wide filters: {len(filtered_repo.get_all_cards())} cards available"
    )


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

    # Apply rarity boost as scoring, not filtering
    rarity_mappings = [
        ("common", getattr(rarity_boost, "common", 0)),
        ("uncommon", getattr(rarity_boost, "uncommon", 0)),
        ("rare", getattr(rarity_boost, "rare", 0)),
        ("mythic", getattr(rarity_boost, "mythic", 0)),
    ]

    # Apply rarity boost to scored cards
    for rarity, boost in rarity_mappings:
        if boost <= 0:
            continue

        # Find cards of this rarity and boost their scores
        for i, (score, card) in enumerate(
            build_context.deck_build_context.scored_cards
        ):
            if hasattr(card, "rarity") and card.rarity == rarity:
                build_context.deck_build_context.scored_cards[i] = (score + boost, card)
                logger.debug(
                    f"Applied rarity boost of {boost} to {card.name} ({rarity})"
                )

    logger.info("Applied rarity boost constraints")
