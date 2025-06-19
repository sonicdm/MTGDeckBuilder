"""
Module for handling deck operations between tabs.
This module is now simplified since we've detached the deck viewer from the deckbuilder.
"""

import gradio as gr
from typing import Dict, Any, List, Tuple
from mtg_deck_builder.models.deck import Deck
from mtg_deck_builder.models.deck_config import DeckConfig
import pandas as pd

__all__ = ["extract_deck_config", "apply_deck_to_builder", "deck_to_viewer_outputs"]


def extract_deck_config(deck_obj: Deck) -> DeckConfig:
    """
    Extract a DeckConfig from a Deck object.

    Args:
        deck_obj: The Deck object to extract config from

    Returns:
        DeckConfig object
    """
    if not deck_obj:
        return None

    config = DeckConfig()
    config.deck.name = deck_obj.name
    config.deck.size = deck_obj.size()
    config.deck.max_card_copies = 4  # Default to 4 copies

    # Extract colors
    colors = []
    for card in deck_obj.cards:
        for color in card.colors:
            if color not in colors:
                colors.append(color)
    config.deck.colors = colors

    # Extract other properties as needed
    return config


def apply_deck_to_builder(
    deck_obj: Deck, ui_map: Dict[str, gr.Component], apply_config_fn
) -> Dict[str, Any]:
    """
    Apply a deck's configuration to the builder UI.

    Args:
        deck_obj: The Deck object to apply
        ui_map: Dictionary of UI components
        apply_config_fn: Function to apply config to UI

    Returns:
        Dictionary of UI updates
    """
    if not deck_obj:
        return {}

    config = extract_deck_config(deck_obj)
    if not config:
        return {}

    return apply_config_fn(config, ui_map)


def safe_to_str(value):
    """Safely convert any value to a string representation."""
    if value is None:
        return ""
    elif isinstance(value, (list, tuple, set)):
        # Handle nested lists (like priority_cards)
        if value and isinstance(value[0], (list, tuple)):
            return "\n".join(f"- {safe_to_str(item)}" for item in value)
        # Handle empty lists
        if not value:
            return ""
        # Handle regular lists
        return ", ".join(str(x) for x in value)
    elif isinstance(value, dict):
        # Handle empty dicts
        if not value:
            return ""
        # Format dict items as key-value pairs
        return "\n".join(f"- {k}: {safe_to_str(v)}" for k, v in value.items())
    return str(value)


def dict_to_md_list(d: dict) -> str:
    """Convert a dictionary to a markdown list string."""
    if not d:
        return "(none)"
    return "\n".join(f"- {k}: {safe_to_str(v)}" for k, v in d.items())


def deck_to_viewer_outputs(
    deck_obj: Deck, selected_columns: List[str]
) -> Tuple[str, str, str, str, str, str, pd.DataFrame, str, str]:
    """
    Convert a Deck object to viewer tab outputs.

    Args:
        deck_obj: The Deck object to convert
        selected_columns: List of columns to display in the viewer

    Returns:
        Tuple of viewer outputs:
        - deck_name_top: Deck name for top display
        - deck_name: Deck name
        - deck_stats: Deck statistics
        - mana_curve_plot: Mana curve plot
        - power_toughness_plot: Power/toughness plot
        - deck_properties: Deck properties
        - card_table: Card table DataFrame
        - deck_summary: Deck summary
        - arena_out: Arena export string
    """
    try:
        # Get deck name
        deck_name = getattr(deck_obj, "name", "Unnamed Deck")
        deck_name_top = f"# {deck_name}"
        deck_name_md = f"## {deck_name}"

        # Get deck stats
        stats = {
            "total_cards": deck_obj.size(),
            "avg_mana_value": round(deck_obj.average_mana_value(), 2),
            "color_balance": deck_obj.color_balance(),
            "type_counts": deck_obj.count_card_types(),
            "ramp_count": deck_obj.count_mana_ramp(),
            "lands": deck_obj.count_lands(),
        }
        deck_stats = "\n".join(
            [
                f"Total Cards: {safe_to_str(stats['total_cards'])}",
                f"Average Mana Value: {safe_to_str(stats['avg_mana_value'])}",
                f"Color Balance: {safe_to_str(stats['color_balance'])}",
                f"Type Counts: {safe_to_str(stats['type_counts'])}",
                f"Ramp Count: {safe_to_str(stats['ramp_count'])}",
                f"Lands: {safe_to_str(stats['lands'])}",
            ]
        )

        # Get plots
        from mtg_deckbuilder_ui.utils.plot_utils import (
            plot_mana_curve,
            plot_power_toughness_curve,
        )

        mana_curve_plot = plot_mana_curve(deck_obj)
        power_toughness_plot = plot_power_toughness_curve(deck_obj)

        # Get deck properties
        deck_properties = "\n".join(
            [
                f"Name: {deck_name}",
                f"Size: {stats['total_cards']}",
                f"Colors: {', '.join(deck_obj.colors) if deck_obj.colors else 'Colorless'}",
            ]
        )

        # Get card table
        card_table = deck_obj.to_dataframe(columns=selected_columns)

        # Get deck summary
        deck_summary = f"Deck Summary:\n{deck_stats}"

        # Get Arena export
        arena_out = deck_obj.to_arena_format()

        return (
            deck_name_top,
            deck_name_md,
            deck_stats,
            mana_curve_plot,
            power_toughness_plot,
            deck_properties,
            card_table,
            deck_summary,
            arena_out,
        )
    except Exception as e:
        print(f"Error in deck_to_viewer_outputs: {e}")
        return None, None, None, None, None, None, None, None, None
