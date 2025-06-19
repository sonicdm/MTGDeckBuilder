import os
import json
import requests
from mtg_deckbuilder_ui.app_config import app_config


def load_keywords_json():
    """
    Loads the keywords.json file from the MTGJSON directory.
    Returns the loaded JSON as a Python object, or None if not found.
    """
    keywords_path = app_config.get_path("keywords")
    if not os.path.exists(keywords_path):
        return None
    with open(keywords_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_cardtypes_json():
    """
    Loads the cardtypes.json file from the MTGJSON directory.
    Returns the loaded JSON as a Python object, or None if not found.
    """
    cardtypes_path = app_config.get_path("cardtypes")
    if not os.path.exists(cardtypes_path):
        return None
    with open(cardtypes_path, "r", encoding="utf-8") as f:
        return json.load(f)


def download_keywords_json(keywords_url, keywords_json):
    """Download Keywords.json from MTGJSON and save to local path."""
    try:
        print(f"[mtgjson_sync] Downloading Keywords.json from {keywords_url} ...")
        r = requests.get(keywords_url, timeout=30)
        r.raise_for_status()
        with open(keywords_json, "wb") as f:
            f.write(r.content)
        print(f"[mtgjson_sync] Saved Keywords.json to {keywords_json}")
    except Exception as e:
        print(f"[mtgjson_sync] Failed to download Keywords.json: {e}")


def download_cardtypes_json(cardtypes_url, local_cardtypes_path):
    """Download CardTypes.json from MTGJSON and save to local path."""
    try:
        print(f"[mtgjson_sync] Downloading CardTypes.json from {cardtypes_url} ...")
        r = requests.get(cardtypes_url, timeout=30)
        r.raise_for_status()
        with open(local_cardtypes_path, "wb") as f:
            f.write(r.content)
        print(f"[mtgjson_sync] Saved CardTypes.json to {local_cardtypes_path}")
    except Exception as e:
        print(f"[mtgjson_sync] Failed to download CardTypes.json: {e}")
