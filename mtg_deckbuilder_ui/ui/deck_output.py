# Decklist display, Arena export, and stats for mtg_deckbuilder_ui

import gradio as gr
from pathlib import Path
import pandas as pd
from mtg_deckbuilder_ui.logic.deckbuilder_func import build_deck


CONFIG_PRESETS_DIR = Path("config/presets")
USER_UPLOADS_DIR = Path("data/user_uploads")


def list_yaml_presets():
    return [
        f.name
        for f in CONFIG_PRESETS_DIR.iterdir()
        if f.suffix.lower() in [".yaml", ".yml"]
    ]


def list_user_inventories():
    if not USER_UPLOADS_DIR.exists():
        USER_UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    return [
        f.name
        for f in USER_UPLOADS_DIR.iterdir()
        if f.suffix.lower() in [".txt", ".csv"]
    ]


def deck_output_tab():
    with gr.Blocks() as demo:
        # Config selection
        config_dropdown = gr.Dropdown(
            choices=list_yaml_presets(),
            label="Select Deck Config (YAML Preset)",
            interactive=True,
        )
        # Inventory selection/upload
        inventory_dropdown = gr.Dropdown(
            choices=list_user_inventories(),
            label="Select Inventory File",
            interactive=True,
        )
        inventory_upload = gr.File(
            label="Upload Inventory File (.txt or .csv)", file_types=[".txt", ".csv"]
        )

        # Deck info/stats output
        deck_info = gr.Textbox(label="Deck Info & Stats", lines=8, interactive=False)
        # Deck table output
        card_table = gr.Dataframe(
            headers=[
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
            ],
            datatype=[
                "str",
                "str",
                "str",
                "str",
                "number",
                "str",
                "str",
                "str",
                "number",
                "str",
            ],
            interactive=False,
            label="Deck Cards",
        )
        # Arena export output
        arena_export = gr.Textbox(
            label="MTG Arena Import String", lines=4, interactive=False
        )

        # Handle inventory upload
        def handle_inventory_upload(uploaded_file):
            if uploaded_file is None:
                return gr.update(), list_user_inventories()
            dest = USER_UPLOADS_DIR / uploaded_file.name
            with open(dest, "wb") as f:
                f.write(uploaded_file.read())
            return uploaded_file.name, list_user_inventories()

        # Run deck build and format outputs
        def run_deckbuilder(config_file, inventory_file):
            if not config_file or not inventory_file:
                return (
                    "Please select both a config and an inventory.",
                    pd.DataFrame(),
                    "",
                )
            config_path = CONFIG_PRESETS_DIR / config_file
            inventory_path = USER_UPLOADS_DIR / inventory_file
            
            # Load config from file
            try:
                with open(config_path, 'r') as f:
                    yaml_content = f.read()
            except Exception as e:
                return f"Error reading config file: {e}", pd.DataFrame(), ""
            
            # Build deck using the validation function which returns proper format
            from mtg_deckbuilder_ui.logic.deckbuilder_func import build_deck_with_validation
            result = build_deck_with_validation(yaml_content)
            
            if not result:
                return "Deck build failed.", pd.DataFrame(), ""
            
            # Extract results from tuple
            card_table, deck_info, deck_stats, arena_export, validation_summary, card_status_table, deck_analysis, deck_state, build_status = result
            
            # Combine deck info and stats
            info_str = f"{deck_info}\n{deck_stats}"
            
            return info_str, card_table, arena_export

        with gr.Row():
            with gr.Column():
                config_dropdown.render()
                inventory_dropdown.render()
                inventory_upload.render()
                run_btn = gr.Button("Build Deck")
            with gr.Column():
                deck_info.render()
                card_table.render()
                arena_export.render()

        # Events
        inventory_upload.upload(
            handle_inventory_upload,
            inputs=inventory_upload,
            outputs=[inventory_dropdown, inventory_dropdown],
        )
        run_btn.click(
            run_deckbuilder,
            inputs=[config_dropdown, inventory_dropdown],
            outputs=[deck_info, card_table, arena_export],
        )
    return demo
