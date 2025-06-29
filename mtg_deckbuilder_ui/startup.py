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

logger = logging.getLogger(__name__)


def ensure_folders():
    """Create required application directories if they don't exist."""
    logger.info("Ensuring required directories exist...")

    # Use the exact directory keys from the configuration file.
    directory_keys = [
        "deck_configs_dir",
        "inventory_dir",
        "mtgjson_dir",
        "deck_outputs_dir",
    ]
    
    # Create directories
    for key in directory_keys:
        try:
            folder_path = app_config.get_path(key)
            folder_path.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Ensured directory exists: {folder_path}")
        except KeyError:
            # This can happen if a key is legitimately missing from the ini.
            logger.warning(f"Directory key '{key}' not found in config, skipping.")
        except Exception as e:
            logger.error(f"Failed to create directory for key '{key}': {e}")


def startup_init(ignore_database_updates=False, force_update=False):
    """Initialize application on startup.

    Args:
        ignore_json_updates: Whether to skip MTGJSON sync.
        force_update: Whether to force update the database schema.
    Returns:
        Dict containing sync results if sync was performed, None otherwise.
    """
    logger.info("Running startup initialization...")

    # Create required directories
    ensure_folders()

    # Run MTGJSON sync if not ignored
    sync_result = None
    if not ignore_database_updates:
        logger.info("Running MTGJSON sync...")
        sync_result = mtgjson_sync(force_update=force_update)
    else:
        logger.info("Skipping MTGJSON sync due to --ignore-json-updates flag.")

    # Note: Database initialization is now handled by the sync process
    # which downloads the SQLite file and builds summary cards
    logger.info("Startup initialization complete.")
    return sync_result
