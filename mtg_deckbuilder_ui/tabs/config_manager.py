from zipfile import sizeEndCentDir

import gradio as gr
import os
import yaml
import shutil
from mtg_deckbuilder_ui.app_config import DECK_CONFIGS_DIR

def ensure_config_dir():
    if not os.path.exists(DECK_CONFIGS_DIR):
        os.makedirs(DECK_CONFIGS_DIR)

def list_yaml_files():
    ensure_config_dir()
    return [f for f in os.listdir(DECK_CONFIGS_DIR) if f.endswith('.yaml') or f.endswith('.yml')]

def load_yaml_config(yaml_file):
    # Try utf-8 first, fallback to latin-1 if decoding fails
    path = os.path.join(DECK_CONFIGS_DIR, yaml_file)
    try:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            with open(path, 'r', encoding='latin-1') as f:
                content = f.read()
        data = yaml.safe_load(content)
        return yaml.dump(data, sort_keys=False)
    except Exception as e:
        return f"Error: {e}"

def save_yaml_config(yaml_file, content):
    try:
        data = yaml.safe_load(content)
        with open(os.path.join(DECK_CONFIGS_DIR, yaml_file), 'w', encoding='utf-8') as f:
            yaml.dump(data, f, sort_keys=False)
        return "Config saved."
    except Exception as e:
        return f"Error: {e}"

def import_yaml_config(uploaded_file):
    try:
        ensure_config_dir()
        filename = os.path.basename(uploaded_file.name)
        dest_path = os.path.join(DECK_CONFIGS_DIR, filename)
        shutil.copy(uploaded_file.name, dest_path)
        return f"Imported {filename}"
    except Exception as e:
        return f"Error importing: {e}"

def config_manager_tab(config_context):
    import gradio as gr
    import os

    ensure_config_dir()
    with gr.Group():
        gr.Markdown("**Config File**")
        with gr.Row(equal_height=True):
            with gr.Column(scale=9):
                yaml_files = gr.Dropdown(
                    choices=list_yaml_files(),
                    label="Select YAML Config",
                    scale=15
                )
            with gr.Column(scale=1):
                refresh_btn = gr.Button(
                    value="🔄 Refresh List",
                    elem_id="refresh_yaml_list",
                    elem_classes="refresh-btn",
                    size="sm",
                    scale=1,
                )

    yaml_content = gr.Code(label="YAML Config Content", language="yaml")
    load_yaml_btn = gr.Button("Load Config")
    save_yaml_btn = gr.Button("Save Config")
    upload_yaml = gr.File(label="Import YAML Config", file_types=[".yaml", ".yml"])
    import_status = gr.Textbox(label="Import Status", interactive=False)
    set_config_btn = gr.Button("Set as Active Config")

    def refresh_files():
        return gr.update(choices=list_yaml_files())

    def set_active_config(selected_file):
        return gr.update(value=selected_file), {"config_file": selected_file}

    refresh_btn.click(refresh_files, None, yaml_files)
    load_yaml_btn.click(load_yaml_config, inputs=yaml_files, outputs=yaml_content)
    save_yaml_btn.click(save_yaml_config, inputs=[yaml_files, yaml_content], outputs=yaml_content)
    upload_yaml.upload(import_yaml_config, inputs=upload_yaml, outputs=import_status).then(
        refresh_files, None, yaml_files
    )
    set_config_btn.click(
        set_active_config, inputs=yaml_files, outputs=[yaml_files, config_context]
    )
