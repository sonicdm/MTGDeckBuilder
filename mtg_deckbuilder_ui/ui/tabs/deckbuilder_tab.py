# mtg_deckbuilder_ui/ui/tabs/deckbuilder_tab.py

"""Deckbuilder tab module."""

# Standard library imports
import logging

# Third-party imports
import gradio as gr

# Local application imports
from mtg_deckbuilder_ui.app_config import app_config
from mtg_deckbuilder_ui.logic.deckbuilder_func import (
    build_deck,
    on_inventory_selected,
    update_card_table_columns,
    on_send_to_deck_viewer,
)
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
)
from mtg_deckbuilder_ui.logic.config_manager_callbacks import load_yaml_and_set_filename

# Set up logger
logger = logging.getLogger(__name__)


def create_deckbuilder_tab() -> UITab:
    """Create the deckbuilder tab."""
    tab = UITab("Deck Builder")

    # Create sections
    config_section = create_config_section()
    inventory_section = create_inventory_section()
    deck_section = create_deck_section()
    controls_section = create_controls_section()

    # Add sections to tab
    tab.add_section(config_section)
    tab.add_section(inventory_section)
    tab.add_section(deck_section)
    tab.add_section(controls_section)

    # Get components for wiring
    components = tab.get_component_map()

    # Wire up config callbacks
    components["deckbuilder_config_refresh"].click(
        lambda: on_refresh_configs(components["deckbuilder_config_select"]),
        outputs=components["deckbuilder_config_select"],
    )

    components["deckbuilder_config_load"].click(
        load_yaml_and_set_filename,
        inputs=[components["deckbuilder_config_select"]],
        outputs=[
            components["deckbuilder_yaml_content"],
            components["deckbuilder_config_filename"],
        ],
    )

    # Wire up inventory callbacks
    components["deckbuilder_inventory_refresh"].click(
        lambda: on_refresh_inventories(components["deckbuilder_inventory_select"]),
        outputs=components["deckbuilder_inventory_select"],
    )

    components["deckbuilder_inventory_load"].click(
        on_inventory_selected,
        inputs=[components["deckbuilder_inventory_select"]],
        outputs=[components["deckbuilder_status"]],
    )

    # Wire up deck building
    components["deckbuilder_build"].click(
        build_deck,
        inputs=[components["deckbuilder_yaml_content"]],
        outputs=[components["deckbuilder_deck_list"], components["deckbuilder_status"]],
    )

    # Wire up send to viewer
    components["deckbuilder_send_to_viewer"].click(
        on_send_to_deck_viewer,
        inputs=[components["deckbuilder_deck_list"]],
        outputs=[components["deckbuilder_deck_list"]],
    )

    return tab
