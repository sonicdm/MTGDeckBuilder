# Standard library imports
import logging

# Third-party imports
import gradio as gr

# Local application imports
from mtg_deckbuilder_ui.ui.ui_objects import UISection

# Set up logger
logger = logging.getLogger(__name__)


def create_deck_identity_section() -> UISection:
    """Create the deck identity section."""
    section = UISection("deck_identity", "Deck Identity")

    with section:
        with gr.Row():
            name = gr.Textbox(
                label="Deck Name", placeholder="Enter deck name", elem_id="name"
            )
            colors = gr.Dropdown(
                label="Colors",
                choices=["W", "U", "B", "R", "G"],
                multiselect=True,
                elem_id="colors",
            )
        with gr.Row():
            size = gr.Number(
                label="Deck Size",
                value=60,
                minimum=40,
                maximum=100,
                step=1,
                elem_id="size",
            )
            max_card_copies = gr.Number(
                label="Max Copies",
                value=4,
                minimum=1,
                maximum=4,
                step=1,
                elem_id="max_card_copies",
            )
        with gr.Row():
            allow_colorless = gr.Checkbox(
                label="Allow Colorless", value=True, elem_id="allow_colorless"
            )
            color_match_mode = gr.Dropdown(
                label="Color Match Mode",
                choices=["exact", "subset", "superset"],
                value="exact",
                elem_id="color_match_mode",
            )
        legalities = gr.Dropdown(
            label="Legalities",
            choices=["standard", "modern", "pioneer", "commander"],
            multiselect=True,
            value=["standard"],
            elem_id="legalities",
        )

    return section
