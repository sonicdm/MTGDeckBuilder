import gradio as gr
from mtg_deck_builder.db.repository import CardRepository

def load_library(session):
    card_repo = CardRepository(session=session)
    return card_repo.get_all_cards()

def filter_library(session, owned_only):
    cards = load_library(session)
    if owned_only:
        cards = [card for card in cards if getattr(card, "owned_qty", 0) > 0]
    return "\n".join([card.name for card in cards])

def library_viewer_tab(config_context, session, db_path):
    owned_checkbox = gr.Checkbox(label="Show only owned cards", value=False)
    library_output = gr.Textbox(label="Library", lines=10)
    owned_checkbox.change(lambda owned: filter_library(session, owned), inputs=owned_checkbox, outputs=library_output)
    library_output.value = filter_library(session, False)
