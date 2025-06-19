"""
Example Callbacks for the YAML builder.
"""
import logging
from typing import Dict, Any, Optional
from mtg_deck_builder.models.deck_config import DeckConfig

logger = logging.getLogger(__name__)

def log_summary(selected: Dict[str, Any], **kwargs) -> None:
    """Log summary of selected cards."""
    logger.info(f"Selected {len(selected)} cards")
    for name, count in selected.items():
        logger.info(f"  {name}: {count}")


def assert_no_commons(selected: Dict[str, Any], **kwargs) -> None:
    """Assert that no common cards were selected."""
    for name, count in selected.items():
        if name.lower().endswith("(common)"):
            raise ValueError(f"Common card selected: {name}")


def ensure_card_present(
    card_name: str,
    min_copies: int = 1
) -> callable:
    """Create a callback that ensures a specific card is present.
    
    Args:
        card_name: Name of card to check for
        min_copies: Minimum number of copies required
        
    Returns:
        Callback function
    """
    def _callback(selected: Dict[str, Any], **kwargs) -> None:
        count = selected.get(card_name, 0)
        if count < min_copies:
            raise ValueError(
                f"Required card {card_name} not found or insufficient copies "
                f"(found {count}, need {min_copies})"
            )
    return _callback


def limit_card_copies(max_allowed: int = 4) -> callable:
    """Create a callback that limits card copies.
    
    Args:
        max_allowed: Maximum copies allowed per card
        
    Returns:
        Callback function
    """
    def _callback(selected: Dict[str, Any], **kwargs) -> None:
        for name, count in selected.items():
            if count > max_allowed:
                raise ValueError(
                    f"Too many copies of {name} (found {count}, max {max_allowed})"
                )
    return _callback


def log_special_lands(
    selected: Optional[list] = None,
    **kwargs
) -> None:
    """Log special lands selection."""
    if selected:
        logger.info(f"Selected {len(selected)} special lands:")
        for land in selected:
            logger.info(f"  {land}")


def log_deck_config_details(**kwargs) -> None:
    """Log deck configuration details."""
    if 'deck_config' in kwargs:
        config = kwargs['deck_config']
        logger.info("Deck configuration:")
        logger.info(f"  Name: {config.deck.name}")
        logger.info(f"  Colors: {config.deck.colors}")
        logger.info(f"  Size: {config.deck.size}")
        logger.info(f"  Max copies: {config.deck.max_card_copies}")
        if config.deck.mana_curve:
            logger.info(f"  Mana curve: {config.deck.mana_curve.min}-{config.deck.mana_curve.max}")
        if config.mana_base:
            logger.info(f"  Land count: {config.mana_base.land_count}")
        if config.categories:
            logger.info("  Categories:")
            for name, cat in config.categories.items():
                logger.info(f"    {name}: {cat.target} cards")


def log_repo_filter_state(**kwargs) -> None:
    """Log repository filter state."""
    if 'card_repo' in kwargs:
        repo = kwargs['card_repo']
        logger.info(f"Card repository state: {repo}")


def log_before_category_fill(**kwargs) -> None:
    """Log state before category fill."""
    if 'context' in kwargs:
        context = kwargs['context']
        logger.info(f"Before category fill: {context.get_total_cards()} cards selected")
        logger.info(f"Color counts: {context.get_color_counts()}")


def log_before_fallback_fill(**kwargs) -> None:
    """Log state before fallback fill."""
    if 'context' in kwargs:
        context = kwargs['context']
        logger.info(f"Before fallback fill: {context.get_total_cards()} cards selected")
        logger.info(f"Color counts: {context.get_color_counts()}")


def log_after_deck_config_load(**kwargs) -> None:
    """Log state after deck config load."""
    if 'deck_config' in kwargs:
        config = kwargs['deck_config']
        logger.info(f"Loaded deck config: {config.deck.name}")
        logger.info(f"Colors: {config.deck.colors}")
        logger.info(f"Size: {config.deck.size}")
        logger.info(f"Max copies: {config.deck.max_card_copies}")

