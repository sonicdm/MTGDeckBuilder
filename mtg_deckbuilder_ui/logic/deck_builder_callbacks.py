"""
Callback functions for the deck builder process.

This module provides callback functions to track progress and status during deck building.
Each callback handles a specific part of the deck building process and updates the UI accordingly.
"""
import logging
from typing import Optional, Callable, Dict, Any

logger = logging.getLogger(__name__)

def get_deck_builder_callbacks(status_update_fn: Optional[Callable[[str], None]] = None) -> Dict[str, Callable]:
    """
    Creates a dictionary of callback functions for the deck building process.

    Args:
        status_update_fn: A function to call with status updates (for UI display)

    Returns:
        Dict of callback functions keyed by hook names
    """
    def after_deck_config_load(**kwargs):
        config = kwargs.get('config')
        deck_name = config.deck.name if config and hasattr(config, 'deck') and hasattr(config.deck, 'name') else "Unnamed"
        colors = ", ".join(config.deck.colors) if config and hasattr(config, 'deck') and hasattr(config.deck, 'colors') else ""
        message = f"Initialized deck: {deck_name} ({colors})"
        logger.info(message)
        if status_update_fn:
            status_update_fn(message)

    def after_inventory_load(**kwargs):
        inventory_items = kwargs.get('inventory_items', [])
        count = len(inventory_items) if inventory_items else 0
        message = f"Loaded inventory with {count} unique cards"
        logger.info(message)
        if status_update_fn:
            status_update_fn(message)

    def before_initial_repo_filter(**kwargs):
        message = "Preparing to filter card repository..."
        logger.info(message)
        if status_update_fn:
            status_update_fn(message)

    def after_initial_repo_filter(**kwargs):
        repo = kwargs.get('repo')
        cards_count = len(repo.get_all_cards()) if repo else 0
        message = f"Filtered repository: {cards_count} cards meet color and legality requirements"
        logger.info(message)
        if status_update_fn:
            status_update_fn(message)

    def after_priority_cards(**kwargs):
        selected = kwargs.get('selected', {})
        priority_count = len(selected)
        message = f"Added {priority_count} priority cards"
        logger.info(message)
        if status_update_fn:
            status_update_fn(message)

    def after_land_selection(**kwargs):
        selected = kwargs.get('selected', {})
        land_count = sum(1 for card in selected.values() if card.matches_type("land"))
        message = f"Selected {land_count} lands for mana base"
        logger.info(message)
        if status_update_fn:
            status_update_fn(message)

    def category_fill_progress(**kwargs):
        category = kwargs.get('category', '')
        filled = kwargs.get('filled', 0)
        target = kwargs.get('target', 0)
        message = f"Filling {category} category: {filled}/{target} cards"
        logger.info(message)
        if status_update_fn:
            status_update_fn(message)

    def after_categories(**kwargs):
        selected = kwargs.get('selected', {})
        card_count = sum(card.owned_qty for card in selected.values())
        message = f"Filled categories with {card_count} cards total"
        logger.info(message)
        if status_update_fn:
            status_update_fn(message)

    def before_fallback_fill(**kwargs):
        current_count = kwargs.get('current_card_count', 0)
        deck_size = kwargs.get('deck_size', 60)
        remaining = max(0, deck_size - current_count)
        if remaining > 0:
            message = f"Need {remaining} more cards to reach deck size of {deck_size}"
        else:
            message = f"Deck already has {current_count}/{deck_size} cards, no fallback needed"
        logger.info(message)
        if status_update_fn:
            status_update_fn(message)

    def before_finalize(**kwargs):
        selected = kwargs.get('selected', {})
        card_count = sum(card.owned_qty for card in selected.values())
        message = f"Finalizing deck with {card_count} cards"
        logger.info(message)
        if status_update_fn:
            status_update_fn(message)

    # Map all callbacks to their hook names
    return {
        "after_deck_config_load": after_deck_config_load,
        "after_inventory_load": after_inventory_load,
        "before_initial_repo_filter": before_initial_repo_filter,
        "after_initial_repo_filter": after_initial_repo_filter,
        "after_priority_cards": after_priority_cards,
        "after_land_selection": after_land_selection,
        "category_fill_progress": category_fill_progress,
        "after_categories": after_categories,
        "before_fallback_fill": before_fallback_fill,
        "before_finalize": before_finalize,
    }

