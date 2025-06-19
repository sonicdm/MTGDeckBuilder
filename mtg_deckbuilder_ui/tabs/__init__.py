"""Tabs module."""

# Local application imports
from mtg_deckbuilder_ui.ui.tabs.deckbuilder_tab import create_deckbuilder_tab
from mtg_deckbuilder_ui.ui.tabs.config_manager_tab import create_config_manager_tab
from mtg_deckbuilder_ui.ui.tabs.deck_viewer_tab import create_deck_viewer_tab
from mtg_deckbuilder_ui.ui.tabs.inventory_manager_tab import (
    create_inventory_manager_tab,
)
from mtg_deckbuilder_ui.ui.tabs.library_viewer_tab import create_library_viewer_tab
# from mtg_deckbuilder_ui.ui.tabs.collection_viewer_tab import create_collection_viewer_tab

# from mtg_deckbuilder_ui.ui.tabs.settings_tab import create_settings_tab

__all__ = [
    "create_deckbuilder_tab",
    "create_config_manager_tab",
    "create_deck_viewer_tab",
    "create_inventory_manager_tab",
    "create_library_viewer_tab",
    # "create_collection_viewer_tab",
    # "create_settings_tab",
]
