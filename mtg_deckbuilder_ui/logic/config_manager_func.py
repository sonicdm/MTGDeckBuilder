import os
import yaml
from mtg_deckbuilder_ui.app_config import DECK_CONFIGS_DIR
from ..ui.config_sync import apply_config_to_ui, extract_config_from_ui, safe_update

def load_config(config_name, ui_map):
    """
    Loads a YAML config and populates the form (for config manager or deckbuilder).
    """
    if not config_name:
        return [None] + [safe_update(ui_map[key], None) for key in ui_map]
    path = os.path.join(DECK_CONFIGS_DIR, config_name)
    try:
        with open(path, 'r', encoding='utf-8') as f:
            config_dict = yaml.safe_load(f)
        updates = apply_config_to_ui(config_dict, ui_map)
        return [f"Loaded: {config_name}"] + updates
    except Exception as e:
        return [f"Error loading config: {e}"] + [safe_update(ui_map[key], None) for key in ui_map]

def save_config(config_name, ui_map):
    """
    Converts the form into a config dict and saves to YAML.
    """
    config_dict = extract_config_from_ui(ui_map)
    try:
        with open(os.path.join(DECK_CONFIGS_DIR, config_name), 'w', encoding='utf-8') as f:
            yaml.dump(config_dict, f, sort_keys=False)
        return f"Saved to {config_name}"
    except Exception as e:
        return f"Error saving config: {e}"

