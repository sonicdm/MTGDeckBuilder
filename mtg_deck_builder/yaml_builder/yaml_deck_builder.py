"""
Deprecated: This module is deprecated and will be removed in a future version.
Use yaml_deckbuilder.py instead.
"""

import logging
import re
from typing import Any, Dict, Optional

import yaml

from mtg_deck_builder.db.models import CardDB
from mtg_deck_builder.db.repository import CardRepository, InventoryRepository
from mtg_deck_builder.models.deck import Deck

logger = logging.getLogger(__name__)


def load_yaml_template(path: str) -> Dict[str, Any]:
    logger.debug(f"[DEBUG] Entering load_yaml_template")
    logger.debug(f"Loading YAML template from {path}")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _select_priority_cards(priority_cards, card_repo, allowed_colors, color_match_mode, legalities, max_copies):
    logger.debug(f"[DEBUG] Entering _select_priority_cards")
    selected_cards: Dict[str, CardDB] = {}
    for pc in priority_cards:
        name = pc["name"]
        min_copies = pc.get("min_copies", 1)
        card = card_repo.find_by_name(name)
        if card:
            color_ok = card.matches_color_identity(list(allowed_colors), color_match_mode)
            legality_ok = True
            if legalities:
                status = (card.legalities or {}).get(legalities[0], '')
                legality_ok = status.lower() == 'legal'
            if color_ok and legality_ok:
                card.owned_qty = min(min_copies, max_copies)
                selected_cards[card.name] = card
                logger.debug(f"Added priority card (ignoring constraints): {card.name} x{card.owned_qty}")
            else:
                logger.warning(
                    f"Priority card '{name}' found but does not match color/legality constraints: "
                    f"color_ok={color_ok}, legality_ok={legality_ok}"
                )
        else:
            logger.warning(f"Priority card not found: {name}")
    return selected_cards


def _select_special_lands(non_basic_lands, special_land_prefer, special_land_avoid, special_land_limit, allowed_colors):
    logger.debug(f"[DEBUG] Entering _select_special_lands")
    # Only select special lands that can produce at least one of the allowed colors
    filtered = []
    for card in non_basic_lands:
        produces_color = any(f"add {{{color}}}".lower() in (card.text or "").lower() for color in allowed_colors)
        if produces_color:
            filtered.append(card)
    special_lands = []
    for card in filtered:
        text = (card.text or "").lower()
        prefer_score = sum(1 for p in special_land_prefer if p.lower() in text)
        avoid_score = sum(1 for a in special_land_avoid if a.lower() in text)
        special_lands.append((prefer_score - avoid_score, prefer_score, -avoid_score, card.name, card))
    special_lands.sort(reverse=True)
    return [card for *_, card in special_lands[:special_land_limit]]


