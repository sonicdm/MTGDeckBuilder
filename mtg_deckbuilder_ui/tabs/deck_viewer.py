import gradio as gr
import pandas as pd
import os
import json
from mtg_deckbuilder_ui.utils.ui_helpers import list_files_by_extension, get_full_path
from mtg_deckbuilder_ui.ui.deck_sync import deck_to_viewer_outputs
from mtg_deckbuilder_ui.logic.deck_viewer_func import plot_mana_curve, plot_power_toughness_curve, filter_card_table, load_deck_json

def deck_viewer_tab(deck_state=None):
    if deck_state is None:
        deck_state = gr.State(value=None)
    deck_dir = os.path.join(os.path.dirname(__file__), '..', 'generated_decks')
    deck_dir = os.path.abspath(deck_dir)
    os.makedirs(deck_dir, exist_ok=True)
    deck_files = list_files_by_extension(deck_dir, ['.json'])
    all_columns = [
        "Name", "Type", "Rarity", "Legalities", "CMC", "Cost",
        "Colors", "Power/Toughness", "Qty", "Card Text"
    ]
    default_columns = [
        "Name", "Type", "Rarity", "Legalities", "CMC", "Cost",
        "Colors", "Power/Toughness", "Qty", "Card Text"
    ]
    with gr.Row():
        with gr.Column(scale=1):
            deck_select = gr.Dropdown(deck_files, label="Select Deck to View", interactive=True)
            load_btn = gr.Button("Load Deck", variant="primary")
            arena_import = gr.Textbox(label="Paste Arena Import String", lines=6, interactive=True)
            import_btn = gr.Button("Import Arena Deck", variant="secondary")
            load_from_builder_btn = gr.Button("Load Deck from Builder", variant="secondary")
            card_table_columns = gr.Dropdown(
                choices=all_columns,
                value=default_columns[0],
                label="Select Columns to Display in Deck Table",
                multiselect=True,
                interactive=True
            )
            view_toggle = gr.Radio(
                choices=["Table View", "Card View (TBD)"],
                value="Table View",
                label="Display Mode"
            )
            deck_summary = gr.Markdown("", label="Deck Summary")
            filter_type = gr.Textbox(label="Filter by Type", interactive=True, placeholder="e.g. Creature")
            filter_keyword = gr.Textbox(label="Filter by Keyword", interactive=True, placeholder="e.g. Flying")
            search_text = gr.Textbox(label="Search Text", interactive=True, placeholder="e.g. Lightning Bolt")
        with gr.Column(scale=2):
            deck_name_top = gr.Markdown("", elem_id="deck-name-md-top")
            deck_name = gr.Markdown(elem_id="deck-name-md")
            deck_stats = gr.Markdown(elem_id="deck-stats-md")
            mana_curve_plot = gr.Image(label="Mana Curve")
            power_toughness_plot = gr.Image(label="Power/Toughness Curve")
            deck_properties = gr.Markdown("", label="Deck Properties")
            arena_btn = gr.Button("Export to MTG Arena")
            arena_out = gr.Textbox(label="Arena Format", lines=8)
    with gr.Row():
        card_table = gr.Dataframe(headers=default_columns, datatype="str", interactive=False, label="Deck Cards", visible=True)
        card_gallery = gr.Gallery(label="Card Gallery (TBD)", visible=False)

    def update_card_display(view_mode):
        if view_mode == "Table View":
            return gr.update(visible=True), gr.update(visible=False)
        return gr.update(visible=False), gr.update(visible=True)
    view_toggle.change(update_card_display, inputs=view_toggle, outputs=[card_table, card_gallery])

    def update_card_table_columns(selected_columns):
        return gr.update(headers=selected_columns)
    card_table_columns.change(update_card_table_columns, inputs=card_table_columns, outputs=card_table)

    def on_load_deck(deck_file, selected_columns, filter_type_val, filter_keyword_val, search_text_val):
        deck_path = get_full_path(deck_dir, deck_file)
        deck_obj = load_deck_json(deck_path)
        if deck_obj is None:
            # Return empty/cleared outputs if loading fails
            return [gr.update() for _ in range(9)]
        # Use the shared output function
        name, stats_md, mana_curve_plot, power_toughness_plot, prop_md, df, summary, arena_export = deck_to_viewer_outputs(deck_obj, selected_columns)
        # Apply filtering to the DataFrame if needed
        if isinstance(df, pd.DataFrame):
            df = filter_card_table(df, None, filter_type_val, filter_keyword_val, search_text_val)
        deck_name_md = f"# {name}" if name else "# Deck Viewer"
        return deck_name_md, name, stats_md, mana_curve_plot, power_toughness_plot, prop_md, df, summary, arena_export
    load_btn.click(on_load_deck, inputs=[deck_select, card_table_columns, filter_type, filter_keyword, search_text], outputs=[deck_name_top, deck_name, deck_stats, mana_curve_plot, power_toughness_plot, deck_properties, card_table, deck_summary, arena_out])

    def on_import_arena(arena_str, selected_columns):
        prop_md = """
        ### Deck Properties\n
        - Imported from Arena string (parsing not yet implemented)
        """
        return "# Imported Deck", "Imported deck from Arena string (parsing not yet implemented)", '', None, None, prop_md, pd.DataFrame(), "Imported deck from Arena string", arena_str
    import_btn.click(on_import_arena, inputs=[arena_import, card_table_columns], outputs=[deck_name_top, deck_name, deck_stats, mana_curve_plot, power_toughness_plot, deck_properties, card_table, deck_summary, arena_out])

    def on_load_from_builder(deck_obj, selected_columns):
        name, stats_md, mana_curve_plot, power_toughness_plot, prop_md, df, summary, arena_export = deck_to_viewer_outputs(deck_obj, selected_columns)
        # Set deck_name_top to the deck name as a Markdown header
        deck_name_md = f"# {name}" if name else "# Deck Viewer"
        return deck_name_md, name, stats_md, mana_curve_plot, power_toughness_plot, prop_md, df, summary, arena_export

    load_from_builder_btn.click(
        on_load_from_builder,
        inputs=[deck_state, card_table_columns],
        outputs=[deck_name_top, deck_name, deck_stats, mana_curve_plot, power_toughness_plot, deck_properties, card_table, deck_summary, arena_out]
    )

    def auto_load_from_builder(deck_obj, selected_columns):
        if deck_obj is not None:
            name, stats_md, mana_curve_plot, power_toughness_plot, prop_md, df, summary, arena_export = deck_to_viewer_outputs(deck_obj, selected_columns)
            deck_name_md = f"# {name}" if name else "# Deck Viewer"
            return deck_name_md, name, stats_md, mana_curve_plot, power_toughness_plot, prop_md, df, summary, arena_export
        return [gr.update() for _ in range(9)]

    deck_state.change(
        auto_load_from_builder,
        inputs=[deck_state, card_table_columns],
        outputs=[deck_name_top, deck_name, deck_stats, mana_curve_plot, power_toughness_plot, deck_properties, card_table, deck_summary, arena_out]
    )

    def export_arena(deck_obj):
        if deck_obj and hasattr(deck_obj, 'mtg_arena_import'):
            return deck_obj.mtg_arena_import()
        return ''
    arena_btn.click(export_arena, inputs=deck_state, outputs=arena_out)

    return gr.Tab(label="Deck Viewer", elem_id="deck_viewer_tab")


