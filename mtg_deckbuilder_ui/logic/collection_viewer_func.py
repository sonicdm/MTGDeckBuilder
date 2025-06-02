import time
from mtg_deck_builder.db import get_session
from mtg_deckbuilder_ui.app_config import app_config
from mtg_deckbuilder_ui.logic.inventory_manager_func import parse_inventory_txt
from mtg_deck_builder.db.repository import CardRepository
import pandas as pd
import os

# Simple in-memory cache for inventory and cards
_inventory_cache = {}
_cards_cache = None
_cards_cache_time = 0
_cards_cache_ttl = 60  # seconds

def get_collection_df(colors=None, color_match_mode="any", owned_only=False, basic_type=None, supertype=None, subtype=None, keyword_multi=None, rarity=None, legality=None, min_qty=0, name_search=None, name_multi=None, text_search=None, inventory_file=None, inventory_dir=None):
    db_url = app_config.get_path('database')
    global _cards_cache, _cards_cache_time
    now = time.time()
    # Cache cards for 60 seconds
    if _cards_cache is None or now - _cards_cache_time > _cards_cache_ttl:
        with get_session(f'sqlite:///{db_url}') as session:
            repo = CardRepository(session=session)
            _cards_cache = repo.get_all_cards()
        _cards_cache_time = now
    cards = _cards_cache
    # Inventory cache by file path and mtime
    inventory_map = {}
    if inventory_file and inventory_dir:
        inv_path = os.path.join(inventory_dir, inventory_file)
        if os.path.exists(inv_path):
            mtime = os.path.getmtime(inv_path)
            cache_key = (inv_path, mtime)
            if cache_key in _inventory_cache:
                inventory_map = _inventory_cache[cache_key]
            else:
                inventory_map = {name.lower(): qty for qty, name in parse_inventory_txt(inv_path)}
                _inventory_cache.clear()  # Only keep one inventory in cache
                _inventory_cache[cache_key] = inventory_map
    rows = []
    for card in cards:
        card_colors = ','.join(card.colors) if getattr(card, 'colors', None) else ''
        # Color filtering
        if colors:
            card_colors_set = set(card.colors or [])
            filter_colors_set = set(colors)
            if color_match_mode == "any":
                if not card_colors_set & filter_colors_set:
                    continue
            elif color_match_mode == "subset":
                if not card_colors_set or not card_colors_set.issubset(filter_colors_set):
                    continue
            elif color_match_mode == "exact":
                if card_colors_set != filter_colors_set:
                    continue
        # Basic type filtering
        if basic_type and basic_type != "Any":
            if not getattr(card, 'type', '') or basic_type.lower() not in getattr(card, 'type', '').lower():
                continue
        # Supertype filtering
        if supertype and supertype != "Any":
            supertypes = getattr(card, 'newest_printing', None)
            if supertypes is not None:
                supertypes = getattr(supertypes, 'supertypes', [])
            else:
                supertypes = []
            if not supertypes or supertype.lower() not in [s.lower() for s in supertypes]:
                continue
        # Subtype filtering
        if subtype and subtype != "Any":
            subtypes = getattr(card, 'newest_printing', None)
            if subtypes is not None:
                subtypes = getattr(subtypes, 'subtypes', [])
            else:
                subtypes = []
            if not subtypes or subtype.lower() not in [s.lower() for s in subtypes]:
                continue
        # Keyword filtering
        if keyword_multi:
            keywords = getattr(card, 'newest_printing', None)
            if keywords is not None:
                keywords = getattr(keywords, 'keywords', [])
            else:
                keywords = []
            if isinstance(keyword_multi, list):
                if not all(kw.lower() in [k.lower() for k in (keywords or [])] for kw in keyword_multi):
                    continue
            elif keyword_multi:
                if keyword_multi.lower() not in [k.lower() for k in (keywords or [])]:
                    continue
        # Rarity filtering
        if rarity and rarity != "Any":
            if not getattr(card, 'rarity', '') or rarity.lower() != getattr(card, 'rarity', '').lower():
                continue
        # Legality filtering
        if legality and legality != "Any":
            legalities = getattr(card, 'legalities', {})
            if not legalities or legality.lower() not in [k.lower() for k in legalities.keys()]:
                continue
        # Name search
        if name_search and name_search.strip():
            if name_search.lower() not in card.name.lower():
                continue
        # Name multi
        if name_multi:
            if card.name.lower() not in [n.lower() for n in name_multi]:
                continue
        # Text search (name or text)
        if text_search and text_search.strip():
            text_blob = (getattr(card, 'name', '') + ' ' + getattr(card, 'text', '')).lower()
            if text_search.lower() not in text_blob:
                continue
        # Use inventory for owned qty if available
        owned_qty = inventory_map.get(card.name.lower(), getattr(card, 'owned_qty', 0))
        if owned_only and owned_qty <= 0:
            continue
        if min_qty and owned_qty < min_qty:
            continue
        rows.append({
            'Name': card.name,
            'Colors': card_colors,
            'Set': getattr(card, 'set_code', ''),
            'Rarity': getattr(card, 'rarity', ''),
            'Type': getattr(card, 'type', ''),
            'Owned Qty': owned_qty,
        })
    return pd.DataFrame(rows)
