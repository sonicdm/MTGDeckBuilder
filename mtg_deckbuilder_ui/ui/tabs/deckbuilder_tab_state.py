from mtg_deckbuilder_ui.app_config import app_config
import gradio as gr


class DeckbuilderTabState:
    def __init__(self, tab_key: str = "DeckBuilder"):
        self.tab_key = tab_key
        self.yaml_file_dropdown = gr.Dropdown(label="YAML Files", choices=[])
        self.yaml_editor = gr.Textbox(label="YAML Editor")
        self.yaml_files = {}
        self.current_yaml_file = None
        self.last_loaded_config = self.get_last_loaded_config()

    def get_last_loaded_config(self):
        # Use the tab_key to fetch the last loaded config for this tab
        if self.tab_key == "DeckBuilder":
            return app_config.get_last_loaded_config()
        else:
            return app_config.get(self.tab_key, "last_loaded_config", "")

    def set_last_loaded_config(self, config_name):
        # Store the last loaded config for this tab
        if self.tab_key == "DeckBuilder":
            app_config.set_last_loaded_config(config_name)
        else:
            app_config.set(self.tab_key, "last_loaded_config", config_name)
        self.last_loaded_config = config_name
