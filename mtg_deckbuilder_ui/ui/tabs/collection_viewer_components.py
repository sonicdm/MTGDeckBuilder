# mtg_deckbuilder_ui/ui/tabs/collection_viewer_components.py

import gradio as gr
from mtg_deckbuilder_ui.ui.ui_objects import UISection, UIElement, UIContainer
from mtg_deckbuilder_ui.app_config import app_config
from mtg_deckbuilder_ui.utils.ui_helpers import list_files_by_extension
import os
import json


def get_inventory_files():
    inventory_dir = app_config.get_path("inventory_dir", fallback="inventory_files")
    if not os.path.exists(inventory_dir):
        os.makedirs(inventory_dir, exist_ok=True)
    return list_files_by_extension(inventory_dir, [".txt"])


def get_card_data():
    keywords_path = app_config.get_path("keywords_json")
    cardtypes_path = app_config.get_path("cardtypes_json")

    mtg_keywords = set()
    card_types = set()
    card_subtypes = set()
    try:
        with open(keywords_path, "r", encoding="utf-8") as f:
            keywords_json = json.load(f)
        keywords_data = keywords_json.get("data", {})
        for k in ["abilityWords", "keywordAbilities", "keywordActions"]:
            mtg_keywords.update(keywords_data.get(k, []))
    except Exception:
        pass
    try:
        with open(cardtypes_path, "r", encoding="utf-8") as f:
            cardtypes_json = json.load(f)
        cardtypes_data = cardtypes_json.get("data", {})
        card_types.update([k.capitalize() for k in cardtypes_data.keys()])
        for v in cardtypes_data.values():
            card_subtypes.update(v.get("subTypes", []))
    except Exception:
        pass

    basic_types = [
        "Creature",
        "Instant",
        "Sorcery",
        "Enchantment",
        "Artifact",
        "Planeswalker",
        "Land",
        "Battle",
    ]
    supertypes = ["Basic", "Legendary", "Ongoing", "Snow", "World"]
    subtypes = sorted(card_subtypes)
    all_card_types = sorted(set(basic_types) | card_types | card_subtypes)
    card_keywords = sorted(mtg_keywords)

    return all_card_types, basic_types, supertypes, subtypes, card_keywords


def create_inventory_and_load_section() -> UISection:
    with UISection("inventory_and_load", "Inventory and Loading") as section:
        inventory_files = get_inventory_files()
        default_inventory = inventory_files[0] if inventory_files else None

        inventory_dropdown = UIElement(
            "inventory_dropdown",
            lambda: gr.Dropdown(
                choices=inventory_files,
                value=default_inventory,
                label="Select Inventory File (for owned cards)",
            ),
        )
        load_inventory_btn = UIElement(
            "load_inventory_btn", lambda: gr.Button("🔄 Load Inventory List")
        )
        load_collection_btn = UIElement(
            "load_collection_btn", lambda: gr.Button("📂 Load Collection")
        )
        status_msg = UIElement(
            "status_msg", lambda: gr.Markdown("_Status: Waiting for load..._")
        )

        layout = UIContainer(
            "group",
            children=[
                UIContainer(
                    "row",
                    children=[
                        UIContainer("column", scale=8, children=[inventory_dropdown]),
                        UIContainer(
                            "column",
                            scale=1,
                            children=[load_inventory_btn, load_collection_btn],
                        ),
                    ],
                ),
                status_msg,
            ],
        )
        section.set_layout(layout)
    return section


def create_color_filter_section() -> UISection:
    with UISection("color_filter", "Color Filters") as section:
        color_labels = {
            "W": "⚪ White",
            "U": "🔵 Blue",
            "B": "⚫ Black",
            "R": "🔴 Red",
            "G": "🟢 Green",
        }
        color_choices = [f"{v} ({k})" for k, v in color_labels.items()]

        color_filter = UIElement(
            "color_filter",
            lambda: gr.CheckboxGroup(choices=color_choices, label="Colors"),
        )
        color_mode = UIElement(
            "color_mode",
            lambda: gr.Dropdown(
                choices=["any", "subset", "exact"],
                value="any",
                label="Color Match Mode",
            ),
        )
        owned_only = UIElement(
            "owned_only",
            lambda: gr.Checkbox(label="Show only owned cards", value=False),
        )

        layout = UIContainer(
            "row",
            children=[
                UIContainer("column", scale=5, children=[color_filter]),
                UIContainer("column", scale=2, children=[color_mode]),
                UIContainer("column", scale=1, children=[owned_only]),
            ],
        )
        section.set_layout(layout)
    return section


