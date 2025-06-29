# mtg_deckbuilder_ui/ui/tabs/inventory_manager_components.py

"""Inventory manager components module."""

# Standard library imports
import logging

# Third-party imports
import gradio as gr

# Local application imports
from mtg_deckbuilder_ui.ui.ui_objects import UISection, UIElement, UIContainer
from mtg_deckbuilder_ui.logic.inventory_manager_callbacks import (
    get_inventory_dir,
    get_default_inventory,
)
from mtg_deckbuilder_ui.utils.file_utils import list_files_by_extension

# Set up logger
logger = logging.getLogger(__name__)


def create_inventory_list_section() -> UISection:
    """Create the inventory list section."""
    inventory_dir = get_inventory_dir()
    inventory_files = list_files_by_extension(inventory_dir, [".txt"])
    default_inventory = get_default_inventory(inventory_dir)

    with UISection("inventory_manager_list", "Inventory List") as section:
        # Inventory list
        inventory_list = UIElement(
            "inventory_manager_list",
            lambda: gr.Dropdown(
                [str(f) for f in inventory_files],
                value=str(default_inventory) if default_inventory else None,
                label="Select Inventory",
            ),
        )
        refresh_btn = UIElement("inventory_manager_refresh", lambda: gr.Button("🔄"))

        section.add_element(inventory_list)
        section.add_element(refresh_btn)

        # Layout
        layout = UIContainer("row", children=[inventory_list, refresh_btn])
        section.set_layout(layout)
    return section


def create_inventory_editor_section() -> UISection:
    """Create the inventory editor section."""
    with UISection("inventory_manager_editor", "Inventory Editor") as section:
        # Inventory table
        inventory_table = UIElement(
            "inventory_manager_table",
            lambda: gr.Dataframe(
                headers=["Quantity", "Card Name"],
                datatype=["number", "str"],
                col_count=(2, "fixed"),
                row_count=(10, "dynamic"),
                label="Inventory",
            ),
        )

        section.add_element(inventory_table)

        # Layout
        layout = UIContainer("column", children=[inventory_table])
        section.set_layout(layout)
    return section


def create_inventory_controls_section() -> UISection:
    """Create the inventory controls section."""
    with UISection("inventory_manager_controls", "Inventory Controls") as section:
        # Filename
        filename = UIElement(
            "inventory_manager_filename", lambda: gr.Textbox(label="Inventory Name")
        )

        # Save button
        save_btn = UIElement(
            "inventory_manager_save", lambda: gr.Button("Save Inventory")
        )

        # Status message
        status_msg = UIElement(
            "inventory_manager_status",
            lambda: gr.Textbox(label="Status", interactive=False),
        )

        section.add_element(filename)
        section.add_element(save_btn)
        section.add_element(status_msg)

        # Layout
        layout = UIContainer("row", children=[filename, save_btn, status_msg])
        section.set_layout(layout)
    return section
