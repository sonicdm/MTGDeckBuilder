"""
Helpers for the YAML deck builder.

These functions provide card selection, filtering, and deck-filling logic for the deck builder pipeline.

Functions:
    _run_callback: Safely invoke a callback from a dict by hook name, logging errors.
    _select_priority_cards: Select cards from a repo based on priority, color, and legality.
    _select_special_lands: Filter and score non-basic lands for special land slots.
    _distribute_basic_lands: Distribute basic lands among allowed colors for the deck.
    _match_priority_text: Check if a card's text matches any pattern (regex or substring).
    _fill_categories: Fill deck categories (e.g., creatures) from a repo, using config and constraints.
    _fill_with_any: Fill the deck with any available cards to reach the target size, respecting constraints.
    generate_target_curve: Generate a mana curve dict based on config.
    _prune_lowest_scoring: Prune lowest scoring cards and attempt to replace them with better options.
    _prune_overfilled_categories: Prune cards from overfilled categories to reach target deck size.

Key Concepts:
- All keyword and type matches are case-insensitive and use structured metadata where possible.
- Category filling and scoring is based on unified and categorized rules from the YAML spec.
- All filtering and scoring logic is modular and reusable for deck building and analysis.
"""

from typing import Dict, Optional, Callable, List, Set
import logging

from mtg_deck_builder.yaml_builder.deck_build_classes import BuildContext
from mtg_deck_builder.yaml_builder.helpers.card_scoring import score_card
from mtg_deck_builder.db.repository import SummaryCardRepository
from mtg_deck_builder.db.mtgjson_models.cards import MTGJSONSummaryCard

logger = logging.getLogger(__name__)

CallbackDict = Dict[str, Callable]


def _run_callback(callbacks: Optional[CallbackDict], hook_name: str, **kwargs) -> None:
    if callbacks and hook_name in callbacks:
        try:
            callbacks[hook_name](**kwargs)
        except Exception as e:
            logger.error(f"Error in callback {hook_name}: {e}")


def _select_priority_cards(build_context: BuildContext):
    logger.info("Selecting priority cards...")
    context = build_context.deck_build_context
    config = build_context.deck_config

    if not context:
        logger.error(
            "DeckBuildContext is None in _select_priority_cards", exc_info=True
        )
        return

    if not config.priority_cards:
        logger.info("No priority cards specified")
        return

    all_cards = build_context.summary_repo.get_all_cards()

    for entry in config.priority_cards:
        name = entry.name
        min_copies = entry.min_copies
        card = next((c for c in all_cards if getattr(c, "name", None) == name), None)

        if not card:
            if hasattr(context, "record_unmet_condition"):
                context.record_unmet_condition(f"Priority card not found: {name}")
            continue

        score = score_card(card, config.scoring_rules, context)
        success = context.add_card(
            card, reason="priority_card", source="priority", quantity=min_copies
        )

        if success:
            context.cards[-1].score = score
            context.cards[-1].add_reason(f"score: {score}")

        logger.debug(f"Added priority card: {name} (qty={min_copies}, score={score})")


def _handle_special_lands(build_context):
    logger.info("Handling special lands...")
    context = build_context.deck_build_context
    config = build_context.deck_config

    if not config.mana_base or not config.mana_base.special_lands:
        logger.info("No special lands configuration")
        return

    special_lands = config.mana_base.special_lands
    target_count = special_lands.count

    if target_count <= 0:
        logger.info("No special lands requested")
        return

    land_repo = SummaryCardRepository(build_context.summary_repo.session)
    land_repo.cards = [
        card
        for card in build_context.summary_repo.get_all_cards()
        if "Land" in getattr(card, "types", [])
    ]
    all_lands = land_repo.get_all_cards()

    candidate_lands = []
    for land in all_lands:
        if "Basic Land" in str(getattr(land, "type", "")):
            continue
        if special_lands.prefer and not any(
            pref.lower() in (getattr(land, "oracle_text", "") or "").lower()
            for pref in special_lands.prefer
        ):
            continue
        if special_lands.avoid and any(
            avoid.lower() in (getattr(land, "oracle_text", "") or "").lower()
            for avoid in special_lands.avoid
        ):
            continue
        candidate_lands.append(land)

    scored_lands = [
        (score_card(land, config.scoring_rules, context), land)
        for land in candidate_lands
    ]
    scored_lands.sort(key=lambda x: x[0], reverse=True)

    added_count = 0
    for score, land in scored_lands:
        if added_count >= target_count:
            break
        if context.add_card(
            land, reason="special_land", source="mana_base", quantity=1
        ):
            added_count += 1
            logger.debug(f"Added special land: {land.name} (score={score})")

    logger.info(f"Added {added_count} special lands")