def _distribute_basic_lands(
        selected_cards, basic_lands, allowed_colors, num_basic_needed, legalities=None
):
    logger.debug(f"[DEBUG] Entering _distribute_basic_lands")
    logger.debug(
        f"[DEBUG] selected_cards before distributing basics: { {k: v.owned_qty for k, v in selected_cards.items()} }")
    logger.debug(f"[DEBUG] num_basic_needed: {num_basic_needed}")
    # Ignore double-faced basic lands (e.g., "Forest // Forest")
    filtered_basics = [card for card in basic_lands if "//" not in card.name]
    logger.debug(f"[DEBUG] filtered_basics: {[card.name for card in filtered_basics]}")
    legal_format = legalities[0] if legalities else None
    result_basics = []
    for card in filtered_basics:
        # Exclude Wastes unless colorless is allowed and it's legal in the format
        if card.name.lower() == "wastes":
            if "C" in allowed_colors and legal_format:
                status = (card.legalities or {}).get(legal_format, '').lower()
                if status == "legal":
                    result_basics.append(card)
            continue
        # Only add basics whose color matches allowed_colors and are legal
        if hasattr(card, "colors") and set(card.colors or []) & set(allowed_colors):
            if legal_format:
                status = (card.legalities or {}).get(legal_format, '').lower()
                if status == "legal":
                    result_basics.append(card)
            else:
                result_basics.append(card)
    logger.debug(f"[DEBUG] result_basics after legality/color filter: {[card.name for card in result_basics]}")
    if not result_basics:
        logger.error("[DEBUG] No basic lands found for allowed colors and legality!")
        raise RuntimeError("No basic lands available to add for the deck colors and format.")

    # Calculate color balance from selected nonland cards
    color_counts = {}
    total = 0
    for card in selected_cards.values():
        if not card.matches_type("land"):
            qty = getattr(card, "owned_qty", 1)
            for color in getattr(card, "colors", []) or []:
                if color in allowed_colors:
                    color_counts[color] = color_counts.get(color, 0) + qty
                    total += qty
    logger.debug(f"[DEBUG] color_counts from nonland cards: {color_counts}, total: {total}")
    # If no nonland cards, distribute evenly
    if not color_counts or total == 0:
        for color in allowed_colors:
            color_counts[color] = 1
        total = len(allowed_colors)
        logger.debug(f"[DEBUG] No nonland color info, defaulting color_counts: {color_counts}, total: {total}")

    # Map color to basic land card
    color_to_basic = {}
    for card in result_basics:
        for color in getattr(card, "colors", []):
            if color in allowed_colors:
                color_to_basic[color] = card
    logger.debug(f"[DEBUG] color_to_basic mapping: { {k: v.name for k, v in color_to_basic.items()} }")

    # Distribute basics proportionally
    basics_distribution = {}
    remaining = num_basic_needed
    for color in allowed_colors:
        portion = int(round(num_basic_needed * color_counts.get(color, 0) / total))
        basics_distribution[color] = portion
        remaining -= portion
    # Assign any remainder to the first color(s)
    for color in list(allowed_colors):
        if remaining <= 0:
            break
        basics_distribution[color] += 1
        remaining -= 1
    logger.debug(f"[DEBUG] basics_distribution: {basics_distribution}")

    # Add basics to selected_cards
    for color, count in basics_distribution.items():
        if count <= 0 or color not in color_to_basic:
            continue
        card = color_to_basic[color]
        if card.name in selected_cards:
            logger.debug(f"[DEBUG] Adding {count} to existing {card.name} (was {selected_cards[card.name].owned_qty})")
            selected_cards[card.name].owned_qty += count
        else:
            logger.debug(f"[DEBUG] Adding new basic {card.name} x{count}")
            card.owned_qty = count
            selected_cards[card.name] = card
    logger.debug(
        f"[DEBUG] selected_cards after distributing basics: { {k: v.owned_qty for k, v in selected_cards.items()} }")


def score_card(card, rules):
    """
    Score a card based on weighting_rules from the YAML key_cards section.
    Supports regex patterns if a rule starts and ends with '/'.
    """
    if not rules:
        return 0
    score = 0
    text = (getattr(card, "text", "") or "").lower()
    rarity = (getattr(card, "rarity", "") or "").lower()
    # Priority text scoring (supports regex)
    for key, val in rules.get("priority_text", {}).items():
        if key.startswith("/") and key.endswith("/"):
            pattern = key[1:-1]
            if re.search(pattern, text, re.IGNORECASE):
                score += val
        else:
            if key.lower() in text:
                score += val
    # Rarity bonus
    for key, val in rules.get("rarity_bonus", {}).items():
        if key.lower() == rarity:
            score += val
    # Mana penalty
    mana_penalty = rules.get("mana_penalty", {})
    if mana_penalty:
        threshold = mana_penalty.get("threshold", None)
        penalty_per_point = mana_penalty.get("penalty_per_point", 0)
        cmc = getattr(card, "converted_mana_cost", 0) or 0
        if threshold is not None and cmc > threshold:
            score -= (cmc - threshold) * penalty_per_point
    return score


