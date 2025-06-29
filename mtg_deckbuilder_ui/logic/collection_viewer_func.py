"""Collection viewer functionality for MTG Deck Builder."""

from collections import defaultdict
import os
import logging
import csv
import json
import gradio as gr
import pandas as pd
from typing import Dict, List, Tuple, Any, Optional
from mtg_deck_builder.db import get_session
from mtg_deck_builder.db.repository import CardRepository
from mtg_deck_builder.db.models import CardDB, InventoryItemDB
from mtg_deck_builder.db.mtgjson_models.inventory import load_inventory_items
from mtg_deckbuilder_ui.app_config import app_config
from mtg_deckbuilder_ui.utils.ui_helpers import list_files_by_extension
from mtg_deckbuilder_ui.utils.logging_config import get_logger


# Set up logger for this module
logger = get_logger(__name__)

# Simple in-memory cache for inventory
_inventory_cache = {}
# Simple in-memory cache for collection DataFrame results
_collection_df_cache = {}


def get_session_factory(db_path):
    return get_session(f"sqlite:///{db_path}")


def get_collection_df(
    colors=None,
    color_match_mode="any",
    owned_only=False,
    basic_type=None,
    supertype=None,
    subtype=None,
    keyword_multi=None,
    rarity=None,
    legality=None,
    min_qty=0,
    name_search=None,
    name_multi=None,
    text_search=None,
    inventory_file=None,
    inventory_dir=None,
    type_multi=None,
):
    logger.debug("Entered get_collection_df")
    try:
        # Build a cache key from all parameters that affect the result
        cache_key = (
            tuple(colors) if colors else None,
            color_match_mode,
            owned_only,
            basic_type,
            supertype,
            subtype,
            tuple(keyword_multi) if keyword_multi else None,
            rarity,
            legality,
            min_qty,
            name_search,
            tuple(name_multi) if name_multi else None,
            text_search,
            inventory_file,
            inventory_dir,
            tuple(type_multi) if type_multi else None,
        )
        if cache_key in _collection_df_cache:
            logger.debug("Returning cached collection DataFrame")
            return _collection_df_cache[cache_key]

        display_columns = [
            "name",
            "colors",
            "mana_cost",
            "converted_mana_cost",
            "type",
            "text",
            "flavor_text",
            "power",
            "toughness",
            "abilities",
            "rarity",
            "legalities",
            "newest_printing_uuid",
            "newest_printing_rel",
            "uuid",
        ]
        db_url = app_config.get_db_url()
        db_path = db_url if db_url.endswith(".db") else db_url.split("///")[-1]
        session_factory = get_session_factory(db_path)
        session, cards = CardRepository.get_cached_cards(
            db_path, session_factory, columns=display_columns
        )

        logger.debug(f"cards loaded: {len(cards)} cards")
        if cards:
            logger.debug(f"Sample card from cards: {cards[0]}")
        inventory_map = {}
        if inventory_file and inventory_dir:
            # Load inventory using load_inventory_items
            try:
                with get_session() as session:
                    load_inventory_items(inventory_file, session)
                    logger.debug(f"Inventory loaded from {inventory_file}")
            except Exception as e:
                logger.warning(f"Failed to load inventory from {inventory_file}: {e}")

        logger.debug(
            "Calling filter_cards with: "
            f"name_query={name_search}, text_query={text_search}, "
            f"rarity={rarity}, color_identity={colors}, "
            f"color_mode={color_match_mode}, legal_in={legality}, "
            f"basic_type={basic_type}, supertype={supertype}, "
            f"subtype={subtype}, keyword_multi={keyword_multi}, "
            f"names_in={name_multi}, min_quantity={min_qty}"
        )
        repo = CardRepository(cards=cards)
        filtered_repo = repo.filter_cards(
            name_query=name_search,
            text_query=text_search,
            rarity=rarity,
            color_identity=colors,
            color_mode=color_match_mode,
            legal_in=legality,
            basic_type=basic_type,
            supertype=supertype,
            subtype=subtype,
            keyword_multi=keyword_multi,
            names_in=name_multi,
            min_quantity=min_qty,
        )
        filtered_cards = filtered_repo._cards
        logger.debug(f"After CardRepository.filter_cards: {len(filtered_cards)} cards")

        preprocessed_cards = []
        for card in filtered_cards:
            newest = card.newest_printing
            preprocessed_cards.append(
                {
                    "card": card,
                    "colors": card.colors or [],
                    "text": (card.text or "").lower(),
                    "type_line": (card.type or "").lower(),
                    "name_lower": str(card.name).lower(),
                    "color_identity": newest.color_identity if newest else [],
                    "keywords": (
                        [kw.lower() for kw in newest.keywords or []] if newest else []
                    ),
                    "newest_printing": newest,
                }
            )

        if type_multi and preprocessed_cards:
            selected_types_lower = [
                st.strip().lower() for st in type_multi if st and st.strip()
            ]
            if selected_types_lower:
                before_count = len(preprocessed_cards)
                cards_to_keep = []
                for card_meta in preprocessed_cards:
                    type_words = card_meta["type_line"].split()
                    if all(t in type_words for t in selected_types_lower):
                        cards_to_keep.append(card_meta)

                after_count = len(cards_to_keep)
                logger.debug(
                    f"type_multi filter: {before_count} -> {after_count} "
                    f"cards after filtering for types: {selected_types_lower}"
                )
                preprocessed_cards = cards_to_keep
        else:
            logger.debug("type_multi not applied or no cards to filter.")
        rows = []
        after_owned = 0
        for card_meta in preprocessed_cards:
            card = card_meta["card"]
            newest_printing = card_meta["newest_printing"]
            card_colors = ",".join(card_meta.get("colors", []))
            color_identity_list = card_meta["color_identity"] or []
            color_identity_str = ",".join(color_identity_list)
            card_name_str = str(card.name)
            owned_qty = inventory_map.get(
                card_name_str.lower(), getattr(card, "owned_qty", 0)
            )
            if owned_only and owned_qty <= 0:
                continue
            after_owned += 1
            row = {
                "Name": card.name,
                "Owned Qty": owned_qty,
                "Colors": card_colors,
                "Color Identity": color_identity_str,
                "Mana Cost": card.mana_cost,
                "Converted Mana Cost": card.converted_mana_cost,
                "Type": card.type,
                "Supertypes": (
                    ", ".join(getattr(newest_printing, "supertypes", []) or [])
                    if newest_printing
                    else ""
                ),
                "Subtypes": (
                    ", ".join(getattr(newest_printing, "subtypes", []) or [])
                    if newest_printing
                    else ""
                ),
                "Keywords": (
                    ", ".join(getattr(newest_printing, "keywords", []) or [])
                    if newest_printing
                    else ""
                ),
                "Text": card.text,
                "Flavor Text": card.flavor_text,
                "Power": card.power,
                "Toughness": card.toughness,
                "Abilities": ", ".join(card.abilities or []),
                "Number": newest_printing.number if newest_printing else "",
                "Rarity": card.rarity,
                "UUID": newest_printing.uuid if newest_printing else "",
            }
            rows.append(row)
        logger.debug(f"After owned_only/min_qty filter: {after_owned} cards")
        df = pd.DataFrame(rows)
        _collection_df_cache[cache_key] = df
        if df.empty:
            params = {
                "owned_only": owned_only,
                "min_qty": min_qty,
                "type_multi": type_multi,
                "basic_type": basic_type,
                "supertype": supertype,
                "subtype": subtype,
                "keyword_multi": keyword_multi,
                "rarity": rarity,
                "legality": legality,
                "name_search": name_search,
                "name_multi": name_multi,
                "text_search": text_search,
            }
            logger.debug(f"DataFrame is empty. Params: {params}")

        possible_columns = [
            "Name",
            "Owned Qty",
            "Colors",
            "Color Identity",
            "Mana Cost",
            "Converted Mana Cost",
            "Type",
            "Supertypes",
            "Subtypes",
            "Keywords",
            "Text",
            "Flavor Text",
            "Power",
            "Toughness",
            "Abilities",
            "Number",
            "Rarity",
            "UUID",
        ]
        for col_name in possible_columns:
            if col_name not in df.columns:
                df[col_name] = ""
        return df
    except Exception as e:
        import traceback

        logger.debug(f"Exception in get_collection_df: {e}")
        logger.debug(f"Traceback: {traceback.format_exc()}")
        return pd.DataFrame()


