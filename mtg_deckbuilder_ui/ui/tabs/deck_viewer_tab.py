# mtg_deckbuilder_ui/ui/tabs/deck_viewer_tab.py

"""Deck viewer tab module."""

# Standard library imports
import logging

# Third-party imports
import gradio as gr

# Local application imports
from mtg_deckbuilder_ui.app_config import app_config
from mtg_deckbuilder_ui.logic.deck_viewer_func import (
    save_deck,
    on_load_deck,
    on_import_arena,
    export_arena,
    filter_card_table,
    update_card_display,
    update_card_table_columns,
)
from mtg_deckbuilder_ui.logic.deck_validation_func import validate_and_import_arena
from mtg_deckbuilder_ui.ui.ui_objects import UITab
from mtg_deckbuilder_ui.ui.tabs.deck_viewer_components import (
    create_deck_viewer_controls_section,
    create_deck_viewer_display_section,
    create_deck_viewer_table_section,
    create_deck_validation_section,
)

# Set up logger
logger = logging.getLogger(__name__)


def create_deck_viewer_tab() -> UITab:
    """Create the deck viewer tab."""
    tab = UITab("Deck Viewer")

    # Create sections
    controls_section = create_deck_viewer_controls_section()
    display_section = create_deck_viewer_display_section()
    table_section = create_deck_viewer_table_section()
    validation_section = create_deck_validation_section()

    # Add sections to tab
    tab.add_section(controls_section)
    tab.add_section(display_section)
    tab.add_section(table_section)
    tab.add_section(validation_section)

    # Get components for wiring
    components = tab.get_component_map()

    # Wire up deck loading
    components["load_btn"].click(
        on_load_deck,
        inputs=[
            components["deck_select"],
            components["card_table_columns"],
            components["filter_type"],
            components["filter_keyword"],
            components["search_text"],
            components["deck_state"],
        ],
        outputs=[
            components["deck_name_top"],
            components["deck_name"],
            components["deck_stats"],
            components["mana_curve_plot"],
            components["power_toughness_plot"],
            components["color_balance_plot"],
            components["type_counts_plot"],
            components["rarity_plot"],
            components["deck_properties"],
            components["card_table"],
            components["arena_out"],
            components["save_filename"],
        ],
    )

    # Wire up deck saving
    components["save_btn"].click(
        save_deck,
        inputs=[
            components["deck_state"],
            components["save_filename"],
            components["deck_dir"],
        ],
        outputs=[components["save_status"], components["deck_select"]],
    )

    # Wire up enhanced Arena import with validation
    components["import_btn"].click(
        validate_and_import_arena,
        inputs=[
            components["arena_import"],
            components["format_select"],
            components["inventory_file"],
            components["owned_only"],
            components["card_table_columns"],
        ],
        outputs=[
            components["validation_summary"],
            components["card_status_table"],
            components["deck_analysis"],
            components["deck_state"],
            components["import_status"],
        ],
    )

    # Wire up Arena export
    components["arena_btn"].click(
        export_arena,
        inputs=[components["deck_state"]],
        outputs=[components["arena_out"]],
    )

    # Wire up view mode toggle
    components["view_toggle"].change(
        update_card_display,
        inputs=[components["view_toggle"]],
        outputs=[components["card_table"], components["card_gallery"]],
    )

    # Wire up column selection
    components["card_table_columns"].change(
        update_card_table_columns,
        inputs=[components["card_table_columns"]],
        outputs=[components["card_table"]],
    )

    return tab
