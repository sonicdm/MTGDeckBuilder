\
import os
import requests
import gradio as gr

from mtg_deck_builder.data_loader import load_atomic_cards_from_json, load_inventory_from_txt
from mtg_deck_builder.models.collection import Collection
from mtg_deck_builder.models.inventory import Inventory

ATOMIC_DIR = "atomic_json_files"
INVENTORY_DIR = "inventory_files"
CACHE_DIR = "cache_atomic_data"

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def list_local_json_files():
    ensure_dir(ATOMIC_DIR)
    files = [f for f in os.listdir(ATOMIC_DIR) if f.lower().endswith(".json")]
    files.sort()
    return files

def list_local_inventory_files():
    ensure_dir(INVENTORY_DIR)
    files = [f for f in os.listdir(INVENTORY_DIR) if f.lower().endswith(".txt")]
    files.sort()
    return files

def fetch_atomic_data_if_needed(url: str, filename: str) -> str:
    ensure_dir(CACHE_DIR)
    local_path = os.path.join(CACHE_DIR, filename)
    if not os.path.exists(local_path):
        print(f"Downloading {url} -> {local_path}")
        resp = requests.get(url)
        resp.raise_for_status()
        with open(local_path, 'wb') as f:
            f.write(resp.content)
    else:
        print(f"Using cached file {local_path}")
    return local_path

def load_multiple_inventories(selected_files, uploaded_file):
    from mtg_deck_builder.models.inventory import InventoryItem, Inventory

    merged_inv = Inventory(items=[])
    # Merge local selected
    for f in selected_files:
        path_local = os.path.join(INVENTORY_DIR, f)
        inv_local = load_inventory_from_txt(path_local)
        merged_inv.items.extend(inv_local.items)

    # Merge uploaded if any
    if uploaded_file is not None:
        try:
            up_path = uploaded_file.name
            inv_up = load_inventory_from_txt(up_path)
            merged_inv.items.extend(inv_up.items)
        except Exception as e:
            print(f"Failed to parse uploaded inventory: {e}")

    # Consolidate duplicates
    final_dict = merged_inv.to_dict()
    new_items = []
    for cname, qty in final_dict.items():
        new_items.append(InventoryItem(card_name=cname, quantity=qty))
    merged_inv.items = new_items

    return merged_inv

def process_data(
    local_atomic_choice,
    atomic_upload,
    atomic_url,
    local_inv_choices,
    inv_upload,
    session_state
):
    """
    1) Possibly load atomic from local, upload, or url
    2) Possibly load multiple inventories from local + upload
    3) Build a Collection
    """
    results = []

    # 1) Atomic
    loaded_atomic = None
    if local_atomic_choice and local_atomic_choice != "None":
        local_json_path = os.path.join(ATOMIC_DIR, local_atomic_choice)
        try:
            loaded_atomic = load_atomic_cards_from_json(local_json_path)
            results.append(f"Loaded atomic from local: {local_atomic_choice} => {len(loaded_atomic.cards)} cards.")
        except Exception as e:
            results.append(f"Failed local atomic {local_atomic_choice}: {e}")

    if atomic_upload is not None:
        try:
            path_up = atomic_upload.name
            loaded_atomic = load_atomic_cards_from_json(path_up)
            results.append(f\"Loaded atomic from upload => {len(loaded_atomic.cards)} cards.\")
        except Exception as e:
            results.append(f\"Failed atomic from upload: {e}\")

    if atomic_url:
        filename = os.path.basename(atomic_url) or "AtomicCards.json"
        try:
            local_path = fetch_atomic_data_if_needed(atomic_url, filename)
            loaded_atomic = load_atomic_cards_from_json(local_path)
            results.append(f\"Fetched atomic from URL => {len(loaded_atomic.cards)} cards.\")
        except Exception as e:
            results.append(f\"Failed fetch/parse atomic from URL: {e}\")

    if not loaded_atomic:
        results.append("No atomic data loaded.")
        return "\\n".join(results)

    # 2) Inventory
    merged_inv = load_multiple_inventories(local_inv_choices, inv_upload)
    results.append(f\"Merged inventory has {len(merged_inv.items)} items total.\")

    # 3) Build collection
    try:
        coll = Collection.build_from_inventory(loaded_atomic, merged_inv)
        session_state["collection"] = coll
        results.append(f\"Collection built with {len(coll.cards)} total card entries.\")
    except Exception as e:
        results.append(f\"Failed to build collection: {e}\")

    return "\\n".join(results)

def data_tab(session_state):
    with gr.Tab("Data Loading"):
        gr.Markdown("## Select or Upload Atomic Data")

        local_atomic_files = ["None"] + list_local_json_files()
        local_atomic_choice = gr.Dropdown(
            local_atomic_files, label="Local Atomic JSON", value="None"
        )
        atomic_url = gr.Textbox(label="Atomic URL", placeholder="https://example.com/AtomicCards.json")
        atomic_upload = gr.File(label="Upload AtomicCards.json", file_types=[".json"], optional=True)

        gr.Markdown("## Select or Upload Inventory (Multi)")

        local_inv = list_local_inventory_files()
        inv_dropdown = gr.Dropdown(
            local_inv, label="Local Inventories", multiselect=True, value=[]
        )
        inv_upload = gr.File(label="Upload Inventory .txt", file_types=[".txt"], optional=True)

        load_btn = gr.Button("Load Data")
        load_output = gr.Textbox(label="Result", lines=5)

        def on_load(*args):
            return process_data(*args, session_state=session_state)

        load_btn.click(
            fn=on_load,
            inputs=[local_atomic_choice, atomic_upload, atomic_url, inv_dropdown, inv_upload],
            outputs=[load_output]
        )
