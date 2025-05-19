import logging

from tests.conftest import INVENTORY_FILE


def get_database_path():
    """return db url relative to the current working directory
    salite:///working/dir/cards.db"""

    import os
    import sys
    # Get the current working directory
    cwd = os.getcwd()
    # Get the absolute path of the database file
    db_path = os.path.join(cwd, "cards.db")
    # Return the SQLite URL
    return db_path


# Centralized application configuration

# Directory paths
CONFIG_PRESETS_DIR = "config/presets"
DECK_CONFIGS_DIR = "deck_configs"  # Added for deck config YAMLs
INVENTORY_FILE_DIR = "inventory_files"
DATA_DIR = "data"
MTGJSON_DIR = f"{DATA_DIR}/mtgjson"
USER_UPLOADS_DIR = f"{DATA_DIR}/user_uploads"
LOGIC_DIR = "logic"
UI_DIR = "ui"
UTILS_DIR = "utils"
DATABASE_URL = get_database_path()  # SQLite database URL

# MTGJSON file paths
LOCAL_META_PATH = f"{MTGJSON_DIR}/Meta.json"
LOCAL_ALLPRINTINGS_PATH = f"{MTGJSON_DIR}/AllPrintings.json"

# MTGJSON URLs
MTGJSON_META_URL = "https://mtgjson.com/api/v5/Meta.json"
MTGJSON_ALLPRINTINGS_URL = "https://mtgjson.com/api/v5/AllPrintings.json.zip"

# Log level configuration
LOG_LEVEL = logging.INFO  # Change to logging.DEBUG for more verbose output

def configure_logging():
    logging.basicConfig(
        level=LOG_LEVEL,
        format="[%(levelname)s] %(asctime)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )


# Other config (add as needed)