def _get_set_name_by_uuid(uuid):
    """
    Helper create a new session and fetch set_name for a CardPrintingDB by UUID.
    """
    if not uuid:
        return ""
    try:
        from mtg_deck_builder.db import get_session
        from mtg_deck_builder.db.models import CardPrintingDB
        from mtg_deckbuilder_ui.app_config import app_config

        db_url = app_config.get_db_url()
        db_path = db_url if db_url.endswith(".db") else db_url.split("///")[-1]
        with get_session(f"sqlite:///{db_path}") as session:
            printing = session.query(CardPrintingDB).filter_by(uuid=uuid).first()
            if printing and printing.set and hasattr(printing.set, "set_name"):
                return printing.set.set_name
    except Exception as e:
        logger.debug(f"_get_set_name_by_uuid error: {e}")
    return ""


def update_table_with_status(
    inventory_file,
    colors,
    color_mode_val,
    owned,
    basic_type_val,
    supertype_val,
    subtype_val,
    type_multi_val,
    keyword_multi_val,
    rarity_val,
    legality_val,
    min_qty,
    name_val,
    name_multi_val,
    text_val,
    columns,
    inventory_dir=None,
):
    logger = logging.getLogger("mtg_deckbuilder_ui.tabs.collection_viewer")
    status = "_Status: Loading..._"
    try:
        from mtg_deckbuilder_ui.utils.ui_helpers import _get_value

        color_labels = {
            "W": "⚪ White",
            "U": "🔵 Blue",
            "B": "⚫ Black",
            "R": "🔴 Red",
            "G": "🟢 Green",
        }

        def extract_color_codes(selected):
            if not selected:
                return []
            codes = []
            for val in selected:
                for k, v in color_labels.items():
                    if val.startswith(v):
                        codes.append(k)
                        break
            return codes

        color_codes = extract_color_codes(_get_value(colors, []))
        basic_type_val = None if basic_type_val == "Any" else basic_type_val
        supertype_val = None if supertype_val == "Any" else supertype_val
        subtype_val = None if subtype_val == "Any" else subtype_val
        rarity_val = None if rarity_val == "Any" else rarity_val
        legality_val = None if legality_val == "Any" else legality_val
        df = get_collection_df(
            colors=color_codes,
            color_match_mode=color_mode_val,
            owned_only=owned,
            basic_type=basic_type_val,
            supertype=supertype_val,
            subtype=subtype_val,
            keyword_multi=keyword_multi_val,
            rarity=rarity_val,
            legality=legality_val,
            min_qty=min_qty,
            name_search=name_val,
            name_multi=name_multi_val,
            text_search=text_val,
            inventory_file=inventory_file,
            inventory_dir=inventory_dir,
            type_multi=type_multi_val,
        )
        if columns:
            existing_cols = [col for col in columns if col in df.columns]
            missing_cols = [col for col in columns if col not in df.columns]
            df = df[existing_cols]
            if df.empty and missing_cols:
                for col in missing_cols:
                    df[col] = None
                df = df[columns]
        status = "_Status: Loaded successfully._"
        return df, status
    except Exception as e:
        logger.exception("Error in update_table_with_status")
        status = f"_Status: Error: {str(e)}_"
        return None, status


