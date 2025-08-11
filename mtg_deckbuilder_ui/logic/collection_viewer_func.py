"""Collection viewer functionality for MTG Deck Builder."""

from collections import defaultdict
import logging
import csv
import json
import gradio as gr
import pandas as pd
from typing import Dict, List, Tuple, Any
from mtg_deck_builder.db import get_session
from mtg_deck_builder.db.repository import SummaryCardRepository
from mtg_deck_builder.db.inventory import load_inventory_items
from mtg_deckbuilder_ui.app_config import app_config
from mtg_deckbuilder_ui.utils.ui_helpers import list_files_by_extension
from mtg_deckbuilder_ui.utils.logging_config import get_logger
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool


# Set up logger for this module
logger = get_logger(__name__)

# Simple in-memory cache for inventory
_inventory_cache = {}
# Simple in-memory cache for collection DataFrame results
_collection_df_cache = {}


def get_session_factory(db_path):
    engine = create_engine(f"sqlite:///{db_path}", poolclass=NullPool)
    return sessionmaker(bind=engine)


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
    """
    Get collection data as a pandas DataFrame.
    
    Args:
        colors: List of colors to filter by
        color_match_mode: How to match colors ('exact', 'subset', 'any')
        owned_only: Whether to only show owned cards
        basic_type: Basic type to filter by
        supertype: Supertype to filter by
        subtype: Subtype to filter by
        keyword_multi: Keywords to filter by
        rarity: Rarity to filter by
        legality: Format legality to filter by
        min_qty: Minimum quantity required
        name_search: Name search term
        name_multi: List of specific card names
        text_search: Text search term
        inventory_file: Inventory file path
        inventory_dir: Inventory directory
        type_multi: Type filter
        
    Returns:
        pandas DataFrame with card data
    """
    try:
        cache_key = (
            f"{colors}_{color_match_mode}_{owned_only}_{basic_type}_{supertype}_"
            f"{subtype}_{keyword_multi}_{rarity}_{legality}_{min_qty}_{name_search}_"
            f"{name_multi}_{text_search}_{inventory_file}_{type_multi}"
        )
        if cache_key in _collection_df_cache:
            return _collection_df_cache[cache_key]

        display_columns = [
            "name",
            "colors",
            "color_identity",
            "mana_cost",
            "converted_mana_cost",
            "type",
            "supertypes",
            "subtypes",
            "keywords",
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
        
        # Get database session
        db_url = app_config.get_db_url()
        db_path = db_url if db_url.endswith(".db") else db_url.split("///")[-1]
        session_factory = get_session_factory(db_path)
        
        with session_factory() as session:
            # Create repository and get all cards
            repo = SummaryCardRepository(session=session)
            cards = repo.get_all_cards()
            
            if not cards:
                return pd.DataFrame()
            
            logger.debug(f"cards loaded: {len(cards)} cards")
            if cards:
                logger.debug(f"Sample card from cards: {cards[0]}")
                
            inventory_map = {}
            if inventory_file and inventory_dir:
                # Load inventory using load_inventory_items
                try:
                    with get_session(db_url) as session:
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
            
            # Create a repository with the loaded cards for filtering
            repo_with_cards = SummaryCardRepository(session=session, cards=cards)
            filtered_repo = repo_with_cards.filter_cards(
                name_query=name_search,
                text_query=text_search,
                rarity=rarity,
                color_identity=colors,
                color_mode=color_match_mode,
                legal_in=[legality] if legality else None,
                basic_type=basic_type,
                supertype=supertype,
                subtype=subtype,
                keyword_multi=keyword_multi,
                names_in=name_multi,
                min_quantity=min_qty,
            )
            filtered_cards = filtered_repo.get_all_cards()
            logger.debug(f"After SummaryCardRepository.filter_cards: {len(filtered_cards)} cards")

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
    try:
        db_url = app_config.get_db_url()
        with get_session(db_url) as session:
            from mtg_deck_builder.db.mtgjson_models.cards import MTGJSONCard
            printing = session.query(MTGJSONCard).filter_by(uuid=uuid).first()
            if printing and printing.set:
                return printing.set.name
            return "Unknown Set"
    except Exception as e:
        logger.warning(f"Error getting set name for UUID {uuid}: {e}")
        return "Unknown Set"


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
    """Update the collection table with status information."""
    try:
        def extract_color_codes(selected):
            if not selected:
                return []
            if isinstance(selected, str):
                return [selected]
            return selected

        color_codes = extract_color_codes(colors)
        type_multi = extract_color_codes(type_multi_val)
        keyword_multi = extract_color_codes(keyword_multi_val)
        name_multi = extract_color_codes(name_multi_val)

        df = get_collection_df(
            colors=color_codes,
            color_match_mode=color_mode_val,
            owned_only=owned,
            basic_type=basic_type_val,
            supertype=supertype_val,
            subtype=subtype_val,
            keyword_multi=keyword_multi,
            rarity=rarity_val,
            legality=legality_val,
            min_qty=min_qty,
            name_search=name_val,
            name_multi=name_multi,
            text_search=text_val,
            inventory_file=inventory_file,
            inventory_dir=inventory_dir,
            type_multi=type_multi,
        )

        if df.empty:
            return df, "No cards found matching the criteria."
        else:
            return df, f"Found {len(df)} cards matching the criteria."

    except Exception as e:
        logger.exception("Error in update_table_with_status")
        return pd.DataFrame(), f"Error: {str(e)}"


def do_export_csv(df):
    """Export DataFrame to CSV."""
    if df.empty:
        return None
    return df.to_csv(index=False)


def do_export_json(df):
    """Export DataFrame to JSON."""
    if df.empty:
        return None
    return df.to_json(orient="records", indent=2)


def refresh_inventory_files(inventory_dir):
    """Refresh the list of inventory files."""
    files = list_files_by_extension("inventory_files", [".txt", ".csv"])
    return [str(f) for f in files]


def clear_filters(DEFAULT_DISPLAY_COLUMNS):
    """Clear all filters and return default values."""
    return (
        None,  # colors
        "any",  # color_mode_val
        False,  # owned
        None,  # basic_type_val
        None,  # supertype_val
        None,  # subtype_val
        None,  # type_multi_val
        None,  # keyword_multi_val
        None,  # rarity_val
        None,  # legality_val
        0,  # min_qty
        "",  # name_val
        None,  # name_multi_val
        "",  # text_val
        DEFAULT_DISPLAY_COLUMNS,  # columns
        None,  # inventory_dir
    )


def create_collection_viewer_tab() -> Dict[str, Any]:
    """Create the collection viewer tab components."""
    with gr.Tab("Collection Viewer"):
        with gr.Row():
            with gr.Column(scale=1):
                # Filter controls
                colors = gr.Dropdown(
                    choices=["W", "U", "B", "R", "G"],
                    label="Colors",
                    multiselect=True,
                    value=None,
                )
                color_mode_val = gr.Dropdown(
                    choices=["any", "exact", "subset"],
                    label="Color Match Mode",
                    value="any",
                )
                owned = gr.Checkbox(label="Owned Only", value=False)
                basic_type_val = gr.Dropdown(
                    choices=["Creature", "Instant", "Sorcery", "Enchantment", "Artifact", "Planeswalker", "Land"],
                    label="Basic Type",
                    value=None,
                )
                supertype_val = gr.Dropdown(
                    choices=["Basic", "Legendary", "Snow", "World"],
                    label="Supertype",
                    value=None,
                )
                subtype_val = gr.Dropdown(
                    choices=["Human", "Goblin", "Dragon", "Forest", "Mountain", "Island", "Plains", "Swamp"],
                    label="Subtype",
                    value=None,
                )
                type_multi_val = gr.Dropdown(
                    choices=["Creature", "Instant", "Sorcery", "Enchantment", "Artifact", "Planeswalker", "Land"],
                    label="Type Multi",
                    multiselect=True,
                    value=None,
                )
                keyword_multi_val = gr.Dropdown(
                    choices=["Flying", "First Strike", "Double Strike", "Haste", "Vigilance", "Deathtouch", "Lifelink", "Trample"],
                    label="Keywords",
                    multiselect=True,
                    value=None,
                )
                rarity_val = gr.Dropdown(
                    choices=["Common", "Uncommon", "Rare", "Mythic"],
                    label="Rarity",
                    value=None,
                )
                legality_val = gr.Dropdown(
                    choices=["Standard", "Modern", "Legacy", "Vintage", "Commander"],
                    label="Legality",
                    value=None,
                )
                min_qty = gr.Number(label="Min Quantity", value=0, minimum=0)
                name_val = gr.Textbox(label="Name Search", value="")
                name_multi_val = gr.Dropdown(
                    choices=[],
                    label="Name Multi",
                    multiselect=True,
                    value=None,
                )
                text_val = gr.Textbox(label="Text Search", value="")
                inventory_file = gr.Dropdown(
                    choices=refresh_inventory_files(None),
                    label="Inventory File",
                    value=None,
                )
                inventory_dir = gr.Textbox(label="Inventory Directory", value="inventory_files", visible=False)

            with gr.Column(scale=3):
                # Results
                results_df = gr.Dataframe(
                    headers=["Name", "Owned Qty", "Colors", "Color Identity", "Mana Cost", "Converted Mana Cost", "Type", "Supertypes", "Subtypes", "Keywords", "Text", "Flavor Text", "Power", "Toughness", "Abilities", "Number", "Rarity", "UUID"],
                    label="Collection Results",
                    interactive=False,
                )
                status_text = gr.Markdown(value="Ready to search...")
                
                with gr.Row():
                    search_btn = gr.Button("Search", variant="primary")
                    clear_btn = gr.Button("Clear Filters")
                    export_csv_btn = gr.Button("Export CSV")
                    export_json_btn = gr.Button("Export JSON")

    return {
        "colors": colors,
        "color_mode_val": color_mode_val,
        "owned": owned,
        "basic_type_val": basic_type_val,
        "supertype_val": supertype_val,
        "subtype_val": subtype_val,
        "type_multi_val": type_multi_val,
        "keyword_multi_val": keyword_multi_val,
        "rarity_val": rarity_val,
        "legality_val": legality_val,
        "min_qty": min_qty,
        "name_val": name_val,
        "name_multi_val": name_multi_val,
        "text_val": text_val,
        "inventory_file": inventory_file,
        "inventory_dir": inventory_dir,
        "results_df": results_df,
        "status_text": status_text,
        "search_btn": search_btn,
        "clear_btn": clear_btn,
        "export_csv_btn": export_csv_btn,
        "export_json_btn": export_json_btn,
    }


def filter_cards(
    cards: List[Dict[str, Any]],
    filter_text: str,
    sort_by: str,
    group_by: str,
) -> Tuple[List[Dict[str, Any]], str]:
    """Filter and sort cards based on criteria.

    Args:
        cards: List of card dictionaries
        filter_text: Text to filter by
        sort_by: Field to sort by
        group_by: Field to group by

    Returns:
        Tuple containing filtered cards and statistics
    """
    if not cards:
        return [], "No cards to filter"

    # Apply text filter
    if filter_text:
        filter_lower = filter_text.lower()
        cards = [
            card for card in cards
            if filter_lower in card.get("name", "").lower()
            or filter_lower in card.get("text", "").lower()
        ]

    # Sort cards
    if sort_by and sort_by != "None":
        def get_sort_key(card: Dict[str, Any]) -> Any:
            value = card.get(sort_by, "")
            if isinstance(value, str):
                return value.lower()
            return value

        cards = sorted(cards, key=get_sort_key)

    # Group cards (for now, just return as is)
    # TODO: Implement grouping logic

    return cards, f"Found {len(cards)} cards"


def load_collection(
    filename: str,
    filter_text: str,
    sort_by: str,
    group_by: str,
) -> Tuple[List[Dict[str, Any]], str]:
    """Load a collection from file and apply filters.

    Args:
        filename: Name of the collection file
        filter_text: Text to filter by
        sort_by: Field to sort by
        group_by: Field to group by

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
    files = list_files_by_extension("collections", [".csv", ".json"])
    return [str(f) for f in files]
