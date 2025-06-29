# mtg_deckbuilder_ui/logic/config_manager_func.py

import yaml
from pathlib import Path
from mtg_deckbuilder_ui.app_config import app_config
from ..ui.config_sync import apply_config_to_ui, extract_config_from_ui, safe_update


def load_config(config_name, ui_map):
    """
    Loads a YAML config and populates the form (for config manager or deckbuilder).
    """
    if not config_name:
        return [None] + [safe_update(ui_map[key], None) for key in ui_map]
    path = Path(app_config.get_path("deck_configs_dir")) / config_name
    try:
        config_dict = yaml.safe_load(path.read_text(encoding="utf-8"))
        updates = apply_config_to_ui(config_dict, ui_map)
        # Convert dictionary updates to list format
        update_list = [f"Loaded: {config_name}"]
        for key in ui_map:
            if key in updates:
                update_list.append(updates[key])
            else:
                update_list.append(safe_update(ui_map[key], None))
        return update_list
    except Exception as e:
        return [f"Error loading config: {e}"] + [
            safe_update(ui_map[key], None) for key in ui_map
        ]


def save_config(config_name, ui_map):
    """
    Converts the form into a config dict and saves to YAML.
    """
    config_dict = extract_config_from_ui(ui_map)
    try:
        config_path = Path(app_config.get_path("deck_configs_dir")) / config_name
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(config_dict, f, sort_keys=False)
        return f"Saved to {config_name}"
    except Exception as e:
        return f"Error saving config: {e}"
