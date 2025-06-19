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

from mtg_deck_builder.db import get_session
from mtg_deck_builder.db.repository import SummaryCardRepository, CardRepository
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
    deck = Deck(name=deck_config.name)
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
        
        # Step 5: Calculate available slots for non-land cards
        if build_context.mana_base and hasattr(build_context.mana_base, 'land_count'):
            target_lands = build_context.mana_base.land_count
            available_slots = deck_config.deck.size - target_lands
        else:
            target_lands = 0
            available_slots = deck_config.deck.size
            
        # Step 6: Fill category roles with available slots
        logger.info("[BuildPhase] Step 6: Filling category roles")
        if build_context.deck_build_context:
            logger.info(f"Before categories: {build_context.deck_build_context.get_total_cards()} cards")
        _fill_categories(build_context, available_slots)
        if build_context.deck_build_context:
            logger.info(f"After categories: {build_context.deck_build_context.get_total_cards()} cards")

        # Step 7: Add special lands
        logger.info("[BuildPhase] Step 7: Adding special lands")
        if build_context.deck_build_context:
            logger.info(f"Before special lands: {build_context.deck_build_context.get_total_cards()} cards")
        if build_context.mana_base and build_context.mana_base.special_lands:
            _handle_special_lands(build_context)
        if build_context.deck_build_context:
            logger.info(f"After special lands: {build_context.deck_build_context.get_total_cards()} cards")
            
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
            
        return build_context.deck_build_context.deck if build_context.deck_build_context else None
        
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
        # Load configuration
        config_dict: Dict[str, Any]
        if isinstance(yaml_data, str):
            if os.path.exists(yaml_data):
                with open(yaml_data, 'r') as f:
                    config_dict = yaml.safe_load(f)
            else:
                config_dict = yaml.safe_load(yaml_data)
        else:
            config_dict = yaml_data
                
        # Create deck config
        deck_config = DeckConfig.from_dict(config_dict)
        
        # Build deck
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
