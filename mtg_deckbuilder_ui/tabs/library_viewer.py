# mtg_deckbuilder_ui/tabs/library_viewer.py

"""
library_viewer.py

Provides the library viewer tab interface for the MTG Deckbuilder application.
This module defines the UI components and layout for viewing the card library.
"""

import gradio as gr
from mtg_deck_builder.db.repository import SummaryCardRepository
from mtg_deck_builder.db import get_session


def load_library():
    with get_session() as session:
        card_repo = SummaryCardRepository(session=session)
        return card_repo.get_all_cards()


def filter_library(owned_only):
    cards = load_library()
    if owned_only:
        cards = [card for card in cards if getattr(card, "owned_qty", 0) > 0]
    return "\n".join([card.name for card in cards])


def library_viewer_tab():
    owned_checkbox = gr.Checkbox(label="Show only owned cards", value=False)
    library_output = gr.Textbox(label="Library", lines=10)
    owned_checkbox.change(filter_library, inputs=owned_checkbox, outputs=library_output)
    library_output.value = filter_library(False)
    return gr.Tab(label="Library Viewer", elem_id="library_viewer_tab")
