# Standard library imports
import logging

# Third-party imports
import gradio as gr

# Local application imports
from mtg_deckbuilder_ui.ui.ui_objects import UISection

# Set up logger
logger = logging.getLogger(__name__)


def create_mana_curve_section() -> UISection:
    """Create the mana curve section."""
    section = UISection("mana_curve", "Mana Curve")

    with section:
        with gr.Row():
            mana_curve_min = gr.Number(
                label="Min CMC",
                value=0,
                minimum=0,
                maximum=20,
                step=1,
                elem_id="mana_curve_min",
            )
            mana_curve_max = gr.Number(
                label="Max CMC",
                value=7,
                minimum=0,
                maximum=20,
                step=1,
                elem_id="mana_curve_max",
            )
        with gr.Row():
            mana_curve_shape = gr.Dropdown(
                label="Curve Shape",
                choices=["bell", "linear", "exponential"],
                value="bell",
                elem_id="mana_curve_shape",
            )
            mana_curve_slope = gr.Slider(
                label="Curve Slope",
                minimum=-1.0,
                maximum=1.0,
                value=0.0,
                step=0.1,
                elem_id="mana_curve_slope",
            )

    return section
