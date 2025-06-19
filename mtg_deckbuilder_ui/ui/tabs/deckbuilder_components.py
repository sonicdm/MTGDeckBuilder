# mtg_deckbuilder_ui/ui/tabs/deckbuilder_components.py

"""Deckbuilder components module."""

# Standard library imports
import logging

# Third-party imports
import gradio as gr

# Local application imports
from mtg_deckbuilder_ui.ui.ui_objects import UISection, UIElement, UIContainer
from mtg_deckbuilder_ui.utils.file_utils import list_files_by_extension, get_full_path
from mtg_deckbuilder_ui.ui.config_sync import COLOR_DISPLAY_MAP
from mtg_deckbuilder_ui.app_config import app_config

# Set up logger
logger = logging.getLogger(__name__)


def get_config_dir():
    """Get the config directory path."""
    return str(app_config.get_path("deck_configs_dir"))


def get_config_files(config_dir):
    """Get a list of config files in the config directory."""
    return list_files_by_extension(config_dir, [".yaml", ".yml"])


def create_config_section() -> UISection:
    """Create the configuration section."""
    config_dir = get_config_dir()
    config_files = get_config_files(config_dir)

    with UISection("deckbuilder_config", "Deck Builder Configuration") as section:
        # Config selection
        config_select = UIElement(
            "deckbuilder_config_select",
            lambda: gr.Dropdown(config_files, label="Select Configuration"),
        )
        refresh_btn = UIElement("deckbuilder_config_refresh", lambda: gr.Button("🔄"))
        load_btn = UIElement("deckbuilder_config_load", lambda: gr.Button("Load"))

        # YAML editor
        yaml_content = UIElement(
            "deckbuilder_yaml_content",
            lambda: gr.Code(language="yaml", label="Configuration YAML"),
        )
        file_name_box = UIElement(
            "deckbuilder_config_filename",
            lambda: gr.Textbox(label="Configuration Name"),
        )

        # Layout
        layout = UIContainer(
            "column",
            children=[
                UIContainer("row", children=[config_select, refresh_btn, load_btn]),
                yaml_content,
                file_name_box,
            ],
        )
        section.set_layout(layout)
    return section


def create_inventory_section() -> UISection:
    """Create the inventory section."""
    with UISection("deckbuilder_inventory", "Deck Builder Inventory") as section:
        # Inventory selection
        inventory_select = UIElement(
            "deckbuilder_inventory_select",
            lambda: gr.Dropdown(label="Select Inventory"),
        )
        refresh_btn = UIElement(
            "deckbuilder_inventory_refresh", lambda: gr.Button("🔄")
        )
        load_btn = UIElement("deckbuilder_inventory_load", lambda: gr.Button("Load"))

        # Layout
        layout = UIContainer("row", children=[inventory_select, refresh_btn, load_btn])
        section.set_layout(layout)
    return section


def create_deck_section() -> UISection:
    """Create the deck section."""
    with UISection("deckbuilder_deck", "Deck Builder Deck") as section:
        # Deck list
        deck_list = UIElement(
            "deckbuilder_deck_list", lambda: gr.Dataframe(label="Deck Cards")
        )

        # Layout
        layout = UIContainer("column", children=[deck_list])
        section.set_layout(layout)
    return section


def create_controls_section() -> UISection:
    """Create the controls section."""
    with UISection("deckbuilder_controls", "Deck Builder Controls") as section:
        # Build button
        build_btn = UIElement("deckbuilder_build", lambda: gr.Button("Build Deck"))

        # Send to viewer button
        send_to_viewer_btn = UIElement(
            "deckbuilder_send_to_viewer", lambda: gr.Button("Send to Deck Viewer")
        )

        # Status message
        status_msg = UIElement(
            "deckbuilder_status", lambda: gr.Textbox(label="Status", interactive=False)
        )

        # Layout
        layout = UIContainer(
            "row", children=[build_btn, send_to_viewer_btn, status_msg]
        )
        section.set_layout(layout)
    return section


def create_deck_identity_section() -> UISection:
    with UISection("deck_identity", "Deck Identity") as section:
        name = UIElement("name", lambda: gr.Textbox(label="Deck Name"))
        colors = UIElement(
            "colors",
            lambda: gr.CheckboxGroup(
                choices=list(COLOR_DISPLAY_MAP.values()), label="Colors"
            ),
        )
        size = UIElement("size", lambda: gr.Number(label="Deck Size", value=60))
        max_card_copies = UIElement(
            "max_card_copies", lambda: gr.Number(label="Max Card Copies", value=4)
        )
        allow_colorless = UIElement(
            "allow_colorless",
            lambda: gr.Checkbox(label="Allow Colorless Cards", value=True),
        )
        color_match_mode = UIElement(
            "color_match_mode",
            lambda: gr.Radio(
                ["exact", "at_least"], label="Color Match Mode", value="at_least"
            ),
        )
        legalities = UIElement(
            "legalities", lambda: gr.Textbox(label="Legalities (comma-separated)")
        )

        layout = UIContainer(
            "group",
            children=[
                name,
                colors,
                size,
                max_card_copies,
                allow_colorless,
                color_match_mode,
                legalities,
            ],
        )
        section.set_layout(layout)
    return section