def do_export_csv(df):
    if df is None:
        return None
    path = "collection_export.csv"
    df.to_csv(path, index=False)
    return path


def do_export_json(df):
    if df is None:
        return None
    path = "collection_export.json"
    df.to_json(path, orient="records", indent=2)
    return path


def refresh_inventory_files(inventory_dir):
    files = list_files_by_extension(inventory_dir, [".txt"])
    return files


def clear_filters(DEFAULT_DISPLAY_COLUMNS):
    return (
        [],
        "any",
        False,
        "Any",
        "Any",
        "Any",
        [],
        [],
        "Any",
        "Any",
        0,
        "",
        [],
        "",
        DEFAULT_DISPLAY_COLUMNS,
    )


def create_collection_viewer_tab() -> Dict[str, gr.Component]:
    """Create the collection viewer tab UI components.

    Returns:
        Dict[str, gr.Component]: Dictionary of UI components
    """
    with gr.Tab("Collection Viewer"):
        with gr.Row():
            collection_dropdown = gr.Dropdown(
                label="Select Collection",
                choices=list_files_by_extension("collections", [".csv", ".json"]),
                interactive=True,
            )
            refresh_button = gr.Button("Refresh Collections")
        with gr.Row():
            with gr.Column():
                filter_text = gr.Textbox(
                    label="Filter Cards",
                    placeholder="Enter text to filter cards...",
                )
                sort_by = gr.Dropdown(
                    label="Sort By",
                    choices=["Name", "Type", "Rarity", "Set", "Quantity"],
                    value="Name",
                )
                group_by = gr.Dropdown(
                    label="Group By",
                    choices=["None", "Type", "Rarity", "Set"],
                    value="None",
                )
            with gr.Column():
                stats_text = gr.Textbox(
                    label="Collection Statistics",
                    interactive=False,
                )
        card_table = gr.Dataframe(
            headers=["Name", "Type", "Rarity", "Set", "Quantity"],
            interactive=False,
        )
    return {
        "collection_dropdown": collection_dropdown,
        "refresh_button": refresh_button,
        "filter_text": filter_text,
        "sort_by": sort_by,
        "group_by": group_by,
        "stats_text": stats_text,
        "card_table": card_table,
    }


