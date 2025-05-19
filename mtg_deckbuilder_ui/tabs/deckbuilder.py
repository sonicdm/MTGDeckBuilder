import os
import pandas as pd
import numpy as np

import gradio as gr

from mtg_deck_builder.deck_config import DeckConfig
from mtg_deckbuilder_ui.app_config import DECK_CONFIGS_DIR, INVENTORY_FILE_DIR
from mtg_deckbuilder_ui.logic.deckbuilder_func import save_deckbuilder_config
from mtg_deckbuilder_ui.ui.config_sync import apply_config_to_ui, extract_config_from_ui
from mtg_deckbuilder_ui.utils.inventory_importer import import_inventory_file

LAST_CONFIG_PATH = os.path.join(DECK_CONFIGS_DIR, "last_config.txt")

def save_last_loaded_config(filename):
    try:
        with open(LAST_CONFIG_PATH, "w") as f:
            f.write(filename)
    except Exception as e:
        print(f"[WARN] Could not save last loaded config: {e}")

def load_last_loaded_config():
    try:
        if os.path.exists(LAST_CONFIG_PATH):
            with open(LAST_CONFIG_PATH, "r") as f:
                last = f.read().strip()
            if last and os.path.exists(os.path.join(DECK_CONFIGS_DIR, last)):
                return last
    except Exception as e:
        print(f"[WARN] Could not read last loaded config: {e}")
    return None

