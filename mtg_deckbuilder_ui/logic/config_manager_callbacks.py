# mtg_deckbuilder_ui/logic/config_manager_callbacks.py

import os
import yaml
import shutil
import gradio as gr
from mtg_deckbuilder_ui.app_config import app_config


def ensure_config_dir():
    if not os.path.exists(app_config.get_path("deck_configs_dir")):
        os.makedirs(app_config.get_path("deck_configs_dir"))


def list_yaml_files():
    ensure_config_dir()
    return [
        f
        for f in os.listdir(app_config.get_path("deck_configs_dir"))
        if f.endswith(".yaml") or f.endswith(".yml")
    ]


def load_yaml_config(yaml_file):
    path = os.path.join(app_config.get_path("deck_configs_dir"), yaml_file)
    try:
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            with open(path, "r", encoding="latin-1") as f:
                content = f.read()
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
        with open(
            os.path.join(app_config.get_path("deck_configs_dir"), yaml_file),
            "w",
            encoding="utf-8",
        ) as f:
            yaml.dump(data, f, sort_keys=False)
        return "Config saved."
    except Exception as e:
        return f"Error: {e}"


def import_yaml_config(uploaded_file):
    try:
        ensure_config_dir()
        filename = os.path.basename(uploaded_file.name)
        dest_path = os.path.join(app_config.get_path("deck_configs_dir"), filename)
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
