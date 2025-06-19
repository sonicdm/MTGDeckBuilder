"""
startup.py

Handles application startup initialization including:
- Creating required directories
- Running MTGJSON sync
- Initializing database
"""

import logging
from pathlib import Path
from mtg_deckbuilder_ui.app_config import app_config
from mtg_deckbuilder_ui.utils.mtgjson_sync import mtgjson_sync
from mtg_deck_builder.db.bootstrap import bootstrap

logger = logging.getLogger(__name__)


def ensure_folders():
    """Create required application directories if they don't exist."""
    logger.info("Ensuring required directories exist...")

    # Get paths from config
    # data_dir = app_config.get_path("data_dir")
    mtgjson_dir = app_config.get_path("mtgjson_dir")
    inventory_dir = app_config.get_path("inventory_dir")

    # Create directories
    for folder in app_config.get_paths():
        if folder and folder.is_dir():
            Path(folder).mkdir(parents=True, exist_ok=True)
            logger.debug(f"Ensured directory exists: {folder}")


def startup_init(ignore_json_updates=False):
    """Initialize application on startup.

    Args:
        ignore_json_updates: Whether to skip MTGJSON sync.

    Returns:
        Dict containing sync results if sync was performed, None otherwise.
    """
    logger.info("Running startup initialization...")

    # Create required directories
    ensure_folders()

    # Run MTGJSON sync if not ignored
    sync_result = None
    if not ignore_json_updates:
        logger.info("Running MTGJSON sync...")
        sync_result = mtgjson_sync()
    else:
        logger.info("Skipping MTGJSON sync due to --ignore-json-updates flag.")

    # Get correct file paths from config
    json_path = app_config.get_path("allprintings")
    db_url = app_config.get_db_url()

    # Determine inventory file
    last_inventory = app_config.get_last_loaded_inventory()
    inventory_file = None
    if last_inventory:
        inventory_file = app_config.get_path("inventory_dir") / last_inventory
        logger.info(f"Using inventory file: {inventory_file}")

    logger.info(f"Initializing database with json_path={json_path}, db_url={db_url}")
    if inventory_file:
        bootstrap(json_path=json_path, inventory_path=inventory_file, db_url=db_url)
    else:
        bootstrap(json_path=json_path, db_url=db_url)

    logger.info("Startup initialization complete.")
    return sync_result