def create_type_filter_section() -> UISection:
    _, basic_types, supertypes, subtypes, _ = get_card_data()

    with UISection("type_filter", "Type Filters") as section:
        basic_type_filter = UIElement(
            "basic_type_filter",
            lambda: gr.Dropdown(
                choices=["Any"] + basic_types, value="Any", label="Basic Type"
            ),
        )
        supertype_filter = UIElement(
            "supertype_filter",
            lambda: gr.Dropdown(
                choices=["Any"] + supertypes, value="Any", label="Supertype"
            ),
        )
        subtype_filter = UIElement(
            "subtype_filter",
            lambda: gr.Dropdown(
                choices=["Any"] + subtypes, value="Any", label="Subtype"
            ),
        )
        type_multi = UIElement(
            "type_multi",
            lambda: gr.Dropdown(
                choices=subtypes, label="Card Types (multi-select)", multiselect=True
            ),
        )

        layout = UIContainer(
            "row",
            children=[basic_type_filter, supertype_filter, subtype_filter, type_multi],
        )
        section.set_layout(layout)
    return section


def create_keyword_rarity_legality_filter_section() -> UISection:
    _, _, _, _, card_keywords = get_card_data()
    legalities = app_config.get_legalities_formats()

    with UISection(
        "keyword_rarity_legality_filter", "Keyword, Rarity, and Legality Filters"
    ) as section:
        keyword_multi = UIElement(
            "keyword_multi",
            lambda: gr.Dropdown(
                choices=card_keywords,
                label="Card Keywords (multi-select)",
                multiselect=True,
            ),
        )
        rarity_filter = UIElement(
            "rarity_filter",
            lambda: gr.Dropdown(
                choices=["Any", "common", "uncommon", "rare", "mythic"],
                value="Any",
                label="Rarity",
            ),
        )
        legality_filter = UIElement(
            "legality_filter",
            lambda: gr.Dropdown(
                choices=["Any"] + legalities, value="Any", label="Format Legality"
            ),
        )
        min_quantity = UIElement(
            "min_quantity",
            lambda: gr.Number(label="Minimum Owned Quantity", value=0, precision=0),
        )

        layout = UIContainer(
            "row",
            children=[keyword_multi, rarity_filter, legality_filter, min_quantity],
        )
        section.set_layout(layout)
    return section


def create_search_and_display_section() -> UISection:
    DEFAULT_DISPLAY_COLUMNS = ["Name", "Colors", "Set", "Rarity", "Type", "Owned Qty"]
    ALL_AVAILABLE_COLUMNS = sorted(
        [
            "Name",
            "Owned Qty",
            "Colors",
            "Color Identity",
            "Mana Cost",
            "Converted Mana Cost",
            "Type",
            "Supertypes",
            "Subtypes",
            "Keywords",
            "Text",
            "Flavor Text",
            "Power",
            "Toughness",
            "Abilities",
            "Set",
            "Set Name",
            "Rarity",
            "Artist",
            "Number",
            "Legalities",
            "Layout",
            "UID",
        ]
    )

    with UISection("search_and_display", "Search and Display") as section:
        name_search = UIElement(
            "name_search", lambda: gr.Textbox(label="Search by Name")
        )
        text_search = UIElement(
            "text_search", lambda: gr.Textbox(label="Search Name or Text")
        )
        clear_btn = UIElement("clear_btn", lambda: gr.Button("Clear Filters"))
        name_multi = UIElement(
            "name_multi",
            lambda: gr.Dropdown(
                label="Filter by Card Names (multi-select)", multiselect=True
            ),
        )
        collection_table = UIElement(
            "collection_table",
            lambda: gr.DataFrame(headers=DEFAULT_DISPLAY_COLUMNS, interactive=True),
        )
        display_columns = UIElement(
            "display_columns",
            lambda: gr.CheckboxGroup(
                choices=ALL_AVAILABLE_COLUMNS,
                value=DEFAULT_DISPLAY_COLUMNS,
                label="Display Columns",
            ),
        )
        export_csv_btn = UIElement("export_csv_btn", lambda: gr.Button("Export to CSV"))
        export_json_btn = UIElement(
            "export_json_btn", lambda: gr.Button("Export to JSON")
        )

        layout = UIContainer(
            "group",
            children=[
                UIContainer("row", children=[name_search, text_search, clear_btn]),
                name_multi,
                display_columns,
                collection_table,
                UIContainer("row", children=[export_csv_btn, export_json_btn]),
            ],
        )
        section.set_layout(layout)
    return section
