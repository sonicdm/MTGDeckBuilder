# mtg_deckbuilder_ui/logic/library_viewer_callbacks.py

"""Library viewer callbacks module."""

# Standard library imports
import logging

# Local application imports
from mtg_deck_builder.db import CardRepository, get_session

# Set up logger
logger = logging.getLogger(__name__)


def load_library():
    """Load all cards from the library."""
    with get_session() as session:
        card_repo = CardRepository(session=session)
        return card_repo.get_all_cards()


def filter_library(owned_only: bool) -> str:
    """Filter library cards based on ownership.

    Args:
        owned_only: Whether to show only owned cards

    Returns:
        String containing filtered card names
    """
    cards = load_library()
    if owned_only:
        cards = [card for card in cards if getattr(card, "owned_qty", 0) > 0]
    return "\n".join([card.name for card in cards])
