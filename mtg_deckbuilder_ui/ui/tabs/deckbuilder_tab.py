# mtg_deckbuilder_ui/ui/tabs/deckbuilder_tab.py

"""Deckbuilder tab module."""

# Standard library imports
import logging

# Third-party imports
import gradio as gr

# Local application imports
from mtg_deckbuilder_ui.app_config import app_config
from mtg_deckbuilder_ui.logic.deckbuilder_func import (
    build_deck_with_validation,
    on_inventory_selected,
    update_card_table_columns,
    on_send_to_deck_viewer,
)
from mtg_deckbuilder_ui.logic.deck_validation_func import validate_and_analyze_generated_deck
from mtg_deckbuilder_ui.ui.config_sync import (
    on_refresh_configs,
    on_save_config,
    on_refresh_inventories,
)
from mtg_deckbuilder_ui.ui.ui_objects import UITab
from mtg_deckbuilder_ui.ui.tabs.deckbuilder_components import (
    create_config_section,
    create_inventory_section,
    create_deck_section,
    create_controls_section,
    create_output_section,
)
from mtg_deckbuilder_ui.logic.config_manager_callbacks import load_yaml_and_set_filename

# Set up logger
logger = logging.getLogger(__name__)


def create_deckbuilder_tab() -> UITab:
    """Create the deckbuilder tab."""

    def _wire_events(tab: UITab):
        """Wire up the event handlers for the deckbuilder tab."""
        elements = tab.get_elements()

        # Wire up config callbacks
        elements["deckbuilder_config_refresh"].click(
            lambda: on_refresh_configs(elements["deckbuilder_config_select"]),
            outputs=elements["deckbuilder_config_select"].component,
        )

        elements["deckbuilder_config_load"].click(
            load_yaml_and_set_filename,
            inputs=[elements["deckbuilder_config_select"].component],
            outputs=[
                elements["deckbuilder_yaml_content"].component,
                elements["deckbuilder_config_filename"].component,
            ],
        )

        # Wire up inventory callbacks
        elements["deckbuilder_inventory_refresh"].click(
            lambda: on_refresh_inventories(elements["deckbuilder_inventory_select"]),
            outputs=elements["deckbuilder_inventory_select"].component,
        )

        elements["deckbuilder_inventory_load"].click(
            on_inventory_selected,
            inputs=[elements["deckbuilder_inventory_select"].component],
            outputs=[elements["deckbuilder_status"].component],
        )

        # Wire up deck building with validation
        elements["build_btn"].click(
            build_deck_with_validation,
            inputs=[
                elements["deckbuilder_yaml_content"].component,
                elements["validate_format"].component,
                elements["validate_owned_only"].component,
            ],
            outputs=[
                elements["card_table"].component,
                elements["deck_info"].component,
                elements["deck_stats"].component,
                elements["arena_export"].component,
                elements["validation_summary"].component,
                elements["card_status_table"].component,
                elements["deck_analysis"].component,
                elements["deck_state"].component,
                elements["build_status"].component,
            ],
        )

        # Wire up send to viewer
        elements["send_to_viewer_btn"].click(
            on_send_to_deck_viewer,
            inputs=[elements["deck_state"].component],
            outputs=[elements["deck_state"].component],
        )

    tab = UITab("Deck Builder", on_render_wiring=_wire_events)

    # Create sections
    config_section = create_config_section()
    inventory_section = create_inventory_section()
    deck_section = create_deck_section()
    controls_section = create_controls_section()
    output_section = create_output_section()

    # Add sections to tab
    tab.add_section(config_section)
    tab.add_section(inventory_section)
    tab.add_section(deck_section)
    tab.add_section(controls_section)
    tab.add_section(output_section)

    return tab
