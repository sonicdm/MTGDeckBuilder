# mtg_deckbuilder_ui/logic/config_manager_callbacks.py

import yaml
import shutil
import gradio as gr
from pathlib import Path
from mtg_deckbuilder_ui.app_config import app_config


def ensure_config_dir():
    config_dir = Path(app_config.get_path("deck_configs_dir"))
    if not config_dir.exists():
        config_dir.mkdir(parents=True, exist_ok=True)


def list_yaml_files():
    ensure_config_dir()
    config_dir = Path(app_config.get_path("deck_configs_dir"))
    return [
        f.name
        for f in config_dir.iterdir()
        if f.suffix.lower() in [".yaml", ".yml"]
    ]


def load_yaml_config(yaml_file):
    path = Path(app_config.get_path("deck_configs_dir")) / yaml_file
    try:
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            content = path.read_text(encoding="latin-1")
        data = yaml.safe_load(content)
        return yaml.dump(data, sort_keys=False)
    except Exception as e:
        return f"Error: {e}"


def save_yaml_config(yaml_file, content):
    try:
        data = yaml.safe_load(content)
        if not yaml_file or not yaml_file.strip():
            raise ValueError("No file name specified.")
        yaml_file = yaml_file.strip()
        if not (
            yaml_file.lower().endswith(".yaml") or yaml_file.lower().endswith(".yml")
        ):
            yaml_file += ".yaml"
        config_path = Path(app_config.get_path("deck_configs_dir")) / yaml_file
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, sort_keys=False)
        return "Config saved."
    except Exception as e:
        return f"Error: {e}"


def import_yaml_config(uploaded_file):
    try:
        ensure_config_dir()
        filename = uploaded_file.name
        dest_path = Path(app_config.get_path("deck_configs_dir")) / filename
        shutil.copy(uploaded_file.name, dest_path)
        return f"Imported {filename}"
    except Exception as e:
        return f"Error importing: {e}"


def refresh_files():
    return gr.update(choices=list_yaml_files())


def set_active_config(selected_file):
    return gr.update(value=selected_file)


def save_yaml_wrapper(file_name, content):
    return save_yaml_config(file_name, content)


def load_yaml_and_set_filename(selected_file):
    content = load_yaml_config(selected_file)
    return content, selected_file