def deckbuilder_tab(config_context, session, db_path, inventory_path):
    # --- Config Load/Save Section ---
    gr.Markdown("## Deck Config: Load / Save")
    config_files = [f for f in os.listdir(DECK_CONFIGS_DIR) if f.endswith('.yaml') or f.endswith('.yml')]
    with gr.Row():
        config_select = gr.Dropdown(choices=config_files, label="Load Config", interactive=True)
        with gr.Column():
            load_btn = gr.Button("📂 Load", variant="secondary", size="sm")
            save_btn = gr.Button("💾 Save", variant="primary", size="sm")
            refresh_btn = gr.Button(
                value="🔄 Refresh Configurations",
                elem_id="refresh_config_list",
                elem_classes="refresh-btn",
                size="sm",
                scale=1
            )
        save_filename = gr.Textbox(label="Save As Filename", value="deck-output.yaml", interactive=True)

    # --- Inventory Selector (under config_select) ---
    inventory_dir = INVENTORY_FILE_DIR
    inventory_files = [f for f in os.listdir(inventory_dir) if f.endswith('.txt')]
    with gr.Row():
        inventory_select = gr.Dropdown(choices=inventory_files, label="Select Inventory", interactive=True)
        inventory_refresh_btn = gr.Button(
            value="🔄 Refresh Inventories",
            elem_id="refresh_inventory_list",
            elem_classes="refresh-btn",
            size="sm",
            scale=1
        )

    def on_refresh_inventories():
        refreshed = [f for f in os.listdir(inventory_dir) if f.endswith('.txt')]
        return gr.update(choices=refreshed)

    inventory_refresh_btn.click(on_refresh_inventories, outputs=inventory_select)

    status = gr.Markdown(visible=True)

    def on_inventory_selected(selected_inventory):
        if not selected_inventory:
            return gr.update(value="No inventory file selected.")
        inventory_path = os.path.join(inventory_dir, selected_inventory)
        def done_callback(success, message):
            status.value = message
        import_inventory_file(inventory_path, db_path, done_callback=done_callback)
        return gr.update(value=f"Importing inventory: {selected_inventory}")

    inventory_select.change(on_inventory_selected, inputs=inventory_select, outputs=status)

    def on_refresh_configs():
        refreshed = [f for f in os.listdir(DECK_CONFIGS_DIR) if f.endswith('.yaml') or f.endswith('.yml')]
        return gr.update(choices=refreshed)

    def on_load_config(selected_file):
        if not selected_file:
            no_ui_updates = [gr.update() for _ in ui_map.values()]
            return [gr.update(value="No configuration file selected.")] + no_ui_updates

        file_path = os.path.join(DECK_CONFIGS_DIR, selected_file)
        try:
            deck_config = DeckConfig.from_yaml(file_path)
            ui_updates_dict = apply_config_to_ui(deck_config, ui_map)

            ordered_ui_component_updates = []
            for component_key in ui_map.keys():
                ordered_ui_component_updates.append(ui_updates_dict.get(component_key, gr.update()))

            save_last_loaded_config(selected_file)
            return [gr.update(value=f"✅ Successfully loaded '{selected_file}'.")] + ordered_ui_component_updates
        except Exception as e:
            no_ui_updates = [gr.update() for _ in ui_map.values()]
            return [gr.update(value=f"❌ Error loading '{selected_file}': {str(e)[:100]}...")] + no_ui_updates

    def on_save_config(filename):
        try:
            save_deckbuilder_config(filename, ui_map)
            return gr.update(value=f"✅ Saved to {filename}")
        except Exception as e:
            return gr.update(value=f"❌ Error saving '{filename}': {str(e)[:100]}...")

    # Deck Identity (always visible)
    gr.Markdown("### Deck Identity")
    with gr.Row():
        name = gr.Textbox(label="Deck Name", interactive=True, info="The name of the deck.")
        size = gr.Number(label="Deck Size", value=60, interactive=True,
                         info="Total number of cards in the deck (60 for Standard).")
    with gr.Row():
        color_labels = {
            "W": "⚪ White",
            "U": "🔵 Blue",
            "B": "⚫ Black",
            "R": "🔴 Red",
            "G": "🟢 Green",
        }
        colors = gr.CheckboxGroup(
            choices=[f"{v} ({k})" for k, v in color_labels.items()],
            label="Colors",
            interactive=True,
            value=["⚪ White (W)"],
            info="Select allowed colors."
        )
        allow_colorless = gr.Checkbox(label="Allow Colorless Cards", value=True, interactive=True,
                                      info="Include cards that have no color, such as artifacts or Eldrazi.")
    with gr.Row():
        legalities = gr.Dropdown(
            choices=["standard", "modern", "legacy", "vintage", "pauper", "pioneer", "explorer", "brawl", "commander"],
            multiselect=True,
            label="Legalities",
            value=["standard"],
            interactive=True,
            info="Select formats to enforce legality rules for."
        )

    def update_format_defaults(selected):
        if "commander" in selected or "brawl" in selected:
            return gr.update(value=100), gr.update(value=1)
        elif "pauper" in selected or "standard" in selected:
            return gr.update(value=60), gr.update(value=4)
        return gr.update(), gr.update()

    with gr.Row():
        max_card_copies = gr.Number(label="Max Card Copies", value=4, interactive=True,
                                    info="Max number of copies for any non-basic card.")
        legalities.change(update_format_defaults, inputs=legalities, outputs=[size, max_card_copies])

    owned_cards_only = gr.Checkbox(label="Owned Cards Only", value=True, interactive=True,
                                   info="Only use cards from your inventory when building.")

    # Card Categories
    with gr.Accordion("Card Categories", open=False):
        category_ui_elements = {}
        categories_to_render = {
            "creatures": 24,
            "removal": 6,
            "card_draw": 4,
            "buffs": 4,
            "utility": 2
        }
        for category_key, default_target in categories_to_render.items():
            with gr.Group():
                gr.Markdown(f"**{category_key.replace('_', ' ').title()}**")
                target_ui = gr.Number(label="Target", value=default_target, interactive=True,
                                      info=f"Number of {category_key.replace('_', ' ')} cards to include.")
                keywords_ui = gr.Dropdown(label="Preferred Keywords", interactive=True, multiselect=True, allow_custom_value=True,
                                         info="Select or enter keywords (e.g., Haste, Trample, Menace).", choices=[])
                priority_ui = gr.Dropdown(label="Priority Text", interactive=True, multiselect=True, allow_custom_value=True,
                                         info="Select or enter phrases or /regex/ to favor in card text.", choices=[])
                category_ui_elements[f"{category_key}_target"] = target_ui
                category_ui_elements[f"{category_key}_keywords"] = keywords_ui
                category_ui_elements[f"{category_key}_priority_text"] = priority_ui

    # Card Constraints
    with gr.Accordion("Card Constraints", open=False):
        with gr.Row():
            mana_curve_min = gr.Number(label="Min Mana Curve (CMC)", value=1, interactive=True, minimum=0, step=1,
                                       info="Minimum Converted Mana Cost for included cards.")
            mana_curve_max = gr.Number(label="Max Mana Curve (CMC)", value=8, interactive=True, minimum=0, step=1,
                                       info="Maximum Converted Mana Cost for included cards.")
        rarity_boost_common = gr.Number(label="Common Boost", value=0, interactive=True,
                                        info="Weight for common cards.")
        rarity_boost_uncommon = gr.Number(label="Uncommon Boost", value=0, interactive=True,
                                          info="Weight for uncommon cards.")
        rarity_boost_rare = gr.Number(label="Rare Boost", value=2, interactive=True,
                                      info="Weight for rare cards.")
        rarity_boost_mythic = gr.Number(label="Mythic Boost", value=1, interactive=True,
                                        info="Weight for mythic cards.")
        exclude_keywords = gr.Dropdown(label="Exclude Keywords", interactive=True, multiselect=True, allow_custom_value=True,
                                      info="Select or enter phrases to never include in card text (e.g., Defender, Cannot attack).", choices=[])

    # Scoring Rules Section
    with gr.Accordion("Scoring Rules", open=False):
        gr.Markdown(
            "### Priority Text Rules\nList patterns to boost card importance based on text. Patterns can be regex if wrapped in slashes.")
        priority_text_df = pd.DataFrame({"Pattern": ["" for _ in range(10)], "Weight": [None for _ in range(10)]})
        priority_text = gr.Dataframe(
            headers=["Pattern", "Weight"],
            datatype=("str", "number"),
            value=priority_text_df,
            interactive=True,
            label="Priority Text Table",
            row_count=(5, "dynamic"),
            col_count=(2, "fixed")
        )
        rarity_bonus_common = gr.Number(label="Common Bonus", value=0, interactive=True,
                                        info="Score bonus for common cards.")
        rarity_bonus_uncommon = gr.Number(label="Uncommon Bonus", value=0, interactive=True,
                                          info="Score bonus for uncommon cards.")
        rarity_bonus_rare = gr.Number(label="Rare Bonus", value=2, interactive=True,
                                      info="Score bonus for rare cards.")
        rarity_bonus_mythic = gr.Number(label="Mythic Bonus", value=1, interactive=True,
                                        info="Score bonus for mythic cards.")
        mana_penalty_threshold = gr.Number(label="Mana Penalty Threshold", value=5, interactive=True,
                                           info="Start applying penalty above this mana cost.")
        mana_penalty_per = gr.Number(label="Penalty Per Point", value=1, interactive=True,
                                     info="Weight deducted per mana above threshold.")
        min_score_to_flag = gr.Number(label="Minimum Score to Flag", value=5, interactive=True,
                                      info="Minimum score required to consider card 'key'.")

    # Priority Cards Section
    with gr.Accordion("Priority Cards", open=False):
        gr.Markdown("Specify cards you always want in your deck, regardless of other filters.")
        priority_cards_df = pd.DataFrame({"Name": ["" for _ in range(10)], "Min Copies": [None for _ in range(10)]})
        priority_cards = gr.Dataframe(
            headers=["Name", "Min Copies"],
            datatype=("str", "number"),
            value=priority_cards_df,
            interactive=True,
            label="Always Include Cards",
            row_count=(10, "dynamic"),
            col_count=(2, "fixed")
        )

    # Mana Base Accordion
    with gr.Accordion("Mana Base Configuration", open=False):
        land_count = gr.Number(label="Land Count", value=22, interactive=True, info="Total number of lands.")
        special_count = gr.Number(label="Special Lands Count", value=6, interactive=True,
                                  info="Number of non-basic lands allowed.")
        special_prefer = gr.Dropdown(label="Prefer in Lands", interactive=True, multiselect=True, allow_custom_value=True,
                                    info="Select or enter preferred land types or effects.", choices=[])
        special_avoid = gr.Dropdown(label="Avoid in Lands", interactive=True, multiselect=True, allow_custom_value=True,
                                   info="Select or enter land features to avoid.", choices=[])
        adjust_mana = gr.Checkbox(label="Adjust by Mana Symbols", value=True, interactive=True,
                                  info="Adjust land ratio based on deck's mana symbol breakdown.")

    # Fallback Strategy Accordion
    with gr.Accordion("Fallback Strategy", open=False):
        fill_with_any_checkbox = gr.Checkbox(label="Fill remaining slots with any legal cards", value=True, interactive=True,
                                             info="If true, fills remaining slots with any legal cards to meet deck size if category targets aren't met.")
        fill_priority = gr.Textbox(label="Fill Priority (comma-separated categories)", interactive=True,
                                   info="Order of categories to fill in preference if targets are unmet.")
        allow_less_than_target = gr.Checkbox(label="Allow Less Than Target", value=False, interactive=True,
                                             info="If false, must meet exact counts or skip.")

    # --- UI Map for config sync ---
    ui_map = {
        "name": name,
        "size": size,
        "colors": colors,
        "legalities": legalities,
        "max_card_copies": max_card_copies,
        "mana_curve_min": mana_curve_min,
        "mana_curve_max": mana_curve_max,
        "rarity_boost_common": rarity_boost_common,
        "rarity_boost_uncommon": rarity_boost_uncommon,
        "rarity_boost_rare": rarity_boost_rare,
        "rarity_boost_mythic": rarity_boost_mythic,
        "allow_colorless": allow_colorless,
        "owned_cards_only": owned_cards_only,
        "exclude_keywords": exclude_keywords,
        "priority_text": priority_text,
        "rarity_bonus_common": rarity_bonus_common,
        "rarity_bonus_uncommon": rarity_bonus_uncommon,
        "rarity_bonus_rare": rarity_bonus_rare,
        "rarity_bonus_mythic": rarity_bonus_mythic,
        "mana_penalty_threshold": mana_penalty_threshold,
        "mana_penalty_per": mana_penalty_per,
        "min_score_to_flag": min_score_to_flag,
        "fill_with_any": fill_with_any_checkbox,
        "fill_priority": fill_priority,
        "allow_less_than_target": allow_less_than_target,
        **category_ui_elements,
        "land_count": land_count,
        "special_count": special_count,
        "special_prefer": special_prefer,
        "special_avoid": special_avoid,
        "adjust_mana": adjust_mana,
        "priority_cards": priority_cards,
    }

    # After UI map and before Action, auto-load last config if present
    last_loaded = load_last_loaded_config()
    if last_loaded and last_loaded in config_files:
        # Simulate loading the last config on startup
        file_path = os.path.join(DECK_CONFIGS_DIR, last_loaded)
        try:
            deck_config = DeckConfig.from_yaml(file_path)
            ui_updates_dict = apply_config_to_ui(deck_config, ui_map)
            for k, v in ui_updates_dict.items():
                ui_map[k].update(value=v.value)
            status.value = f"✅ Auto-loaded last config: {last_loaded}"
        except Exception as e:
            status.value = f"❌ Failed to auto-load last config: {e}"

    # Action
    load_btn.click(on_load_config, inputs=[config_select], outputs=[status] + list(ui_map.values()))
    save_btn.click(on_save_config, inputs=[save_filename], outputs=status)
    refresh_btn.click(on_refresh_configs, outputs=config_select)

    gr.Button("⚔️ Build Deck", variant="primary", elem_id="build_deck_btn")