def filter_cards(
    cards: List[Dict[str, Any]],
    filter_text: str,
    sort_by: str,
    group_by: str,
) -> Tuple[List[Dict[str, Any]], str]:
    """Filter and sort cards based on user criteria.

    Args:
        cards: List of card dictionaries
        filter_text: Text to filter cards by
        sort_by: Field to sort cards by
        group_by: Field to group cards by

    Returns:
        Tuple containing filtered cards and statistics
    """
    if filter_text:
        filter_text = filter_text.lower()
        cards = [
            card
            for card in cards
            if (
                filter_text in card["name"].lower()
                or filter_text in card["type"].lower()
                or filter_text in card["set"].lower()
            )
        ]

    def get_sort_key(card: Dict[str, Any]) -> Any:
        return card[sort_by.lower()]

    cards.sort(key=get_sort_key)
    if group_by != "None":
        grouped_cards = {}
        for card in cards:
            key = card[group_by.lower()]
            if key not in grouped_cards:
                grouped_cards[key] = []
            grouped_cards[key].append(card)
        cards = [card for group in grouped_cards.values() for card in group]
    total_cards = sum(card["quantity"] for card in cards)
    unique_cards = len(cards)
    type_counts = defaultdict(int)
    rarity_counts = defaultdict(int)
    set_counts = defaultdict(int)
    for card in cards:
        type_counts[card["type"]] += 1
        rarity_counts[card["rarity"]] += 1
        set_counts[card["set"]] += 1

    rarities_str = ", ".join(f"{r}: {c}" for r, c in rarity_counts.items())
    types_str = ", ".join(f"{t}: {c}" for t, c in type_counts.items())
    sets_str = ", ".join(f"{s}: {c}" for s, c in set_counts.items())
    stats = (
        f"Total Cards: {total_cards}\n"
        f"Unique Cards: {unique_cards}\n"
        f"Types: {types_str}\n"
        f"Rarities: {rarities_str}\n"
        f"Sets: {sets_str}"
    )
    return cards, stats


def load_collection(
    filename: str,
    filter_text: str,
    sort_by: str,
    group_by: str,
) -> Tuple[List[Dict[str, Any]], str]:
    """Load collection data from file.

    Args:
        filename: Name of collection file
        filter_text: Text to filter cards by
        sort_by: Field to sort cards by
        group_by: Field to group cards by

    Returns:
        Tuple containing loaded cards and statistics
    """
    if not filename:
        return [], "No collection selected"
    try:
        if filename.endswith(".csv"):
            with open(f"collections/{filename}", "r") as f:
                reader = csv.DictReader(f)
                cards = list(reader)
        else:
            with open(f"collections/{filename}", "r") as f:
                cards = json.load(f)
        for card in cards:
            card["quantity"] = int(card["quantity"])
        return filter_cards(cards, filter_text, sort_by, group_by)
    except Exception as e:
        return [], f"Error loading collection: {str(e)}"


def refresh_collection_list() -> List[str]:
    """Refresh the list of available collections.

    Returns:
        List of collection filenames
    """
    return list_files_by_extension("collections", [".csv", ".json"])
