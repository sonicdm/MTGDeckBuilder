# mtg_deckbuilder_ui/ui/tabs/inventory_manager_tab.py

"""Inventory manager tab module."""

# Standard library imports
import logging

# Third-party imports
import gradio as gr

# Local application imports
from mtg_deckbuilder_ui.ui.ui_objects import UITab
from mtg_deckbuilder_ui.logic.inventory_manager_callbacks import (
    on_refresh_inventories,
    load_inventory,
    save_inventory,
)
from mtg_deckbuilder_ui.ui.tabs.inventory_manager_components import (
    create_inventory_list_section,
    create_inventory_editor_section,
    create_inventory_controls_section,
)

# Set up logger
logger = logging.getLogger(__name__)


def create_inventory_manager_tab() -> UITab:
    """Create the inventory manager tab."""
    tab = UITab("Inventory Manager")

    # Create sections
    inventory_list_section = create_inventory_list_section()
    inventory_editor_section = create_inventory_editor_section()
    inventory_controls_section = create_inventory_controls_section()

    # Add sections to tab
    tab.add_section(inventory_list_section)
    tab.add_section(inventory_editor_section)
    tab.add_section(inventory_controls_section)

    # Get components for wiring
    components = tab.get_component_map()

    # Wire up inventory list callbacks
    components["inventory_manager_refresh"].click(
        on_refresh_inventories,
        inputs=[components["inventory_manager_list"]],
        outputs=components["inventory_manager_list"],
    )

    components["inventory_manager_list"].change(
        load_inventory,
        inputs=[components["inventory_manager_list"]],
        outputs=[
            components["inventory_manager_table"],
            components["inventory_manager_status"],
        ],
    )

    # Wire up inventory editor callbacks
    components["inventory_manager_save"].click(
        save_inventory,
        inputs=[
            components["inventory_manager_filename"],
            components["inventory_manager_table"],
        ],
        outputs=[components["inventory_manager_status"]],
    )

    return tab
