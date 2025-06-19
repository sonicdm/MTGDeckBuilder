# Standard library imports
import logging

# Third-party imports
import gradio as gr

# Local application imports
from mtg_deckbuilder_ui.ui.ui_objects import UISection

# Set up logger
logger = logging.getLogger(__name__)


def create_card_categories_section() -> UISection:
    """Create the card categories section."""
    section = UISection("card_categories", "Card Categories")

    with section:
        # Creatures
        with gr.Group():
            gr.Markdown("### Creatures")
            with gr.Row():
                creatures_target = gr.Number(
                    label="Target Count",
                    value=24,
                    minimum=0,
                    maximum=100,
                    step=1,
                    elem_id="creatures_target",
                )
                creatures_keywords = gr.Textbox(
                    label="Keywords",
                    placeholder="Enter keywords (comma-separated)",
                    elem_id="creatures_keywords",
                )
            with gr.Row():
                creatures_priority_text = gr.Textbox(
                    label="Priority Text",
                    placeholder="Enter priority text patterns",
                    elem_id="creatures_priority_text",
                )
                creatures_basic_type_priority = gr.Textbox(
                    label="Basic Type Priority",
                    placeholder="Enter basic type priority",
                    elem_id="creatures_basic_type_priority",
                )

        # Removal
        with gr.Group():
            gr.Markdown("### Removal")
            with gr.Row():
                removal_target = gr.Number(
                    label="Target Count",
                    value=8,
                    minimum=0,
                    maximum=100,
                    step=1,
                    elem_id="removal_target",
                )
                removal_keywords = gr.Textbox(
                    label="Keywords",
                    placeholder="Enter keywords (comma-separated)",
                    elem_id="removal_keywords",
                )
            with gr.Row():
                removal_priority_text = gr.Textbox(
                    label="Priority Text",
                    placeholder="Enter priority text patterns",
                    elem_id="removal_priority_text",
                )
                removal_basic_type_priority = gr.Textbox(
                    label="Basic Type Priority",
                    placeholder="Enter basic type priority",
                    elem_id="removal_basic_type_priority",
                )

        # Card Draw
        with gr.Group():
            gr.Markdown("### Card Draw")
            with gr.Row():
                card_draw_target = gr.Number(
                    label="Target Count",
                    value=8,
                    minimum=0,
                    maximum=100,
                    step=1,
                    elem_id="card_draw_target",
                )
                card_draw_keywords = gr.Textbox(
                    label="Keywords",
                    placeholder="Enter keywords (comma-separated)",
                    elem_id="card_draw_keywords",
                )
            with gr.Row():
                card_draw_priority_text = gr.Textbox(
                    label="Priority Text",
                    placeholder="Enter priority text patterns",
                    elem_id="card_draw_priority_text",
                )
                card_draw_basic_type_priority = gr.Textbox(
                    label="Basic Type Priority",
                    placeholder="Enter basic type priority",
                    elem_id="card_draw_basic_type_priority",
                )

        # Buffs
        with gr.Group():
            gr.Markdown("### Buffs")
            with gr.Row():
                buffs_target = gr.Number(
                    label="Target Count",
                    value=8,
                    minimum=0,
                    maximum=100,
                    step=1,
                    elem_id="buffs_target",
                )
                buffs_keywords = gr.Textbox(
                    label="Keywords",
                    placeholder="Enter keywords (comma-separated)",
                    elem_id="buffs_keywords",
                )
            with gr.Row():
                buffs_priority_text = gr.Textbox(
                    label="Priority Text",
                    placeholder="Enter priority text patterns",
                    elem_id="buffs_priority_text",
                )
                buffs_basic_type_priority = gr.Textbox(
                    label="Basic Type Priority",
                    placeholder="Enter basic type priority",
                    elem_id="buffs_basic_type_priority",
                )

        # Utility
        with gr.Group():
            gr.Markdown("### Utility")
            with gr.Row():
                utility_target = gr.Number(
                    label="Target Count",
                    value=8,
                    minimum=0,
                    maximum=100,
                    step=1,
                    elem_id="utility_target",
                )
                utility_keywords = gr.Textbox(
                    label="Keywords",
                    placeholder="Enter keywords (comma-separated)",
                    elem_id="utility_keywords",
                )
            with gr.Row():
                utility_priority_text = gr.Textbox(
                    label="Priority Text",
                    placeholder="Enter priority text patterns",
                    elem_id="utility_priority_text",
                )
                utility_basic_type_priority = gr.Textbox(
                    label="Basic Type Priority",
                    placeholder="Enter basic type priority",
                    elem_id="utility_basic_type_priority",
                )
