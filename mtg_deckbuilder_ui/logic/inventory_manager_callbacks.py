# mtg_deckbuilder_ui/logic/inventory_manager_callbacks.py

import os
import gradio as gr
from mtg_deckbuilder_ui.utils.file_utils import (
    list_files_by_extension,
    import_inventory_file,
    save_inventory_file,
)
from mtg_deckbuilder_ui.utils.ui_helpers import get_full_path, ensure_extension
from mtg_deckbuilder_ui.app_config import app_config
from mtg_deckbuilder_ui.utils.logging_config import get_logger

logger = get_logger(__name__)


def get_inventory_dir():
    inventory_path = app_config.get("inventory_path")  # Assuming this might exist
    if inventory_path and isinstance(inventory_path, str):
        inventory_dir = os.path.dirname(inventory_path)
        if not inventory_dir:
            logger.warning(
                f"Invalid inventory path provided: {inventory_path}, using default directory"
            )
            return app_config.get_path("inventory_dir")
        return inventory_dir
    return app_config.get_path("inventory_dir")


def on_refresh_inventories(inventory_dir):
    logger.debug(f"Refreshing inventory list from directory: {inventory_dir}")
    return gr.update(choices=list_files_by_extension(inventory_dir, [".txt"]))


def autofill_filename(selected_file):
    logger.debug(
        f"Autofilling filename field with: {selected_file or 'card inventory.txt'}"
    )
    return selected_file or "card inventory.txt"


def load_inventory(selected_file, inventory_dir):
    if not selected_file:
        logger.warning("Attempted to load inventory with no file selected")
        return [], gr.update(value="No file selected")

    logger.info(f"Loading inventory: {selected_file}")
    file_path = get_full_path(inventory_dir, selected_file)
    logger.debug(f"Full path for loading: {file_path}")

    try:
        rows = import_inventory_file(file_path)
        app_config.set_last_loaded_inventory(selected_file, section="InventoryManager")
        logger.info(f"Successfully loaded {len(rows)} cards from {selected_file}")
        return rows, gr.update(
            value=f"✅ Loaded {len(rows)} cards from {selected_file}"
        )
    except Exception as e:
        logger.error(f"Failed to load inventory {selected_file}: {e}", exc_info=True)
        return [[0, f"Error: {str(e)}"]], gr.update(
            value=f"❌ Failed to load {selected_file}: {str(e)}"
        )


def save_inventory(filename, table_data, inventory_dir):
    if not filename:
        logger.warning("Attempted to save inventory with no filename provided")
        return gr.update(value="❌ No filename provided")

    filename = ensure_extension(filename, ".txt")
    file_path = get_full_path(inventory_dir, filename)

    logger.info(f"Saving inventory to: {filename}")
    result = save_inventory_file(file_path, table_data)

    if not result:
        logger.error(f"Failed to save inventory to {filename}")
        return gr.update(value=f"❌ Failed to save inventory to {filename}")
    else:
        app_config.set_last_loaded_inventory(filename, section="InventoryManager")
        logger.info(f"Successfully saved inventory to {filename}")
        return gr.update(value=f"✅ Inventory saved to {filename}")


def get_default_inventory(inventory_dir):
    inventory_files = list_files_by_extension(inventory_dir, [".txt"])
    last_inventory = app_config.get_last_loaded_inventory(section="InventoryManager")
    if last_inventory and last_inventory in inventory_files:
        return last_inventory
    elif inventory_files:
        return inventory_files[0]
    return None
