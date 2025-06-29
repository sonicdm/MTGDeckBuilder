"""Config manager tab module."""

# Standard library imports
import logging

# Third-party imports
import gradio as gr

# Local application imports
from mtg_deckbuilder_ui.app_config import app_config
from mtg_deckbuilder_ui.logic.config_manager_callbacks import (
    load_yaml_and_set_filename,
    refresh_files,
    save_yaml_wrapper,
)
from mtg_deckbuilder_ui.ui.ui_objects import UITab
from mtg_deckbuilder_ui.ui.tabs.config_manager_components import (
    create_config_list_section,
    create_config_editor_section,
    create_config_controls_section,
)

# Set up logger
logger = logging.getLogger(__name__)


def create_config_manager_tab() -> UITab:
    """Create the config manager tab."""

    def _wire_events(tab: UITab):
        """Wire up the event handlers for the config manager tab."""
        elements = tab.get_elements()

        # Wire up config list callbacks
        elements["config_manager_refresh"].click(
            refresh_files, outputs=elements["config_manager_list"].component
        )

        elements["config_manager_list"].change(
            load_yaml_and_set_filename,
            inputs=[elements["config_manager_list"].component],
            outputs=[
                elements["config_manager_yaml"].component,
                elements["config_manager_filename"].component,
            ],
        )

        # Wire up config editor callbacks
        elements["config_manager_save"].click(
            save_yaml_wrapper,
            inputs=[
                elements["config_manager_filename"].component,
                elements["config_manager_yaml"].component,
            ],
            outputs=[elements["config_manager_status"].component],
        )

    tab = UITab("Config Manager", on_render_wiring=_wire_events)

    # Create sections
    config_list_section = create_config_list_section()
    config_editor_section = create_config_editor_section()
    config_controls_section = create_config_controls_section()

    # Add sections to tab
    tab.add_section(config_list_section)
    tab.add_section(config_editor_section)
    tab.add_section(config_controls_section)

    return tab
