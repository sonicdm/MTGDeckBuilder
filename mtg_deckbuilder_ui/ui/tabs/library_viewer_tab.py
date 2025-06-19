# mtg_deckbuilder_ui/ui/tabs/library_viewer_tab.py

"""Library viewer tab module."""

# Standard library imports
import logging

# Third-party imports
import gradio as gr

# Local application imports
from mtg_deckbuilder_ui.ui.ui_objects import UITab
from mtg_deckbuilder_ui.logic.library_viewer_callbacks import filter_library
from mtg_deckbuilder_ui.ui.tabs.library_viewer_components import (
    create_library_viewer_section,
)

# Set up logger
logger = logging.getLogger(__name__)


def create_library_viewer_tab() -> UITab:
    """Create the library viewer tab."""
    tab = UITab("Library Viewer")

    # Create main section
    main_section = create_library_viewer_section()
    tab.add_section(main_section)

    # Get components for wiring
    components = tab.get_component_map()

    # Wire up callbacks
    components["owned_only"].change(
        filter_library,
        inputs=[components["owned_only"]],
        outputs=[components["library_output"]],
    )

    # Initial load
    components["library_output"].value = filter_library(False)

    return tab
