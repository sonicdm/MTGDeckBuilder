# mtg_deckbuilder_ui/logic/deck_viewer_func.py

"""
deck_viewer_func.py

Provides the deck viewing functionality for the MTG Deckbuilder application.
This module contains the logic for viewing and analyzing decks.
"""

import logging
from typing import List, Tuple, Dict, Any, Optional
import pandas as pd
import gradio as gr
import json

from mtg_deck_builder.models.deck import Deck
from mtg_deckbuilder_ui.utils.ui_helpers import list_files_by_extension, get_full_path
from mtg_deckbuilder_ui.utils.plot_utils import (
    plot_mana_curve,
    plot_power_toughness_curve,
    plot_color_balance,
    plot_type_counts,
    plot_rarity_breakdown,
)

logger = logging.getLogger(__name__)


def load_deck_from_file(file_path: str) -> Deck:
    """Load a deck from a file."""
    try:
        with open(file_path, "r") as f:
            deck_data = f.read()
        return Deck.from_json(deck_data)
    except Exception as e:
        logger.error(f"Error loading deck from {file_path}: {e}")
        raise


def save_deck_to_file(deck: Deck, file_path: str) -> None:
    """Save a deck to a file."""
    try:
        deck_json = deck.to_json()
        with open(file_path, "w") as f:
            f.write(deck_json)
    except Exception as e:
        logger.error(f"Error saving deck to {file_path}: {e}")
        raise


def get_deck_stats(deck: Deck) -> dict:
    """Get statistics about a deck."""
    stats = {
        "total_cards": len(deck.cards),
        "type_counts": deck.count_card_types(),
        "color_counts": deck.count_colors(),
        "mana_curve": deck.get_mana_curve(),
        "power_toughness": deck.get_power_toughness_curve(),
    }
    return stats


def get_deck_files(directory: str) -> List[str]:
    """Get a list of deck files in a directory."""
    try:
        return list_files_by_extension(directory, [".json", ".txt"])
    except Exception as e:
        logger.error(f"Error getting deck files from {directory}: {e}")
        return []


def get_deck_file_path(directory: str, filename: str) -> str:
    """Get the full path to a deck file."""
    try:
        return get_full_path(directory, filename)
    except Exception as e:
        logger.error(f"Error getting deck file path for {filename}: {e}")
        raise


def get_deck_cards(deck: Deck) -> List[Tuple[str, str, int]]:
    """Get a list of cards in a deck."""
    cards = []
    for card in deck.cards:
        cards.append((card.name, card.type or "Unknown", card.owned_qty))
    return cards


def get_deck_mana_curve(deck: Deck) -> dict:
    """Get the mana curve of a deck."""
    try:
        return deck.get_mana_curve()
    except Exception as e:
        logger.error(f"Error getting mana curve: {e}")
        return {}


def get_deck_power_toughness(deck: Deck) -> dict:
    """Get the power/toughness curve of a deck."""
    try:
        return deck.get_power_toughness_curve()
    except Exception as e:
        logger.error(f"Error getting power/toughness curve: {e}")
        return {}


def get_deck_colors(deck: Deck) -> dict:
    """Get the color distribution of a deck."""
    try:
        return deck.count_colors()
    except Exception as e:
        logger.error(f"Error getting color distribution: {e}")
        return {}


def get_deck_types(deck: Deck) -> dict:
    """Get the type distribution of a deck."""
    try:
        return deck.count_card_types()
    except Exception as e:
        logger.error(f"Error getting type distribution: {e}")
        return {}


def get_deck_rarities(deck: Deck) -> dict:
    """Get the rarity distribution of a deck."""
    try:
        return deck.count_rarities()
    except Exception as e:
        logger.error(f"Error getting rarity distribution: {e}")
        return {}


def get_deck_sets(deck: Deck) -> dict:
    """Get the set distribution of a deck."""
    try:
        return deck.count_sets()
    except Exception as e:
        logger.error(f"Error getting set distribution: {e}")
        return {}


def get_deck_artists(deck: Deck) -> dict:
    """Get the artist distribution of a deck."""
    try:
        return deck.count_artists()
    except Exception as e:
        logger.error(f"Error getting artist distribution: {e}")
        return {}


