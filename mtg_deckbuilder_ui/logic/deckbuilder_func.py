"""Deckbuilder functions module."""

# Standard library imports
import logging
from typing import Dict, List, Optional, Tuple, Union, Any

# Third-party imports
import gradio as gr
import pandas as pd

# Local application imports
from mtg_deck_builder import (
    Deck,
    DeckConfig,
    CardRepository,
    InventoryRepository,
    get_session,
    build_deck_from_config,
)
from mtg_deckbuilder_ui.logic.deck_progress_callbacks import get_deck_builder_callbacks
from mtg_deckbuilder_ui.ui.config_sync import extract_config_from_ui

logger = logging.getLogger(__name__)


def build_deck(
    config: DeckConfig, status_update_fn: Optional[callable] = None
) -> Tuple[Optional[Deck], str]:
    """Build a deck from a DeckConfig.

    Args:
        config: DeckConfig object containing all deck building parameters
        status_update_fn: Optional callback for status updates

    Returns:
        Tuple of (Deck object or None if build failed, status message)
    """
    try:
        # Get database session
        session = get_session()

        # Initialize repositories
        card_repo = CardRepository(session)
        inventory_repo = InventoryRepository(session)

        # Get callbacks for tracking progress
        callbacks = get_deck_builder_callbacks(status_update_fn)

        # Build the deck
        deck = build_deck_from_config(
            deck_config=config,
            card_repo=card_repo,
            inventory_repo=inventory_repo,
            callbacks=callbacks,
        )

        if deck is None:
            return None, "Failed to build deck"

        # Check for warnings
        warnings = []
        if deck.unmet_conditions:
            warnings.append("Unmet conditions:")
            for condition in deck.unmet_conditions:
                warnings.append(f"- {condition}")

        if deck.warnings:
            warnings.append("Warnings:")
            for warning in deck.warnings:
                warnings.append(f"- {warning}")

        status = "\n".join(warnings) if warnings else "Deck built successfully"
        return deck, status

    except Exception as e:
        logger.error("[build_deck] Error building deck: %r", e, exc_info=True)
        return None, f"Error building deck: {str(e)}"
    finally:
        session.close()


def run_deckbuilder_from_ui(ui_state: Dict[str, Any]) -> Dict[str, Any]:
    """Run the deck builder from UI state.

    Args:
        ui_state: Dictionary containing UI component values

    Returns:
        Dict containing status and deck data
    """
    try:
        # Extract DeckConfig from UI state
        config = extract_config_from_ui(ui_state)

        # Build the deck
        deck, status = build_deck(config)

        if deck is None:
            return {"status": "error", "message": status, "deck": None}

        # Convert deck to dataframe for display
        deck_data = []
        for card in deck.cards:
            deck_data.append(
                {
                    "Name": card.name,
                    "Type": card.type_line,
                    "Mana Cost": card.mana_cost,
                    "Quantity": card.quantity,
                }
            )

        return {"status": "success", "message": status, "deck": pd.DataFrame(deck_data)}

    except Exception as e:
        logger.error("[run_deckbuilder_from_ui] Error: %r", e, exc_info=True)
        return {"status": "error", "message": f"Error: {str(e)}", "deck": None}


def on_inventory_selected(inventory_path: str) -> str:
    """Handle inventory file selection.

    Args:
        inventory_path: Path to selected inventory file

    Returns:
        Status message
    """
    try:
        # Get database session
        session = get_session()

        # Initialize inventory repository
        inventory_repo = InventoryRepository(session)

        # Load inventory
        inventory_repo.load_inventory(inventory_path)

        return f"Inventory loaded from {inventory_path}"

    except Exception as e:
        logger.error("[on_inventory_selected] Error: %r", e, exc_info=True)
        return f"Error loading inventory: {str(e)}"
    finally:
        session.close()


def update_card_table_columns(columns: List[str]) -> gr.update:
    """Update the card table columns.

    Args:
        columns: List of column names to display

    Returns:
        Gradio update object
    """
    return gr.update(columns=columns)


def on_send_to_deck_viewer(deck_state: Dict) -> Dict:
    """Send the current deck state to the deck viewer tab.

    Args:
        deck_state: Current deck state dictionary

    Returns:
        Updated deck state
    """
    return deck_state