def _fill_categories(categories, repo, selected_cards, mana_min, mana_max, max_copies, deck_size, weighting_rules=None,
                     inventory_items=None):
    logger.debug(f"[DEBUG] Entering _fill_categories")
    # Build a lookup for owned quantities if inventory_items is provided
    owned_lookup = {}
    if inventory_items:
        for item in inventory_items:
            owned_lookup[item.card_name] = getattr(item, "quantity", 0)
    for cat, cat_conf in categories.items():
        target = cat_conf.get("target", 0)
        preferred_keywords = cat_conf.get("preferred_keywords", [])
        priority_text = cat_conf.get("priority_text", [])
        cat_cards = []
        for card in repo.get_all_cards():
            if card.name in selected_cards:
                continue
            cmc = getattr(card, "converted_mana_cost", None)
            if mana_min is not None and cmc is not None and cmc < mana_min:
                continue
            if mana_max is not None and cmc is not None and cmc > mana_max:
                continue
            if cat == "creatures" and card.matches_type("creature"):
                cat_cards.append(card)
            elif cat == "removal" and any(txt.lower() in (card.text or "").lower() for txt in priority_text):
                cat_cards.append(card)
            elif cat == "card_draw" and any(txt.lower() in (card.text or "").lower() for txt in priority_text):
                cat_cards.append(card)
            elif cat == "buffs" and any(txt.lower() in (card.text or "").lower() for txt in priority_text):
                cat_cards.append(card)
            elif cat == "utility" and any(txt.lower() in (card.text or "").lower() for txt in priority_text):
                cat_cards.append(card)
        # Score and sort cards if rules are provided
        if weighting_rules:
            cat_cards.sort(key=lambda c: score_card(c, weighting_rules), reverse=True)
        logger.debug(f"Category '{cat}': found {len(cat_cards)} candidates after mana curve filter, target {target}")
        count = 0
        for card in cat_cards:
            if count >= target:
                break
            # Determine how many can be added (respect owned quantity for non-basic lands)
            if card.is_basic_land():
                copies_to_add = min(max_copies, target - count)
            else:
                owned = owned_lookup.get(card.name, max_copies) if inventory_items else max_copies
                already = selected_cards[card.name].owned_qty if card.name in selected_cards else 0
                copies_to_add = min(max_copies, target - count, owned - already)
            if copies_to_add <= 0:
                continue
            if card.name in selected_cards:
                selected_cards[card.name].owned_qty += copies_to_add
            else:
                card.owned_qty = copies_to_add
                selected_cards[card.name] = card
            count += copies_to_add
        logger.debug(f"Category '{cat}': added {count} cards")


def _fill_with_any(repo, selected_cards, deck_size, mana_min, mana_max, max_copies, weighting_rules=None,
                   inventory_items=None):
    logger.debug(f"[DEBUG] Entering _fill_with_any")
    # Build a lookup for owned quantities if inventory_items is provided
    owned_lookup = {}
    if inventory_items:
        for item in inventory_items:
            owned_lookup[item.card_name] = getattr(item, "quantity", 0)
    all_cards = repo.get_all_cards()
    # Score and sort cards if rules are provided (now always use score_card if weighting_rules is present)
    if weighting_rules:
        all_cards.sort(key=lambda c: score_card(c, weighting_rules), reverse=True)
    logger.debug(
        f"Filling up to deck size with any cards, starting with {sum(card.owned_qty for card in selected_cards.values())} cards")
    last_count = -1
    fill_pass = 0
    while sum(card.owned_qty for card in selected_cards.values()) < deck_size and all_cards:
        added_this_pass = 0
        for idx, card in enumerate(all_cards):
            current_total = sum(card.owned_qty for card in selected_cards.values())
            if current_total >= deck_size:
                break
            if card.is_basic_land():
                add_now = min(max_copies, deck_size - current_total)
            else:
                owned = owned_lookup.get(card.name, max_copies) if inventory_items else max_copies
                already = selected_cards[card.name].owned_qty if card.name in selected_cards else 0
                add_now = min(max_copies - already, deck_size - current_total, owned - already)
            if add_now <= 0:
                continue
            if card.name in selected_cards:
                selected_cards[card.name].owned_qty += add_now
            else:
                card.owned_qty = add_now
                selected_cards[card.name] = card
            added_this_pass += add_now
            if idx % 100 == 0 and idx > 0:
                logger.debug(
                    f"Fill loop pass {fill_pass}, idx={idx}, selected_cards={sum(card.owned_qty for card in selected_cards.values())}")
        fill_pass += 1
        logger.debug(
            f"Fill pass {fill_pass} complete, added_this_pass={added_this_pass}, selected_cards={sum(card.owned_qty for card in selected_cards.values())} cards")
        if added_this_pass == 0:
            logger.debug(
                f"No more unique cards to add, stopping fill at {sum(card.owned_qty for card in selected_cards.values())} cards after {fill_pass} passes.")


