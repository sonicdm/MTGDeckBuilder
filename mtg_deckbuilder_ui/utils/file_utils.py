# mtg_deckbuilder_ui/utils/file_utils.py

"""
file_utils.py

Provides file utility functions for the MTG Deckbuilder application.
These functions help standardize operations like:
- File path operations and validation
- File extension management
- File listing and filtering
- Inventory file operations
"""
import os
import logging
from pathlib import Path
from typing import List, Optional
import gradio as gr
from mtg_deckbuilder_ui.app_config import app_config

# Set up logging
logger = logging.getLogger(__name__)


def get_full_path(directory: str, filename: str) -> Optional[str]:
    """Get the full path to a file, ensuring it exists in the specified directory.

    Args:
        directory: Base directory
        filename: Filename or relative path

    Returns:
        Full path to the file or None if filename is empty
    """
    directory = Path(directory)
    filename = Path(filename)
    if not filename:
        return directory if directory.is_dir() else None
    return directory / filename


def ensure_extension(filename: str, default_extension: str) -> str:
    """Ensure a filename has the specified extension.

    Args:
        filename: The filename to check
        default_extension: Extension to add if missing (include the dot)

    Returns:
        Filename with extension
    """
    if not filename.lower().endswith(default_extension.lower()):
        return f"{filename}{default_extension}"
    return filename


def list_files_by_extension(directory: str, extensions: List[str]) -> List[str]:
    """List all files in a directory with specified extensions.

    Args:
        directory: The directory to search
        extensions: List of file extensions to include (e.g. ['.txt', '.yaml'])

    Returns:
        List of filenames that match the extensions
    """
    if not os.path.exists(directory):
        logger.warning(f"Directory does not exist: {directory}")
        return []

    try:
        return [
            f
            for f in os.listdir(directory)
            if any(f.lower().endswith(ext.lower()) for ext in extensions)
        ]
    except Exception as e:
        logger.error(f"Error listing files in {directory}: {e}")
        return []


def refresh_dropdown(
    dropdown: gr.Dropdown, directory: str, extensions: List[str]
) -> gr.update:
    """Refresh a dropdown with files from a directory.

    Args:
        dropdown: The dropdown component to update
        directory: Directory to scan for files
        extensions: List of file extensions to include

    Returns:
        Gradio update object for the dropdown
    """
    files = list_files_by_extension(directory, extensions)
    return gr.update(choices=files)


def import_inventory_file(filename: str) -> List[str]:
    """Import card inventory from a text file.

    Args:
        filename: Name of the inventory file

    Returns:
        List of card names from the inventory file
    """
    inventory_path = app_config.get_path("inventory") / filename

    if not inventory_path.exists():
        logger.error(f"Inventory file not found: {inventory_path}")
        return []

    try:
        with open(inventory_path, "r", encoding="utf-8") as f:
            # Read lines and strip whitespace
            cards = [line.strip() for line in f.readlines()]
            # Filter out empty lines and comments
            cards = [card for card in cards if card and not card.startswith("#")]
            logger.info(f"Imported {len(cards)} cards from {filename}")
            return cards
    except Exception as e:
        logger.error(f"Error importing inventory file {filename}: {e}")
        return []


def save_inventory_file(filename: str, cards: List[str]) -> bool:
    """Save card inventory to a text file.

    Args:
        filename: Name of the inventory file
        cards: List of card names to save

    Returns:
        True if successful, False otherwise
    """
    inventory_path = app_config.get_path("inventory") / filename

    try:
        with open(inventory_path, "w", encoding="utf-8") as f:
            for card in cards:
                f.write(f"{card}\n")
        logger.info(f"Saved {len(cards)} cards to {filename}")
        return True
    except Exception as e:
        logger.error(f"Error saving inventory file {filename}: {e}")
        return False


def get_config_path(filename: str) -> Path:
    """Get full path to a config file in the deck configs directory.

    Args:
        filename: Name of the config file

    Returns:
        Full path to the config file
    """
    return app_config.get_path("decks") / filename


def list_config_files() -> List[str]:
    """List all config files in the deck configs directory.

    Returns:
        List of config filenames
    """
    return list_files_by_extension(str(app_config.get_path("decks")), [".yaml", ".yml"])


def list_inventory_files() -> List[str]:
    """List all inventory files in the inventory directory.

    Returns:
        List of inventory filenames
    """
    return list_files_by_extension(str(app_config.get_path("inventory")), [".txt"])
