"""YAML Deck Builder Module.

This module provides the main entry points for constructing a Deck object from a YAML file or
configuration dictionary, using the provided card and inventory repositories. It supports deck
building with category targets, priority cards, mana base configuration, and fallback strategies,
and allows for callback hooks at various stages of the build process.

Functions:
    build_deck_from_config: Build a Deck from a DeckConfig object.
    build_deck_from_yaml: Build a Deck from a YAML file or dictionary.
    load_yaml_config: Load a YAML configuration file into a DeckConfig object.
"""

import logging
import os
import random
import traceback
from pathlib import Path
from typing import Any, Dict, Optional, Union

import yaml

from mtg_deck_builder.db.repository import SummaryCardRepository
from mtg_deck_builder.models.deck import Deck
from mtg_deck_builder.models.deck_config import DeckConfig
from mtg_deck_builder.yaml_builder.deck_build_classes import (
    BuildContext,
    DeckBuildContext,
)
from mtg_deck_builder.yaml_builder.helpers import (
    _apply_card_constraints,
    _fill_categories,
    _filter_summary_repository,
    _finalize_deck,
    _handle_basic_lands,
    _handle_fallback_strategy,
    _handle_priority_cards,
    _handle_special_lands,
    _log_deck_composition,
    _prune_overfilled_categories,
)
from mtg_deck_builder.yaml_builder.helpers.mana_curve import _compute_mana_symbols
from mtg_deck_builder.yaml_builder.types import CallbackDict

logger = logging.getLogger(__name__)


def build_deck_from_config(
    deck_config: DeckConfig,
    summary_repo: SummaryCardRepository,
    callbacks: Optional[CallbackDict] = None,
    verbose: bool = False,
) -> Optional[Deck]:
    """Build a deck from a configuration object."""
    logger.info(f"Starting deck build for {deck_config.name}")
    logger.info(
        f"Deck configuration: colors={deck_config.colors}, size={deck_config.deck.size}, max_copies={deck_config.deck.max_card_copies}"
    )

    # Initialize build context
    # Attach DeckConfig so downstream (API/UI) can access configuration and context
    deck = Deck(name=deck_config.name, config=deck_config)
    deck_build_context = DeckBuildContext(
        config=deck_config, summary_repo=summary_repo, deck=deck
    )
    build_context = BuildContext(
        deck_config=deck_config,
        summary_repo=summary_repo,
        callbacks=callbacks,
        deck_build_context=deck_build_context,
    )

    seed = str(
        getattr(deck_config, "seed", None)
        or getattr(deck_config.deck, "name", "mtg-deck-builder")
    )
    build_context.rng = random.Random(seed)

    try:
        # Step 1: Apply deck-wide filters
        logger.info("[BuildPhase] Step 1: Applying deck-wide filters")
        _filter_summary_repository(build_context)

        # Step 2: Add priority cards
        logger.info("[BuildPhase] Step 2: Adding priority cards")
        _handle_priority_cards(build_context)

        # Step 3: Apply card constraints
        logger.info("[BuildPhase] Step 3: Applying card constraints")
        _apply_card_constraints(build_context)

        # Step 4: Compute mana symbol distribution
        logger.info("[BuildPhase] Step 4: Computing mana symbol distribution")
        _compute_mana_symbols(build_context)

        # Step 5: Calculate available slots for non-land cards (after priority cards)
        deck_obj = (
            build_context.deck_build_context.deck
            if build_context.deck_build_context
            else None
        )
        size = int(getattr(deck_config.deck, "size", 60) or 60)
        land_target = getattr(
            getattr(build_context, "mana_base", None), "land_count", None
        )
        if land_target is None:
            land_target = max(16, min(28, round(size * 0.40)))

        current_nonlands = 0
        if deck_obj:
            current_nonlands = sum(
                int(e.quantity)
                for e in getattr(build_context.deck_build_context, "cards", [])
                if "Land" not in getattr(e.card, "type_line", "")
            )
        nonland_target = max(0, size - land_target)
        available_slots = max(0, nonland_target - current_nonlands)
        logger.info(
            f"Available slots for categories: {available_slots} (deck size: {size}, target lands: {land_target}, current nonlands: {current_nonlands})"
        )

        # Pre-check: category targets vs deck size and available non-land slots
        try:
            total_category_targets = sum(
                cat.target for cat in deck_config.categories.values()
            )
        except Exception:
            total_category_targets = 0
        if total_category_targets > deck_config.deck.size:
            logger.warning(
                f"Category targets ({total_category_targets}) exceed deck size ({deck_config.deck.size}). Targets will be scaled."
            )
            if deck_build_context:
                deck_build_context.record_unmet_condition(
                    f"Category targets exceed deck size: {total_category_targets} > {deck_config.deck.size}"
                )
        if total_category_targets > nonland_target:
            logger.warning(
                f"Category targets ({total_category_targets}) exceed available non-land slots ({nonland_target}). Targets will be scaled."
            )
            if deck_build_context:
                deck_build_context.record_unmet_condition(
                    f"Targets exceed non-land slots: {total_category_targets} > {nonland_target}"
                )

        # Step 6: Fill category roles with available slots
        logger.info("[BuildPhase] Step 6: Filling category roles")
        if build_context.deck_build_context:
            logger.info(
                f"Before categories: {build_context.deck_build_context.get_total_cards()} cards"
            )
        _fill_categories(build_context, available_slots)
        if build_context.deck_build_context:
            logger.info(
                f"After categories: {build_context.deck_build_context.get_total_cards()} cards"
            )
            # Recompute mana symbols based on filled categories
            _compute_mana_symbols(build_context)

        # Step 7: Add special lands
        logger.info("[BuildPhase] Step 7: Adding special lands")
        if build_context.deck_build_context:
            logger.info(
                f"Before special lands: {build_context.deck_build_context.get_total_cards()} cards"
            )
        if build_context.mana_base and build_context.mana_base.special_lands:
            _handle_special_lands(build_context)
        if build_context.deck_build_context:
            logger.info(
                f"After special lands: {build_context.deck_build_context.get_total_cards()} cards"
            )
            # Recompute mana symbols after special lands (no mana cost but updates context)
            _compute_mana_symbols(build_context)

        # Step 8: Add basic lands
        logger.info("[BuildPhase] Step 8: Adding basic lands")
        if build_context.deck_build_context:
            logger.info(
                f"Before basic lands: {build_context.deck_build_context.get_total_cards()} cards"
            )
        if build_context.mana_base:
            _handle_basic_lands(build_context)
        if build_context.deck_build_context:
            logger.info(
                f"After basic lands: {build_context.deck_build_context.get_total_cards()} cards"
            )
        logger.info("[BuildPhase] Step 9: Applying fallback strategy")
        if build_context.deck_build_context:
            logger.info(
                f"Before fallback: {build_context.deck_build_context.get_total_cards()} cards"
            )
        _handle_fallback_strategy(build_context)
        if build_context.deck_build_context:
            logger.info(
                f"After fallback: {build_context.deck_build_context.get_total_cards()} cards"
            )
        # Step 10: Finalize deck
        logger.info("[BuildPhase] Step 10: Finalizing deck")
        _finalize_deck(build_context)

        # Validate final deck size
        if build_context.deck_build_context:
            final_size = build_context.deck_build_context.get_total_cards()
            if final_size != deck_config.deck.size:
                logger.warning(
                    f"Deck size mismatch: expected {deck_config.deck.size}, got {final_size}"
                )

                if final_size > deck_config.deck.size:
                    # Deck is too large - prune lowest scoring cards
                    _prune_overfilled_categories(build_context, deck_config.deck.size)
                elif final_size < deck_config.deck.size and build_context.mana_base:
                    # Deck is too small - add more basic lands
                    remaining_slots = deck_config.deck.size - final_size
                    _handle_basic_lands(build_context, remaining_slots)

                # Verify size after adjustment
                final_size = build_context.deck_build_context.get_total_cards()
                if final_size != deck_config.deck.size:
                    logger.error(
                        f"Failed to adjust deck to target size. Current size: {final_size}, target: {deck_config.deck.size}"
                    )
                    # Don't raise an error, just log it and continue

        # Log final deck composition
        if build_context.deck_build_context:
            _log_deck_composition(build_context)

        if build_context.deck_build_context:
            # Expose build context on the deck instance for debugging/inspection downstream
            try:
                setattr(deck, "_build_context", build_context.deck_build_context)
            except Exception:
                # Safe fallback; context is only for debug/inspection
                pass
            return build_context.deck_build_context.deck
        return None

    except Exception as e:
        logger.error(f"Error building deck: {str(e)}")
        logger.error(traceback.format_exc())
        return None