def _finalize_deck(selected_cards, max_copies, deck_size):
    logger.debug(f"[DEBUG] Entering _finalize_deck")

    # Split into land and non-land cards
    land_cards = [c for c in selected_cards.values() if c.matches_type("land")]
    non_land_cards = [c for c in selected_cards.values() if not c.matches_type("land")]

    final_list = []

    # Add all lands first (basic and non-basic)
    for card in land_cards:
        count = card.owned_qty
        for _ in range(count):
            final_list.append(card)

    # Determine how many non-land cards we can still add
    remaining_slots = deck_size - len(final_list)
    logger.debug(f"[DEBUG] Land cards added: {len(final_list)}, remaining slots for non-land cards: {remaining_slots}")

    # Add non-land cards up to remaining slots
    non_land_added = 0
    for card in non_land_cards:
        count = min(card.owned_qty, max_copies)
        for _ in range(count):
            if non_land_added >= remaining_slots:
                break
            final_list.append(card)
            non_land_added += 1

    # Convert final list into deck dict
    deck_dict = {}
    for card in final_list:
        if card.name in deck_dict:
            deck_dict[card.name].owned_qty += 1
        else:
            card.owned_qty = 1
            deck_dict[card.name] = card

    logger.debug(f"Final deck card count: {sum(c.owned_qty for c in deck_dict.values())} (target {deck_size})")
    return Deck(cards=deck_dict, session=None)


