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
    tab = UITab("Config Manager")

    # Create sections
    config_list_section = create_config_list_section()
    config_editor_section = create_config_editor_section()
    config_controls_section = create_config_controls_section()

    # Add sections to tab
    tab.add_section(config_list_section)
    tab.add_section(config_editor_section)
    tab.add_section(config_controls_section)

    # Get components for wiring
    components = tab.get_component_map()

    # Wire up config list callbacks
    components["config_manager_refresh"].click(
        refresh_files, outputs=components["config_manager_list"]
    )

    components["config_manager_list"].change(
        load_yaml_and_set_filename,
        inputs=[components["config_manager_list"]],
        outputs=[
            components["config_manager_yaml"],
            components["config_manager_filename"],
        ],
    )

    # Wire up config editor callbacks
    components["config_manager_save"].click(
        save_yaml_wrapper,
        inputs=[
            components["config_manager_filename"],
            components["config_manager_yaml"],
        ],
        outputs=[components["config_manager_status"]],
    )

    return tab
