# Top-level tab layout logic for mtg_deckbuilder_ui

import gradio as gr

from mtg_deckbuilder_ui.tabs.config_manager import config_manager_tab
from mtg_deckbuilder_ui.tabs.deckbuilder import deckbuilder_tab
from mtg_deckbuilder_ui.tabs.inventory_manager import inventory_manager_tab
# from mtg_deckbuilder_ui.tabs.yaml_editor import yaml_editor_tab
# from mtg_deckbuilder_ui.tabs.deck_output import deck_output_tab
# from mtg_deckbuilder_ui.tabs.form_builder import form_builder_tab


def build_tabs():
    # Shared context/state for config selection
    config_context = gr.State({"config_file": None})
    # Dummy session/db_path/inventory_path for now; replace with real session/paths as needed
    session = gr.State(None)
    db_path = gr.State("profile_cards.db")
    inventory_path = gr.State("inventory.txt")

    with gr.Tab("Deckbuilder"):
        deckbuilder_tab(config_context, session, db_path, inventory_path)
    with gr.Tab("Config Manager"):
        config_manager_tab(config_context)
    with gr.Tab("Inventory Manager"):
        inventory_manager_tab(config_context, session, db_path, inventory_path)
    # Uncomment/add other tabs as implemented
    # with gr.Tab("YAML Editor"):
    #     yaml_editor_tab()
    # with gr.Tab("Deck Output"):
    #     deck_output_tab()
    # with gr.Tab("Form Builder"):
    #     form_builder_tab()

    # ...add other tabs here...
