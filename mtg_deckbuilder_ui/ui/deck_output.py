# Decklist display, Arena export, and stats for mtg_deckbuilder_ui

import gradio as gr
import os


CONFIG_PRESETS_DIR = "config/presets"
USER_UPLOADS_DIR = "data/user_uploads"


def list_yaml_presets():
    return [
        f
        for f in os.listdir(CONFIG_PRESETS_DIR)
        if f.endswith(".yaml") or f.endswith(".yml")
    ]


def list_user_inventories():
    if not os.path.exists(USER_UPLOADS_DIR):
        os.makedirs(USER_UPLOADS_DIR)
    return [
        f
        for f in os.listdir(USER_UPLOADS_DIR)
        if f.endswith(".txt") or f.endswith(".csv")
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
            dest = os.path.join(USER_UPLOADS_DIR, os.path.basename(uploaded_file.name))
            with open(dest, "wb") as f:
                f.write(uploaded_file.read())
            return os.path.basename(uploaded_file.name), list_user_inventories()

        # Run deck build and format outputs
        def run_deckbuilder(config_file, inventory_file):
            if not config_file or not inventory_file:
                return (
                    "Please select both a config and an inventory.",
                    pd.DataFrame(),
                    "",
                )
            config_path = os.path.join(CONFIG_PRESETS_DIR, config_file)
            inventory_path = os.path.join(USER_UPLOADS_DIR, inventory_file)
            result = build_deck(config_path, inventory_path)
            if not result or "deck" not in result:
                return "Deck build failed.", pd.DataFrame(), ""
            deck = result["deck"]
            stats = result.get("stats", {})
            arena_str = result.get("arena_export", "")

            # Deck info/stats
            info_lines = [
                f"Deck Name: {deck.get('name', '')}",
                f"Total Cards: {stats.get('total_cards', '')}",
                f"Average Mana Value: {stats.get('avg_mana_value', '')}",
                f"Color Balance: {stats.get('color_balance', '')}",
                f"Type Counts: {stats.get('type_counts', '')}",
                f"Ramp Count: {stats.get('ramp_count', '')}",
                f"Lands: {stats.get('lands', '')}",
            ]
            info_str = "\n".join(info_lines)

            # Card table
            card_rows = []
            for card in deck.get("cards", []):
                pt = (
                    f"{card.get('power','')}/{card.get('toughness','')}"
                    if card.get("power") or card.get("toughness")
                    else ""
                )
                legalities = ", ".join(
                    f"{fmt}:{stat}" for fmt, stat in card.get("legalities", {}).items()
                )
                card_rows.append(
                    [
                        card.get("name", ""),
                        card.get("type", ""),
                        card.get("rarity", ""),
                        legalities,
                        card.get("cmc", ""),
                        card.get("cost", ""),
                        ", ".join(card.get("colors", [])),
                        pt,
                        card.get("qty", 1),
                        card.get("text", ""),
                    ]
                )
            df = pd.DataFrame(
                card_rows,
                columns=[
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
            )

            return info_str, df, arena_str

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