def build_deck_from_yaml(
    yaml_data: Union[Dict[str, Any], str, Path],
    summary_repo: SummaryCardRepository,
    callbacks: Optional[CallbackDict] = None,
    verbose: bool = False,
) -> Optional[Deck]:
    """Build a deck from YAML data."""

    try:
        if isinstance(yaml_data, dict):
            deck_config = DeckConfig.from_dict(yaml_data)
        else:
            deck_config = load_yaml_config(yaml_data)
        return build_deck_from_config(deck_config, summary_repo, callbacks, verbose)
    except Exception as e:
        logger.error(f"Error building deck from YAML: {e}", exc_info=True)
        return None


def load_yaml_config(yaml_path_or_text: Union[str, Path]) -> DeckConfig:
    """Load a YAML configuration from a path or YAML string."""

    if isinstance(yaml_path_or_text, (str, Path)) and Path(yaml_path_or_text).exists():
        raw = Path(yaml_path_or_text).read_text(encoding="utf-8")
    elif isinstance(yaml_path_or_text, (str, Path)):
        raw = str(yaml_path_or_text)
    else:
        raise TypeError("yaml_path_or_text must be a path or YAML string")

    try:
        data = yaml.safe_load(raw)
    except Exception as e:
        raise ValueError(f"Invalid deck config: {e}") from e

    if not isinstance(data, dict):
        raise ValueError("Invalid deck config: root must be a mapping")

    version = str(data.get("version", "1.0"))
    if version == "1.0":
        deck = data.get("deck", {})
        if "color_mode" in deck and "color_match_mode" not in deck:
            deck["color_match_mode"] = deck.pop("color_mode")
        data["version"] = "1.1"

    try:
        return DeckConfig.model_validate(data)
    except Exception as e:
        raise ValueError(f"Invalid deck config: {e}") from e