def get_deck_legalities(deck: Deck) -> dict:
    """Get the legality information of a deck."""
    try:
        return deck.get_legalities()
    except Exception as e:
        logger.error(f"Error getting legality information: {e}")
        return {}


def get_deck_rulings(deck: Deck) -> List[str]:
    """Get the rulings of a deck."""
    try:
        return deck.get_rulings()
    except Exception as e:
        logger.error(f"Error getting rulings: {e}")
        return []


def get_deck_foreign_data(deck: Deck) -> dict:
    """Get the foreign language data of a deck."""
    try:
        return deck.get_foreign_data()
    except Exception as e:
        logger.error(f"Error getting foreign language data: {e}")
        return {}


def filter_card_table(
    df: pd.DataFrame,
    filter_type: str = None,
    filter_keyword: str = None,
    search_text: str = None,
) -> pd.DataFrame:
    """Filter the card table based on type, keyword, and search text.

    Args:
        df: DataFrame containing card data
        filter_type: Type to filter by (e.g. "Creature")
        filter_keyword: Keyword to filter by (e.g. "Flying")
        search_text: Text to search for in card names or text

    Returns:
        Filtered DataFrame
    """
    if df is None or df.empty:
        return df

    filtered_df = df.copy()

    # Filter by type
    if filter_type:
        filter_type = filter_type.lower()
        filtered_df = filtered_df[
            filtered_df["Type"].str.lower().str.contains(filter_type, na=False)
        ]

    # Filter by keyword
    if filter_keyword:
        filter_keyword = filter_keyword.lower()
        filtered_df = filtered_df[
            filtered_df["Keywords"].str.lower().str.contains(filter_keyword, na=False)
        ]

    # Filter by search text
    if search_text:
        search_text = search_text.lower()
        filtered_df = filtered_df[
            filtered_df["Name"].str.lower().str.contains(search_text, na=False)
            | filtered_df["Card Text"].str.lower().str.contains(search_text, na=False)
        ]

    return filtered_df


