"""Initialize the tabs module."""

from .deckbuilder_tab import create_deckbuilder_tab
from .config_manager_tab import create_config_manager_tab
from .inventory_manager_tab import create_inventory_manager_tab
from .deck_viewer_tab import create_deck_viewer_tab
from .library_viewer_tab import create_library_viewer_tab
# from .collection_viewer_tab import create_collection_viewer_tab
# from .settings_tab import create_settings_tab

__all__ = [
    "create_deckbuilder_tab",
    "create_config_manager_tab",
    "create_inventory_manager_tab",
    "create_deck_viewer_tab",
    "create_library_viewer_tab",
    # "create_collection_viewer_tab",
    # "create_settings_tab",
] 