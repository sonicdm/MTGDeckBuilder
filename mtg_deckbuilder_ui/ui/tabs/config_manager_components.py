# mtg_deckbuilder_ui/ui/tabs/config_manager_components.py

"""Config manager components module."""

# Standard library imports
import logging

# Third-party imports
import gradio as gr

# Local application imports
from mtg_deckbuilder_ui.ui.ui_objects import UISection, UIElement, UIContainer
from mtg_deckbuilder_ui.utils.file_utils import list_files_by_extension, get_full_path

# Set up logger
logger = logging.getLogger(__name__)


def get_config_dir():
    """Get the config directory path."""
    return get_full_path("deck_configs")


def get_config_files(config_dir):
    """Get a list of config files in the config directory."""
    return list_files_by_extension(config_dir, [".yaml", ".yml"])


def create_config_list_section() -> UISection:
    """Create the config list section."""
    config_dir = get_config_dir()
    config_files = get_config_files(config_dir)

    with UISection("config_manager_list", "Config List") as section:
        # Config list
        config_list = UIElement(
            "config_manager_list",
            lambda: gr.Dropdown(config_files, label="Select Config"),
        )
        refresh_btn = UIElement("config_manager_refresh", lambda: gr.Button("🔄"))

        # Layout
        layout = UIContainer("row", children=[config_list, refresh_btn])
        section.set_layout(layout)
    return section


def create_config_editor_section() -> UISection:
    """Create the config editor section."""
    with UISection("config_manager_editor", "Config Editor") as section:
        # YAML editor
        yaml_editor = UIElement(
            "config_manager_yaml",
            lambda: gr.Code(language="yaml", label="YAML Content"),
        )

        # Layout
        layout = UIContainer("column", children=[yaml_editor])
        section.set_layout(layout)
    return section


def create_config_controls_section() -> UISection:
    """Create the config controls section."""
    with UISection("config_manager_controls", "Config Controls") as section:
        # Filename
        filename = UIElement(
            "config_manager_filename", lambda: gr.Textbox(label="Config Name")
        )

        # Save button
        save_btn = UIElement("config_manager_save", lambda: gr.Button("Save Config"))

        # Status message
        status_msg = UIElement(
            "config_manager_status",
            lambda: gr.Textbox(label="Status", interactive=False),
        )

        # Layout
        layout = UIContainer("row", children=[filename, save_btn, status_msg])
        section.set_layout(layout)
    return section
