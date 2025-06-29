# mtg_deckbuilder_ui/logic/inventory_manager_callbacks.py

import gradio as gr
from pathlib import Path
from mtg_deckbuilder_ui.utils.file_utils import (
    list_files_by_extension,
    import_inventory_file,
    save_inventory_file,
)
from mtg_deckbuilder_ui.utils.ui_helpers import get_full_path, ensure_extension
from mtg_deckbuilder_ui.app_config import app_config
from mtg_deckbuilder_ui.utils.logging_config import get_logger
from typing import Optional

logger = get_logger(__name__)


def get_inventory_dir() -> Path:
    """Get the inventory directory path."""
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
        # Load inventory for display
        rows = import_inventory_file(str(file_path))
        
        # Load inventory into database
        from mtg_deck_builder.db import get_session
        from mtg_deck_builder.db.mtgjson_models.inventory import load_inventory_items
        
        with get_session() as session:
            load_inventory_items(str(file_path), session)
            logger.info(f"Inventory loaded into database from {selected_file}")
        
        logger.info(f"Successfully loaded {len(rows)} cards from {selected_file}")
        return rows, gr.update(
            value=f"✅ Loaded {len(rows)} cards from {selected_file} (and into database)"
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
    result = save_inventory_file(str(file_path), table_data)

    if not result:
        logger.error(f"Failed to save inventory to {filename}")
        return gr.update(value=f"❌ Failed to save inventory to {filename}")
    else:
        logger.info(f"Successfully saved inventory to {filename}")
        return gr.update(value=f"✅ Inventory saved to {filename}")


def get_default_inventory(inventory_dir):
    inventory_files = list_files_by_extension(inventory_dir, [".txt"])
    if inventory_files:
        return inventory_files[0]
    return None
