# logic/data_logic.py

import os
import shutil
import requests

from mtg_deck_builder.data_loader import load_atomic_cards_from_json, load_inventory_from_txt
from mtg_deck_builder.models.collection import Collection
from mtg_deck_builder.models.inventory import Inventory

ATOMIC_DIR = "atomic_json_files"
INVENTORY_DIR = "inventory_files"
CACHE_DIR = "cache_atomic_data"

def ensure_dir(path: str):
    if not os.path.exists(path):
        os.makedirs(path)

def list_local_json_files():
    """
    Return a sorted list of all .json in ATOMIC_DIR.
    """
    ensure_dir(ATOMIC_DIR)
    files = [f for f in os.listdir(ATOMIC_DIR) if f.lower().endswith(".json")]
    files.sort()
    return files

def list_local_inventory_files():
    """
    Return a sorted list of all .txt in INVENTORY_DIR.
    """
    ensure_dir(INVENTORY_DIR)
    files = [f for f in os.listdir(INVENTORY_DIR) if f.lower().endswith(".txt")]
    files.sort()
    return files

def fetch_atomic_data_if_needed(url: str, filename: str) -> str:
    """
    Download from URL into CACHE_DIR if not present.
    Return local path to the file.
    """
    ensure_dir(CACHE_DIR)
    local_path = os.path.join(CACHE_DIR, filename)
    if not os.path.exists(local_path):
        print(f"Downloading {url} -> {local_path}")
        resp = requests.get(url)
        resp.raise_for_status()
        with open(local_path, "wb") as f:
            f.write(resp.content)
    else:
        print(f"Using cached file {local_path}")
    return local_path

def copy_to_directory(uploaded_file, target_dir: str) -> str:
    """
    Copies a Gradio-uploaded file to target_dir, returning the new local path.
    If uploaded_file is None, returns None.
    """
    if uploaded_file is None:
        return None
    ensure_dir(target_dir)

    temp_path = uploaded_file.name  # The temp file path
    base_name = os.path.basename(temp_path)
    final_path = os.path.join(target_dir, base_name)

    shutil.copy(temp_path, final_path)
    print(f"Copied {temp_path} -> {final_path}")
    return final_path

def load_multiple_inventories(selected_files, uploaded_path):
    """
    Merge multiple inventories from local 'selected_files' + one uploaded path.
    Return a single merged Inventory object.
    """
    from mtg_deck_builder.models.inventory import InventoryItem, Inventory

    merged_inv = Inventory(items=[])

    # Merge local selected
    for f in selected_files:
        path_local = os.path.join(INVENTORY_DIR, f)
        inv_local = load_inventory_from_txt(path_local)
        merged_inv.items.extend(inv_local.items)

    # Merge uploaded if any
    if uploaded_path:
        inv_up = load_inventory_from_txt(uploaded_path)
        merged_inv.items.extend(inv_up.items)

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
    Orchestrates loading atomic data + inventory, building a Collection.
    """
    results = []

    # 1) Load Atomic
    loaded_atomic = None

    # (a) local dropdown
    if local_atomic_choice and local_atomic_choice != "None":
        local_json_path = os.path.join(ATOMIC_DIR, local_atomic_choice)
        try:
            loaded_atomic = load_atomic_cards_from_json(local_json_path)
            results.append(f"Loaded atomic from local: {local_atomic_choice} => {len(loaded_atomic.cards)} cards.")
        except Exception as e:
            results.append(f"Failed local atomic {local_atomic_choice}: {e}")

    # (b) if user uploaded an atomic file
    atomic_uploaded_path = copy_to_directory(atomic_upload, ATOMIC_DIR) if atomic_upload else None
    if atomic_uploaded_path:
        try:
            loaded_atomic = load_atomic_cards_from_json(atomic_uploaded_path)
            results.append(f"Loaded atomic from upload => {len(loaded_atomic.cards)} cards.")
        except Exception as e:
            results.append(f"Failed atomic from upload: {e}")

    # (c) if user specified a URL
    if atomic_url:
        filename = os.path.basename(atomic_url) or "AtomicCards.json"
        try:
            local_path = fetch_atomic_data_if_needed(atomic_url, filename)
            loaded_atomic = load_atomic_cards_from_json(local_path)
            results.append(f"Fetched atomic from URL => {len(loaded_atomic.cards)} cards.")
        except Exception as e:
            results.append(f"Failed fetch/parse atomic from URL: {e}")

    if not loaded_atomic:
        results.append("No atomic data loaded.")
        return "\n".join(results)

    # 2) Merge Inventories
    inv_uploaded_path = copy_to_directory(inv_upload, INVENTORY_DIR) if inv_upload else None
    merged_inv = load_multiple_inventories(local_inv_choices, inv_uploaded_path)
    results.append(f"Merged inventory has {len(merged_inv.items)} items total.")

    # 3) Build collection
    from mtg_deck_builder.models.collection import Collection
    try:
        coll = Collection.build_from_inventory(loaded_atomic, merged_inv)
        session_state["collection"] = coll
        results.append(f"Collection built with {len(coll.cards)} total card entries.")
    except Exception as e:
        results.append(f"Failed to build collection: {e}")

    return "\n".join(results)