def load_deck_json(file_path: str) -> Dict[str, Any]:
    """Load a deck from a JSON file."""
    try:
        with open(file_path, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading deck from {file_path}: {e}")
        raise


def update_card_display(view_mode: str) -> Tuple[gr.update, gr.update]:
    """Update the visibility of card display components based on view mode.

    Args:
        view_mode: The selected view mode ('table' or 'grid')

    Returns:
        Tuple[gr.update, gr.update]: Updates for table and grid components
    """
    if view_mode == "table":
        return gr.update(visible=True), gr.update(visible=False)
    else:  # grid view
        return gr.update(visible=False), gr.update(visible=True)


def update_card_table_columns(selected_columns: List[str]) -> gr.update:
    """Update the visible columns in the card table.

    Args:
        selected_columns: List of column names to display

    Returns:
        gr.update: Update for the table component
    """
    if not selected_columns:
        selected_columns = ["name", "type", "mana_cost"]
    return gr.update(headers=selected_columns)


def save_deck(
    deck_state: Dict, filename: str, deck_dir: str
) -> Tuple[gr.update, gr.update]:
    """Save a deck and its configuration to disk.

    Args:
        deck_state: The deck state containing both deck and config
        filename: The filename to save as
        deck_dir: Directory to save the deck in

    Returns:
        Tuple of updates for UI components:
        - save_status: Status message
        - deck_select: Updated deck list
    """
    try:
        if not filename:
            return gr.update(value="Error: Please enter a filename"), gr.update()

        # Ensure filename has .json extension
        if not filename.endswith(".json"):
            filename += ".json"

        # Create full path
        deck_path = get_full_path(deck_dir, filename)

        # Save the deck state
        with open(deck_path, "w") as f:
            json.dump(deck_state, f, indent=2)

        # Update deck list
        deck_files = get_deck_files(deck_dir)

        return (
            gr.update(value=f"Successfully saved deck to {filename}"),
            gr.update(choices=deck_files, value=filename),
        )
    except Exception as e:
        logger.error(f"Error saving deck: {e}")
        return gr.update(value=f"Error saving deck: {str(e)}"), gr.update()


def on_load_deck(
    deck_file: str,
    selected_columns: List[str],
    filter_type: str,
    filter_keyword: str,
    search_text: str,
    deck_dir: str,
    deck_state: Optional[Dict] = None,
) -> Tuple[
    gr.update,
    gr.update,
    gr.update,
    gr.update,
    gr.update,
    gr.update,
    gr.update,
    gr.update,
    gr.update,
    gr.update,
    gr.update,
    gr.update,
]:
    """Handle loading a deck file or receiving deck state.

    Args:
        deck_file: Name of the deck file to load (None if loading from state)
        selected_columns: List of columns to display
        filter_type: Type to filter by
        filter_keyword: Keyword to filter by
        search_text: Text to search for
        deck_dir: Directory containing deck files
        deck_state: Optional deck state to load directly

    Returns:
        Tuple of updates for UI components
    """
    try:
        # Load deck data
        if deck_state:
            deck = Deck.from_dict(deck_state)
            config = deck_state.get("config", {})
        else:
            deck_path = get_full_path(deck_dir, deck_file)
            with open(deck_path, "r") as f:
                deck_data = json.load(f)
            deck = Deck.from_dict(deck_data)
            config = deck_data.get("config", {})

        # Create DataFrame
        df = deck.to_dataframe(columns=selected_columns)

        # Apply filters
        df = filter_card_table(df, filter_type, filter_keyword, search_text)

        # Generate plots
        mana_curve = plot_mana_curve(deck.mana_curve())
        power_toughness = plot_power_toughness_curve(deck.power_toughness_counts())
        color_balance = plot_color_balance(deck.color_balance())
        type_counts = plot_type_counts(deck.count_card_types())
        rarity_breakdown = plot_rarity_breakdown(deck.rarity_breakdown())

        # Format deck info
        deck_name = deck.name or "Unnamed Deck"
        deck_stats = f"Total Cards: {len(df)}\n"
        deck_stats += (
            f"Colors: {', '.join(deck.colors) if deck.colors else 'Colorless'}\n"
        )

        # Store the config in the deck state for saving
        deck._config = config

        # Create save filename from deck name
        save_filename = deck_name.lower().replace(" ", "_")

        return (
            gr.update(value=f"# {deck_name}"),  # deck_name_top
            gr.update(value=deck_name),  # deck_name
            gr.update(value=deck_stats),  # deck_stats
            gr.update(value=mana_curve),  # mana_curve_plot
            gr.update(value=power_toughness),  # power_toughness_plot
            gr.update(value=color_balance),  # color_balance_plot
            gr.update(value=type_counts),  # type_counts_plot
            gr.update(value=rarity_breakdown),  # rarity_plot
            gr.update(value=deck_stats),  # deck_properties
            gr.update(value=df),  # card_table
            gr.update(value=deck.to_arena_format()),  # arena_out
            gr.update(value=save_filename),  # save_filename
        )
    except Exception as e:
        logger.error(f"Error loading deck: {e}")
        return tuple(gr.update() for _ in range(12))


def on_import_arena(arena_text: str) -> Tuple[gr.update, gr.update]:
    """Handle Arena deck import.

    Args:
        arena_text: Text content from Arena export

    Returns:
        Tuple[gr.update, gr.update]: Updates for status and deck components
    """
    try:
        if not arena_text:
            return gr.update(value="No text provided"), gr.update()

        # TODO: Implement Arena import
        return gr.update(value="Arena import not implemented yet"), gr.update()
    except Exception as e:
        logger.error(f"Error importing Arena deck: {e}")
        return gr.update(value=f"Error: {str(e)}"), gr.update()


def export_arena(deck_data: Dict[str, Any]) -> str:
    """Export a deck to Arena format.

    Args:
        deck_data: Deck data dictionary

    Returns:
        Arena format string
    """
    try:
        # TODO: Implement Arena export
        return "Arena export not implemented yet"
    except Exception as e:
        logger.error(f"Error exporting to Arena: {e}")
        return f"Error: {str(e)}"
