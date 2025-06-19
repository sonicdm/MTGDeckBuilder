# mtg_deckbuilder_ui/logic/deck_viewer_callbacks.py

import gradio as gr
from mtg_deckbuilder_ui.utils.ui_helpers import list_files_by_extension
from mtg_deckbuilder_ui.utils.plot_utils import (
    plot_mana_curve,
    plot_power_toughness_curve,
)
from mtg_deckbuilder_ui.logic.deck_viewer_func import (
    filter_card_table,
    load_deck_json,
    update_card_display,
    update_card_table_columns,
    on_load_deck as do_on_load_deck,
    on_import_arena as do_on_import_arena,
    export_arena,
)
import os


def get_deck_dir():
    deck_dir = os.path.join(os.path.dirname(__file__), "..", "..", "generated_decks")
    return os.path.abspath(deck_dir)


def get_deck_files(deck_dir):
    os.makedirs(deck_dir, exist_ok=True)
    return list_files_by_extension(deck_dir, [".json"])


def on_load_deck(
    deck_file,
    selected_columns,
    filter_type_val,
    filter_keyword_val,
    search_text_val,
    deck_dir,
):
    return do_on_load_deck(
        deck_file,
        selected_columns,
        filter_type_val,
        filter_keyword_val,
        search_text_val,
        deck_dir,
    )


def on_import_arena(arena_import, card_table_columns):
    return do_on_import_arena(arena_import, card_table_columns)


def on_update_deck(deck_state, card_table_columns_value):
    try:
        if not deck_state:
            return [gr.update()] * 9

        from mtg_deckbuilder_ui.ui.deck_sync import deck_to_viewer_outputs

        outputs = deck_to_viewer_outputs(deck_state, card_table_columns_value)
        if not outputs:
            return [gr.update()] * 9

        return [gr.update(value=o) for o in outputs]
    except Exception as e:
        return [gr.update()] * 9