def build_deck_from_yaml(
        yaml_data: Dict[str, Any],
        card_repo: CardRepository,
        inventory_repo: Optional[InventoryRepository] = None
) -> Deck:
    logger.debug(f"[DEBUG] Entering build_deck_from_yaml")
    deck_conf = yaml_data.get("deck", {})
    categories = yaml_data.get("categories", {})
    constraints = yaml_data.get("card_constraints", {})
    priority_cards = yaml_data.get("priority_cards", [])
    mana_base = yaml_data.get("mana_base", {})
    fallback = yaml_data.get("fallback_strategy", {})
    mana_curve = deck_conf.get("mana_curve", {})
    owned_cards_only = deck_conf.get("owned_cards_only", False)

    # Parse key_cards weighting rules if present
    key_cards_conf = deck_conf.get("key_cards", {}) or yaml_data.get("key_cards", {})
    weighting_rules = key_cards_conf.get("weighting_rules", {}) if key_cards_conf else {}

    logger.debug(f"Deck config: {deck_conf}")
    logger.debug(f"Categories: {categories}")
    logger.debug(f"Constraints: {constraints}")
    logger.debug(f"Priority cards: {priority_cards}")
    logger.debug(f"Mana base: {mana_base}")
    logger.debug(f"Fallback: {fallback}")
    logger.debug(f"Mana curve: {mana_curve}")
    logger.debug(f"Key card weighting rules: {weighting_rules}")

    deck_size = deck_conf.get("size", 60)
    max_copies = deck_conf.get("max_card_copies", 4)
    allowed_colors = set(deck_conf.get("colors", []))
    legalities = deck_conf.get("legalities", [])
    color_match_mode = deck_conf.get("color_match_mode", "subset")
    mana_min = mana_curve.get("min", None)
    mana_max = mana_curve.get("max", None)

    # Restrict to owned cards if needed, then filter by color/legality/etc.
    inventory_items = None
    if owned_cards_only and inventory_repo:
        inventory_items = inventory_repo.get_owned_cards()
        repo = card_repo.get_owned_cards_by_inventory(inventory_items)
    else:
        repo = card_repo

    repo = repo.filter_cards(
        color_identity=list(allowed_colors),
        color_mode=color_match_mode,
        legal_in=legalities[0] if legalities else None
    )
    logger.debug(f"Cards after color/legality/min_quantity filter: {len(repo.get_all_cards())}")

    # Pull all basic lands up front using type_query (do NOT filter by ownership)
    basic_lands = card_repo.filter_cards(
        type_query="Basic Land"
    ).get_all_cards()
    logger.debug(f"Pulled {len(basic_lands)} basic lands using type_query='Basic Land'")

    # 1. Priority cards
    selected_cards = _select_priority_cards(priority_cards, card_repo, allowed_colors, color_match_mode, legalities,
                                            max_copies)

    # 2. Mana base (lands)
    land_count = mana_base.get("land_count", 22)
    special_lands_conf = mana_base.get("special_lands", {})
    special_land_limit = special_lands_conf.get("count", 0)
    special_land_prefer = special_lands_conf.get("prefer", [])
    special_land_avoid = special_lands_conf.get("avoid", [])

    all_lands = [card for card in repo.get_all_cards() if card.matches_type("land")]
    logger.debug(f"Found {len(all_lands)} total land cards for mana base")
    non_basic_lands = [card for card in all_lands if not card.is_basic_land()]

    # Only select special lands that actually produce the deck's color(s)
    special_lands = _select_special_lands(
        non_basic_lands, special_land_prefer, special_land_avoid, special_land_limit, allowed_colors
    )
    logger.debug(f"Selected {len(special_lands)} special lands for mana base (limit {special_land_limit})")
    for land in special_lands:
        land.owned_qty = 1
        logger.debug(f"[DEBUG] Adding special land: {land.name} x1")
        selected_cards[land.name] = land

    # Always fill up to land_count with basics, even if not enough special lands
    num_special = len(special_lands)
    num_basic_needed = max(0, land_count - num_special)
    logger.debug(f"Need {num_basic_needed} basic lands to reach land count {land_count}")
    logger.debug(f"[DEBUG] selected_cards before basics: { {k: v.owned_qty for k, v in selected_cards.items()} }")
    _distribute_basic_lands(selected_cards, basic_lands, allowed_colors, num_basic_needed, legalities)
    logger.debug(
        f"Total lands in deck after filling: {sum(card.owned_qty for card in selected_cards.values() if card.matches_type('land'))} "
        f"(should be {land_count})"
    )
    # Debug: Show land breakdown
    land_breakdown = {card.name: card.owned_qty for card in selected_cards.values() if card.matches_type('land')}
    logger.debug(f"Land breakdown: {land_breakdown}")

    # 3. Categories
    _fill_categories(
        categories, repo, selected_cards, mana_min, mana_max, max_copies, deck_size,
        weighting_rules=weighting_rules, inventory_items=inventory_items
    )

    # 4. Fill with any
    fill_with_any = fallback.get("fill_with_any", True)
    if fill_with_any:
        _fill_with_any(
            repo, selected_cards, deck_size, mana_min, mana_max, max_copies,
            weighting_rules=weighting_rules, inventory_items=inventory_items
        )

    # 5. Finalize deck
    deck = _finalize_deck(selected_cards, max_copies, deck_size)
    deck.session = card_repo.session
    return deck
