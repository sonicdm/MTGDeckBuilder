"""Deckbuilder functions module."""

# Standard library imports
import logging
from typing import Dict, List, Optional, Tuple

# Third-party imports
import gradio as gr
import pandas as pd

# Local application imports
from mtg_deck_builder.models.deck import Deck
from mtg_deck_builder.models.deck_config import DeckConfig
from mtg_deck_builder.db.repository import SummaryCardRepository
from mtg_deck_builder.db import get_session
from mtg_deck_builder.yaml_builder.yaml_deckbuilder import build_deck_from_config
from mtg_deckbuilder_ui.logic.deck_progress_callbacks import get_deck_builder_callbacks
from mtg_deckbuilder_ui.logic.deck_validation_func import validate_and_analyze_generated_deck

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
        with get_session() as session:
            # Initialize repositories
            summary_repo = SummaryCardRepository(session)

            # Get callbacks for tracking progress
            callbacks = get_deck_builder_callbacks(status_update_fn)

            # Build the deck
            deck = build_deck_from_config(
                deck_config=config,
                summary_repo=summary_repo,
                callbacks=callbacks,
            )

            if deck is None:
                return None, "Failed to build deck"

            status = "Deck built successfully"
            return deck, status

    except Exception as e:
        logger.error("[build_deck] Error building deck: %r", e, exc_info=True)
        return None, f"Error building deck: {str(e)}"


def build_deck_with_validation(
    yaml_content: str,
    validate_format: str = "standard",
    validate_owned_only: bool = False,
) -> Tuple[
    pd.DataFrame,  # card_table
    str,  # deck_info
    str,  # deck_stats
    str,  # arena_export
    str,  # validation_summary
    pd.DataFrame,  # card_status_table
    str,  # deck_analysis
    Dict,  # deck_state
    str,  # build_status
]:
    """Build a deck from YAML content with validation.

    Args:
        yaml_content: YAML configuration string
        validate_format: Format to validate against
        validate_owned_only: Whether to only allow owned cards

    Returns:
        Tuple of output components for the UI
    """
    try:
        # Parse YAML into DeckConfig
        config = DeckConfig.from_yaml(yaml_content)
        
        # Build the deck
        deck, status = build_deck(config)
        
        if deck is None:
            # Return empty results on failure
            empty_df = pd.DataFrame(columns=["Name", "Cost", "Type", "Pow/Tgh", "Text"])
            empty_status_df = pd.DataFrame(columns=["Qty", "Name", "Status", "Reason", "Owned"])
            return (
                empty_df,  # card_table
                "Build failed",  # deck_info
                "No stats available",  # deck_stats
                "",  # arena_export
                f"Build failed: {status}",  # validation_summary
                empty_status_df,  # card_status_table
                "No analysis available",  # deck_analysis
                {},  # deck_state
                status,  # build_status
            )

        # Convert deck to dataframe for display
        deck_data = []
        for card_name, card in deck.cards.items():
            quantity = deck.get_quantity(card_name)
            deck_data.append({
                "Name": card.name,
                "Cost": getattr(card, 'mana_cost', '') or "",
                "Type": getattr(card, 'type_line', '') or "",
                "Pow/Tgh": f"{getattr(card, 'power', '') or ''}/{getattr(card, 'toughness', '') or ''}" if getattr(card, 'power', None) or getattr(card, 'toughness', None) else "",
                "Text": getattr(card, 'oracle_text', '') or "",
            })
        
        card_table = pd.DataFrame(deck_data)
        
        # Generate deck info and stats
        deck_info = f"Deck: {deck.name}\nSize: {deck.size()} cards"
        
        # Calculate basic stats
        total_cards = deck.size()
        land_count = sum(1 for card in deck.cards.values() if "Land" in (getattr(card, 'type_line', '') or ""))
        creature_count = sum(1 for card in deck.cards.values() if "Creature" in (getattr(card, 'type_line', '') or ""))
        spell_count = total_cards - land_count
        
        deck_stats = f"Total: {total_cards} | Lands: {land_count} | Creatures: {creature_count} | Spells: {spell_count}"
        
        # Generate Arena export
        arena_export = "\n".join([f"{deck.get_quantity(card_name)} {card.name}" for card_name, card in deck.cards.items()])
        
        # Validate the deck
        validation_updates = validate_and_analyze_generated_deck(
            deck=deck,
            format_name=validate_format,
            owned_only=validate_owned_only,
        )
        
        # Extract validation results from gr.update objects
        validation_summary = validation_updates[0].value if validation_updates[0].value else "No validation performed"
        card_status_table = validation_updates[1].value if validation_updates[1].value is not None else pd.DataFrame(columns=["Qty", "Name", "Status", "Reason", "Owned"])
        deck_analysis = validation_updates[2].value if validation_updates[2].value else "No analysis available"
        
        # Create deck state for other components
        deck_state = {
            "deck": deck,
            "validation_result": validation_updates,
            "card_table": card_table,
        }
        
        build_status = "Deck built and validated successfully"
        
        return (
            card_table,
            deck_info,
            deck_stats,
            arena_export,
            validation_summary,
            card_status_table,
            deck_analysis,
            deck_state,
            build_status,
        )
        
    except Exception as e:
        logger.error("[build_deck_with_validation] Error: %r", e, exc_info=True)
        error_msg = f"Error building deck: {str(e)}"
        
        # Return empty results on error
        empty_df = pd.DataFrame(columns=["Name", "Cost", "Type", "Pow/Tgh", "Text"])
        empty_status_df = pd.DataFrame(columns=["Qty", "Name", "Status", "Reason", "Owned"])
        
        return (
            empty_df,  # card_table
            "Build failed",  # deck_info
            "No stats available",  # deck_stats
            "",  # arena_export
            error_msg,  # validation_summary
            empty_status_df,  # card_status_table
            "No analysis available",  # deck_analysis
            {},  # deck_state
            error_msg,  # build_status
        )


def on_inventory_selected(inventory_path: str) -> str:
    """Handle inventory file selection.

    Args:
        inventory_path: Path to selected inventory file

    Returns:
        Status message
    """
    try:
        # Get database session
        with get_session() as session:
            # Load inventory using load_inventory_items
            from mtg_deck_builder.db.inventory import load_inventory_items
            load_inventory_items(inventory_path, session)
            return f"Inventory loaded from {inventory_path}"

    except Exception as e:
        logger.error("[on_inventory_selected] Error: %r", e, exc_info=True)
        return f"Error loading inventory: {str(e)}"


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
