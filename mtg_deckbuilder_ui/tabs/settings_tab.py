# mtg_deckbuilder_ui/tabs/settings_tab.py

"""
settings_tab.py

Provides the settings tab interface for the MTG Deckbuilder application.
This module defines the UI components and layout for application settings.
"""

import gradio as gr
from mtg_deckbuilder_ui.app_config import app_config


def settings_tab():
    with gr.Blocks() as tab:
        gr.Markdown("# Settings")
        config = app_config.config
        input_widgets = {}
        # --- UI Section: Add auto_load_collection toggle ---
        if not config.has_section("UI"):
            config.add_section("UI")
        auto_load_collection_val = (
            config.get("UI", "auto_load_collection", fallback="False").lower() == "true"
        )
        auto_load_collection = gr.Checkbox(
            label="Auto-load Collection on Tab Open", value=auto_load_collection_val
        )
        input_widgets[("UI", "auto_load_collection")] = auto_load_collection
        # --- Render all other config fields ---
        for section in config.sections():
            if section == "UI":
                continue  # Already handled above
            with gr.Group():
                gr.Markdown(f"### [{section}]")
                for key, value in config.items(section):
                    val_lower = value.lower()
                    if val_lower in ["true", "false"]:
                        input_widgets[(section, key)] = gr.Checkbox(
                            label=key, value=val_lower == "true"
                        )
                    else:
                        input_widgets[(section, key)] = gr.Textbox(
                            label=key, value=value
                        )
        save_btn = gr.Button("Save Settings")
        status = gr.Markdown("")

        def save_settings(*args):
            idx = 0
            for section, key in input_widgets:
                widget = input_widgets[(section, key)]
                val = args[idx]
                if isinstance(widget, gr.Checkbox):
                    val = str(bool(val))
                app_config.set(section, key, val)
                idx += 1
            return "Settings saved!"

        save_btn.click(
            save_settings, inputs=list(input_widgets.values()), outputs=status
        )
    return tab