def create_mana_curve_section() -> UISection:
    with UISection("mana_curve", "Mana Curve") as section:
        mana_curve_min = UIElement(
            "mana_curve_min", lambda: gr.Number(label="Min Mana Curve", value=0)
        )
        mana_curve_max = UIElement(
            "mana_curve_max", lambda: gr.Number(label="Max Mana Curve", value=6)
        )
        mana_curve_shape = UIElement(
            "mana_curve_shape", lambda: gr.Textbox(label="Mana Curve Shape")
        )
        mana_curve_slope = UIElement(
            "mana_curve_slope",
            lambda: gr.Slider(
                label="Mana Curve Slope", minimum=0.1, maximum=2.0, value=1.0
            ),
        )

        layout = UIContainer(
            "group",
            children=[
                mana_curve_min,
                mana_curve_max,
                mana_curve_shape,
                mana_curve_slope,
            ],
        )
        section.set_layout(layout)
    return section


def create_card_categories_section() -> UISection:
    with UISection("card_categories", "Card Categories") as section:
        # This could be more dynamic, but for now, we'll hardcode some categories
        creatures_target = UIElement(
            "creatures_target", lambda: gr.Number(label="Creatures Target", value=20)
        )
        creatures_keywords = UIElement(
            "creatures_keywords", lambda: gr.Textbox(label="Creatures Keywords")
        )
        # ... add other elements for creatures, removal, etc.

        layout = UIContainer("group", children=[creatures_target, creatures_keywords])
        section.set_layout(layout)
    return section


def create_card_constraints_section() -> UISection:
    with UISection("card_constraints", "Card Constraints") as section:
        exclude_keywords = UIElement(
            "exclude_keywords", lambda: gr.Textbox(label="Exclude Keywords")
        )
        # ... add other rarity boost elements

        layout = UIContainer("group", children=[exclude_keywords])
        section.set_layout(layout)
    return section


def create_scoring_rules_section() -> UISection:
    with UISection("scoring_rules", "Scoring Rules") as section:
        scoring_text_match = UIElement(
            "scoring_text_match", lambda: gr.Textbox(label="Scoring Text Match")
        )
        # ... add other scoring elements

        layout = UIContainer("group", children=[scoring_text_match])
        section.set_layout(layout)
    return section


def create_priority_cards_section() -> UISection:
    with UISection("priority_cards", "Priority Cards") as section:
        priority_cards_yaml = UIElement(
            "priority_cards_yaml",
            lambda: gr.Code(language="yaml", label="Priority Cards (YAML)"),
        )

        layout = UIContainer("group", children=[priority_cards_yaml])
        section.set_layout(layout)
    return section


def create_mana_base_section() -> UISection:
    with UISection("mana_base", "Mana Base") as section:
        land_count = UIElement(
            "land_count", lambda: gr.Number(label="Land Count", value=24)
        )
        # ... add other mana base elements

        layout = UIContainer("group", children=[land_count])
        section.set_layout(layout)
    return section


def create_fallback_strategy_section() -> UISection:
    with UISection("fallback", "Fallback Strategy") as section:
        fill_priority = UIElement(
            "fill_priority", lambda: gr.Textbox(label="Fill Priority")
        )
        # ... add other fallback elements

        layout = UIContainer("group", children=[fill_priority])
        section.set_layout(layout)
    return section


def create_output_section() -> UISection:
    with UISection("output", "Output") as section:
        build_btn = UIElement(
            "build_btn", lambda: gr.Button("Build Deck", variant="primary")
        )
        build_status = UIElement(
            "build_status", lambda: gr.Textbox(label="Status", interactive=False)
        )
        card_table = UIElement(
            "card_table",
            lambda: gr.DataFrame(headers=["Name", "Cost", "Type", "Pow/Tgh", "Text"]),
        )
        deck_info = UIElement("deck_info", lambda: gr.Textbox(label="Deck Info"))
        deck_stats = UIElement("deck_stats", lambda: gr.Textbox(label="Deck Stats"))
        arena_export = UIElement(
            "arena_export", lambda: gr.Textbox(label="Arena Export")
        )
        deck_state = UIElement("deck_state", lambda: gr.State())
        copy_btn = UIElement("copy_btn", lambda: gr.Button("Copy to Clipboard"))
        send_to_viewer_btn = UIElement(
            "send_to_viewer_btn", lambda: gr.Button("Send to Deck Viewer")
        )

        layout = UIContainer(
            "group",
            children=[
                build_btn,
                build_status,
                card_table,
                deck_info,
                deck_stats,
                arena_export,
                copy_btn,
                send_to_viewer_btn,
            ],
        )
        section.set_layout(layout)
    return section
