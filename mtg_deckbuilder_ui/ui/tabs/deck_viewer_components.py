# mtg_deckbuilder_ui/ui/tabs/deck_viewer_components.py

"""Deck viewer components module."""

# Standard library imports
import logging

# Third-party imports
import gradio as gr

# Local application imports
from mtg_deckbuilder_ui.ui.ui_objects import UISection, UIElement, UIContainer
from mtg_deckbuilder_ui.logic.deck_viewer_callbacks import get_deck_files, get_deck_dir

# Set up logger
logger = logging.getLogger(__name__)


def create_deck_viewer_controls_section() -> UISection:
    """Create the deck viewer controls section."""
    deck_dir = get_deck_dir()
    deck_files = get_deck_files(deck_dir)
    all_columns = [
        "Name",
        "Type",
        "Rarity",
        "Legalities",
        "CMC",
        "Cost",
        "Colors",
        "Power/Toughness",
        "Qty",
        "Card Text",
    ]
    default_columns = ["Name", "Type", "Qty", "Colors"]

    with UISection("deck_viewer_controls", "Deck Viewer Controls") as section:
        # Deck selection and loading
        deck_select = UIElement(
            "deck_select", lambda: gr.Dropdown(deck_files, label="Select Deck to View")
        )
        load_btn = UIElement("load_btn", lambda: gr.Button("Load Deck"))

        # Deck saving
        save_filename = UIElement(
            "save_filename",
            lambda: gr.Textbox(label="Save As", placeholder="Enter filename..."),
        )
        save_btn = UIElement("save_btn", lambda: gr.Button("Save Deck"))
        save_status = UIElement(
            "save_status", lambda: gr.Textbox(label="Save Status", interactive=False)
        )
        deck_state = UIElement(
            "deck_state", lambda: gr.State()
        )  # Store current deck state

        # Arena import/export
        arena_import = UIElement(
            "arena_import",
            lambda: gr.Textbox(label="Paste Arena Import String", lines=6),
        )
        import_btn = UIElement("import_btn", lambda: gr.Button("Import Arena Deck"))

        # Display controls
        card_table_columns = UIElement(
            "card_table_columns",
            lambda: gr.Dropdown(
                choices=all_columns,
                value=default_columns,
                label="Select Columns to Display",
                multiselect=True,
            ),
        )
        view_toggle = UIElement(
            "view_toggle",
            lambda: gr.Radio(
                choices=["Table View", "Card View"],
                value="Table View",
                label="Display Mode",
            ),
        )

        # Deck summary and filtering
        deck_summary = UIElement(
            "deck_summary", lambda: gr.Markdown(label="Deck Summary")
        )
        filter_type = UIElement(
            "filter_type", lambda: gr.Textbox(label="Filter by Type")
        )
        filter_keyword = UIElement(
            "filter_keyword", lambda: gr.Textbox(label="Filter by Keyword")
        )
        search_text = UIElement("search_text", lambda: gr.Textbox(label="Search Text"))

        # Layout
        layout = UIContainer(
            "column",
            children=[
                # Deck selection row
                UIContainer("row", children=[deck_select, load_btn]),
                # Save controls row
                UIContainer("row", children=[save_filename, save_btn, save_status]),
                # Arena controls
                UIContainer("row", children=[arena_import, import_btn]),
                # Display controls
                UIContainer("row", children=[card_table_columns, view_toggle]),
                # Filtering controls
                UIContainer("row", children=[filter_type, filter_keyword, search_text]),
                # Deck summary
                deck_summary,
                # Hidden state
                deck_state,
            ],
        )
        section.set_layout(layout)
    return section


def create_deck_viewer_display_section() -> UISection:
    """Create the deck viewer display section."""
    with UISection("deck_viewer_display", "Deck Viewer Display") as section:
        # Deck info
        deck_name_top = UIElement("deck_name_top", lambda: gr.Markdown())
        deck_name = UIElement("deck_name", lambda: gr.Markdown())
        deck_stats = UIElement("deck_stats", lambda: gr.Markdown())

        # Plots
        mana_curve_plot = UIElement(
            "mana_curve_plot", lambda: gr.Plot(label="Mana Curve")
        )
        power_toughness_plot = UIElement(
            "power_toughness_plot", lambda: gr.Plot(label="Power/Toughness Curve")
        )
        color_balance_plot = UIElement(
            "color_balance_plot", lambda: gr.Plot(label="Color Balance")
        )
        type_counts_plot = UIElement(
            "type_counts_plot", lambda: gr.Plot(label="Type Counts")
        )
        rarity_plot = UIElement(
            "rarity_plot", lambda: gr.Plot(label="Rarity Breakdown")
        )

        # Deck properties
        deck_properties = UIElement(
            "deck_properties", lambda: gr.Markdown(label="Deck Properties")
        )

        # Arena export
        arena_btn = UIElement("arena_btn", lambda: gr.Button("Export to MTG Arena"))
        arena_out = UIElement(
            "arena_out", lambda: gr.Textbox(label="Arena Format", lines=8)
        )

        # Layout
        layout = UIContainer(
            "column",
            children=[
                # Deck info
                deck_name_top,
                deck_name,
                deck_stats,
                # Plots in rows
                UIContainer("row", children=[mana_curve_plot, power_toughness_plot]),
                UIContainer("row", children=[color_balance_plot, type_counts_plot]),
                rarity_plot,
                # Deck properties
                deck_properties,
                # Arena export
                UIContainer("row", children=[arena_btn, arena_out]),
            ],
        )
        section.set_layout(layout)
    return section


def create_deck_viewer_table_section() -> UISection:
    """Create the deck viewer table section."""
    default_columns = ["Name", "Type", "Qty", "Colors"]
    with UISection("deck_viewer_table", "Deck Table") as section:
        # Card display
        card_table = UIElement(
            "card_table",
            lambda: gr.Dataframe(
                headers=default_columns, datatype="str", label="Deck Cards"
            ),
        )
        card_gallery = UIElement(
            "card_gallery", lambda: gr.Gallery(label="Card Gallery", visible=False)
        )

        # Layout
        layout = UIContainer("group", children=[card_table, card_gallery])
        section.set_layout(layout)
    return section