def _distribute_basic_lands(
    basic_lands,
    allowed_colors,
    land_count,
    context,
    legalities=None,
    callbacks=None,
    lands_per_color=None,
):
    logger.debug(
        f"Starting with {len(basic_lands)} basic lands, target count: {land_count}"
    )

    if lands_per_color:
        for color, count in lands_per_color.items():
            if color not in allowed_colors:
                continue
            land = next((l for l in basic_lands if l.color == color), None)
            if land:
                if context.add_card(
                    land,
                    reason=f"basic_land_{color}",
                    source="mana_base",
                    quantity=count,
                ):
                    logger.debug(f"Added basic land: {land.name} ({color})")
        return

    color_counts = context.get_color_counts()
    total_symbols = sum(color_counts.values())

    if total_symbols == 0:
        lands_per_color = {
            color: land_count // len(allowed_colors) for color in allowed_colors
        }
        remainder = land_count % len(allowed_colors)
        if remainder > 0 and allowed_colors:
            first_color = next(iter(allowed_colors))
            lands_per_color[first_color] += remainder
    else:
        lands_per_color = {
            color: int(land_count * (color_counts.get(color, 0) / total_symbols))
            for color in allowed_colors
        }
        remainder = land_count - sum(lands_per_color.values())
        if remainder > 0:
            max_color = max(color_counts.items(), key=lambda x: x[1])[0]
            lands_per_color[max_color] += remainder

    for color, count in lands_per_color.items():
        if count <= 0:
            continue
        land = next((l for l in basic_lands if l.color == color), None)
        if land:
            if context.add_card(
                land, reason=f"basic_land_{color}", source="mana_base", quantity=count
            ):
                logger.debug(f"Added basic land: {land.name} ({color})")

    logger.info(f"Basic lands added for colors: {lands_per_color}")


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


def _filter_summary_repository(
    build_context: BuildContext,
) -> None:
    """Filter the card repository based on deck configuration.

    Args:
        build_context: Build context containing deck config and card repository
    """
    logger.info("Filtering card repository...")

    # Get core deck parameters
    deck_config = build_context.deck_config
    colors = deck_config.deck.colors
    color_match_mode = deck_config.deck.color_match_mode
    legalities = deck_config.deck.legalities
    allow_colorless = deck_config.deck.allow_colorless

    # Filter in-place
    build_context.summary_repo = build_context.summary_repo.filter_cards(
        color_identity=colors,
        color_mode=color_match_mode,
        legal_in=legalities,
        allow_colorless=allow_colorless,
    )

    # Log results
    card_count = len(build_context.summary_repo.get_all_cards())
    logger.info(
        f"Filtered repository: {card_count} cards meet color and legality requirements"
    )

    # Run callback if provided
    if (
        build_context.callbacks
        and "after_initial_repo_filter" in build_context.callbacks
    ):
        build_context.callbacks["after_initial_repo_filter"](
            repo=build_context.summary_repo, context=build_context.deck_build_context
        )


def _apply_card_constraints(
    build_context: BuildContext,
) -> None:
    """Apply card constraints after scoring.

    Args:
        build_context: Build context containing deck config and card repository
    """
    logger.info("Applying card constraints...")
    if not build_context.deck_build_context:
        return

    context = build_context.deck_build_context
    config = build_context.deck_config

    # Get configuration values
    card_constraints = config.card_constraints
    if not card_constraints:
        return

    # Get exclude keywords
    exclude_keywords = card_constraints.exclude_keywords
    if not exclude_keywords:
        return

    # Filter out cards with exclude keywords
    filtered_cards = []
    for score, card in context.scored_cards:
        # Skip if card has any exclude keywords
        if any(
            kw.lower() in (getattr(card, "text", "") or "").lower()
            for kw in exclude_keywords
        ):
            logger.debug(f"Excluding {card.name} due to exclude keywords")
            continue
        filtered_cards.append((score, card))

    # Update scored cards
    context.scored_cards = filtered_cards
    logger.info(
        f"Filtered {len(context.scored_cards)} cards after applying constraints"
    )
