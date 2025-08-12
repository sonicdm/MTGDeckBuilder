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
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union, Callable, TypeVar, cast
import os
import traceback

import yaml
import random

from mtg_deck_builder.db import get_session
from mtg_deck_builder.db.repository import SummaryCardRepository
from mtg_deck_builder.models.deck import Deck
from mtg_deck_builder.models.deck_config import DeckConfig
from mtg_deck_builder.yaml_builder.deck_build_classes import BuildContext, DeckBuildContext
from mtg_deck_builder.yaml_builder.types import CallbackDict
from mtg_deck_builder.yaml_builder.helpers import (
    _handle_priority_cards,
    _handle_basic_lands,
    _fill_categories,
    _prune_overfilled_categories,
    _log_deck_composition,
    _filter_summary_repository,
    _handle_special_lands,
    _handle_fallback_strategy,
    _finalize_deck,
    _apply_card_constraints
)
from mtg_deck_builder.yaml_builder.helpers.card_scoring import score_card
from mtg_deck_builder.yaml_builder.helpers.mana_curve import _compute_mana_symbols

logger = logging.getLogger(__name__)

# Type variables for better type hinting
T = TypeVar('T')

def build_deck_from_config(
    deck_config: DeckConfig,
    summary_repo: SummaryCardRepository,
    callbacks: Optional[CallbackDict] = None,
    verbose: bool = False,
) -> Optional[Deck]:
    """Build a deck from a configuration object."""
    logger.info(f"Starting deck build for {deck_config.name}")
    logger.info(f"Deck configuration: colors={deck_config.colors}, size={deck_config.deck.size}, max_copies={deck_config.deck.max_card_copies}")
    
    # Initialize build context
    # Attach DeckConfig so downstream (API/UI) can access configuration and context
    deck = Deck(name=deck_config.name, config=deck_config)
    deck_build_context = DeckBuildContext(
        config=deck_config,
        summary_repo=summary_repo,
        deck=deck
    )
    build_context = BuildContext(
        deck_config=deck_config,
        summary_repo=summary_repo,
        callbacks=callbacks,
        deck_build_context=deck_build_context
    )
    
    try:
        # Seed RNG once per build for determinism
        seed_value = str(getattr(deck_config, 'seed', None) or deck_config.deck.name or 'mtg-deck-builder')
        rng = random.Random(seed_value)
        # Step 1: Apply deck-wide filters
        logger.info("[BuildPhase] Step 1: Applying deck-wide filters")
        _filter_summary_repository(build_context)
        
        # Step 2: Add priority cards (with global copy cap and logging)
        logger.info("[BuildPhase] Step 2: Adding priority cards")
        try:
            from collections import defaultdict
            max_copies = int(getattr(deck_config.deck, 'max_card_copies', 4) or 4)
            copies: Dict[str, int] = defaultdict(int)
            all_cards = build_context.summary_repo.get_all_cards()
            name_index = {str(getattr(c, 'name', '')): c for c in all_cards}
            for p in (deck_config.priority_cards or []):
                name = str(getattr(p, 'name', '') or '').strip()
                want = int(getattr(p, 'min_copies', 1) or 1)
                have = copies[name]
                add = max(0, min(want, max_copies - have))
                if add <= 0:
                    continue
                card = name_index.get(name)
                if not card:
                    if build_context.deck_build_context:
                        build_context.deck_build_context.build_log.append({"warning": f"priority_missing:{name}"})
                    continue
                if build_context.deck_build_context and build_context.deck_build_context.add_card(card, reason="priority_card", source="priority", quantity=add):
                    copies[name] += add
                    build_context.deck_build_context.log(f"Added priority {add}x {name}")
        except Exception:
            # Fallback to existing handler
            _handle_priority_cards(build_context)
        
        # Step 3: Apply card constraints
        logger.info("[BuildPhase] Step 3: Applying card constraints")
        _apply_card_constraints(build_context)
        
        # Step 4: Compute mana symbol distribution
        logger.info("[BuildPhase] Step 4: Computing mana symbol distribution")
        _compute_mana_symbols(build_context)
        
        # Step 5: Calculate available slots for non-land cards (after priority cards)
        current_cards = build_context.deck_build_context.get_total_cards() if build_context.deck_build_context else 0
        if build_context.mana_base and hasattr(build_context.mana_base, 'land_count'):
            target_lands = build_context.mana_base.land_count
            available_slots = deck_config.deck.size - target_lands - current_cards
        else:
            target_lands = 0
            available_slots = deck_config.deck.size - current_cards
            
        logger.info(f"Available slots for categories: {available_slots} (deck size: {deck_config.deck.size}, target lands: {target_lands}, current cards: {current_cards})")
        
        # Pre-check: category targets vs deck size and available non-land slots
        try:
            total_category_targets = sum(cat.target for cat in deck_config.categories.values())
        except Exception:
            total_category_targets = 0
        non_land_slots = available_slots
        if total_category_targets > deck_config.deck.size:
            logger.warning(
                f"Category targets ({total_category_targets}) exceed deck size ({deck_config.deck.size}). Targets will be scaled." 
            )
            if deck_build_context:
                deck_build_context.record_unmet_condition(
                    f"Category targets exceed deck size: {total_category_targets} > {deck_config.deck.size}"
                )
        if total_category_targets > non_land_slots:
            logger.warning(
                f"Category targets ({total_category_targets}) exceed available non-land slots ({non_land_slots}). Targets will be scaled."
            )
            if deck_build_context:
                deck_build_context.record_unmet_condition(
                    f"Targets exceed non-land slots: {total_category_targets} > {non_land_slots}"
                )

        # Step 6: Fill category roles with available slots
        logger.info("[BuildPhase] Step 6: Filling category roles")
        if build_context.deck_build_context:
            logger.info(f"Before categories: {build_context.deck_build_context.get_total_cards()} cards")
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
            logger.info(f"Before special lands: {build_context.deck_build_context.get_total_cards()} cards")
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
            logger.info(f"Before basic lands: {build_context.deck_build_context.get_total_cards()} cards")
        if build_context.mana_base:
            _handle_basic_lands(build_context)
        if build_context.deck_build_context:
            logger.info(f"After basic lands: {build_context.deck_build_context.get_total_cards()} cards")
        logger.info("[BuildPhase] Step 9: Applying fallback strategy")
        if build_context.deck_build_context:
            logger.info(f"Before fallback: {build_context.deck_build_context.get_total_cards()} cards")
        _handle_fallback_strategy(build_context)
        if build_context.deck_build_context:
            logger.info(f"After fallback: {build_context.deck_build_context.get_total_cards()} cards")
        # Step 10: Finalize deck
        logger.info("[BuildPhase] Step 10: Finalizing deck")
        _finalize_deck(build_context)
        
        # Validate final deck size
        if build_context.deck_build_context:
            final_size = build_context.deck_build_context.get_total_cards()
            if final_size != deck_config.deck.size:
                logger.warning(f"Deck size mismatch: expected {deck_config.deck.size}, got {final_size}")
                
                if final_size > deck_config.deck.size:
                    # Deck is too large - prune lowest scoring cards
                    _prune_overfilled_categories(build_context, deck_config.deck.size)
                elif final_size < deck_config.deck.size and build_context.mana_base:
                    # Deck is too small - add more basic lands
                    remaining_slots = deck_config.deck.size - final_size
                    _handle_basic_lands(build_context)
                
                # Verify size after adjustment
                final_size = build_context.deck_build_context.get_total_cards()
                if final_size != deck_config.deck.size:
                    logger.error(f"Failed to adjust deck to target size. Current size: {final_size}, target: {deck_config.deck.size}")
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
    yaml_data: Union[Dict[str, Any], str],
    summary_repo: SummaryCardRepository,
    callbacks: Optional[CallbackDict] = None,
    verbose: bool = False,
) -> Optional[Deck]:
    """Build a deck from YAML data.
    
    Args:
        yaml_data: YAML data or path
        summary_repo: Summary card repository
        callbacks: Optional callbacks for build stages
        verbose: Whether to enable detailed logging
        
    Returns:
        Deck object if successful, None otherwise
    """
    try:
        # Load configuration with migration and readable errors
        def _load_yaml(y: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
            if isinstance(y, str):
                if os.path.exists(y):
                    with open(y, 'r', encoding='utf-8') as f:
                        data = yaml.safe_load(f)
                else:
                    data = yaml.safe_load(y)
            else:
                data = y
            if not isinstance(data, dict):
                raise ValueError("Invalid deck config: YAML root must be a mapping")
            # migrate legacy keys
            root_version = str(data.get('version') or '').strip()
            deck_dict = data.get('deck') or {}
            if not root_version or root_version == '1.0':
                if isinstance(deck_dict, dict) and 'color_mode' in deck_dict and 'color_match_mode' not in deck_dict:
                    deck_dict['color_match_mode'] = deck_dict.pop('color_mode')
                data['version'] = '1.1'
                data['deck'] = deck_dict
            return data

        try:
            config_dict: Dict[str, Any] = _load_yaml(yaml_data)
            deck_config = DeckConfig.from_dict(config_dict)
        except Exception as e:
            raise ValueError(f"Invalid deck config: {e}")
        
        # Build deck (seeded RNG for determinism)
        # Create deck and context in build_deck_from_config; but seed RNG here by piggybacking on name/seed
        return build_deck_from_config(deck_config, summary_repo, callbacks, verbose)
        
    except Exception as e:
        logger.error(f"Error building deck from YAML: {e}", exc_info=True)
        return None


def load_yaml_config(yaml_path: Union[str, Path]) -> DeckConfig:
    """Load a YAML configuration file into a DeckConfig object.
    
    Args:
        yaml_path: Path to the YAML configuration file
        
    Returns:
        DeckConfig object initialized with the YAML data
        
    Raises:
        FileNotFoundError: If the YAML file doesn't exist
        yaml.YAMLError: If the YAML file is invalid
        ValueError: If the YAML data is invalid for deck configuration
    """
    yaml_path = Path(yaml_path)
    if not yaml_path.exists():
        raise FileNotFoundError(f"YAML configuration file not found: {yaml_path}")
        
    with open(yaml_path, 'r', encoding='utf-8') as f:
        try:
            yaml_data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"Invalid YAML in {yaml_path}: {e}")
            
    if not isinstance(yaml_data, dict):
        raise ValueError(f"Invalid YAML data in {yaml_path}: root must be a dictionary")
        
    return DeckConfig.model_validate(yaml_data)
