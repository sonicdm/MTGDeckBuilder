import logging
import re
from typing import Dict, Optional, List
from mtg_deck_builder.db.models import CardDB, InventoryItemDB
from mtg_deck_builder.models.deck import Deck
from mtg_deck_builder.deck_config.deck_config import (
    CategoryDefinition, PriorityCardEntry, CardConstraintMeta, ScoringRulesMeta
)

logger = logging.getLogger(__name__)


def _run_callback(callbacks, hook_name, **kwargs):
    if callbacks and hook_name in callbacks:
        try:
            callbacks[hook_name](**kwargs)
        except Exception as e:
            logger.warning(f"[CALLBACK ERROR] {hook_name}: {e}")


def _select_priority_cards(priority_cards: List[PriorityCardEntry], card_repo, allowed_colors, color_match_mode, legalities, max_copies, callbacks=None):
    selected_cards: Dict[str, CardDB] = {}
    for pc in priority_cards:
        name = pc.name if hasattr(pc, 'name') else pc["name"]
        min_copies = pc.min_copies if hasattr(pc, 'min_copies') else pc.get("min_copies", 1)
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
            else:
                logger.warning(
                    f"Priority card '{name}' doesn't match color/legality constraints (color_ok={color_ok}, legality_ok={legality_ok})"
                )
        else:
            logger.warning(f"Priority card not found: {name}")
    _run_callback(callbacks, "after_priority_card_select", selected=selected_cards)
    return selected_cards


def _select_special_lands(non_basic_lands, special_land_prefer, special_land_avoid, special_land_limit, allowed_colors, callbacks=None):
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
    selected = [card for *_, card in special_lands[:special_land_limit]]
    _run_callback(callbacks, "after_special_lands", selected=selected)
    return selected


def _distribute_basic_lands(selected_cards, basic_lands, allowed_colors, num_basic_needed, legalities=None, callbacks=None, max_copies=4):
    filtered_basics = [card for card in basic_lands if "//" not in card.name]
    legal_format = legalities[0] if legalities else None
    result_basics = []

    for card in filtered_basics:
        if card.name.lower() == "wastes":
            if "C" in allowed_colors and legal_format:
                status = (card.legalities or {}).get(legal_format, '').lower()
                if status == "legal":
                    result_basics.append(card)
            continue
        if hasattr(card, "colors") and set(card.colors or []) & set(allowed_colors):
            if legal_format:
                status = (card.legalities or {}).get(legal_format, '').lower()
                if status == "legal":
                    result_basics.append(card)
            else:
                result_basics.append(card)

    if not result_basics:
        raise RuntimeError("No basic lands available to add for the deck colors and format.")

    color_counts = {}
    total = 0
    for card in selected_cards.values():
        if not card.matches_type("land"):
            qty = getattr(card, "owned_qty", 1)
            for color in getattr(card, "colors", []) or []:
                if color in allowed_colors:
                    color_counts[color] = color_counts.get(color, 0) + qty
                    total += qty
    if not color_counts or total == 0:
        for color in allowed_colors:
            color_counts[color] = 1
        total = len(allowed_colors)

    color_to_basic = {}
    for card in result_basics:
        for color in getattr(card, "colors", []):
            if color in allowed_colors:
                color_to_basic[color] = card

    basics_distribution = {}
    remaining = num_basic_needed
    for color in allowed_colors:
        portion = int(round(num_basic_needed * color_counts.get(color, 0) / total))
        basics_distribution[color] = portion
        remaining -= portion
    for color in list(allowed_colors):
        if remaining <= 0:
            break
        basics_distribution[color] += 1
        remaining -= 1

    for color, count in basics_distribution.items():
        if count <= 0 or color not in color_to_basic:
            continue
        card = color_to_basic[color]

        # For basic lands, max_copies constraint does not apply.
        # The limit is the calculated 'count' for this color distribution pass.
        actual_add_count = count

        if actual_add_count <= 0:
            continue

        if card.name in selected_cards:
            selected_cards[card.name].owned_qty += actual_add_count
        else:
            # Create a new instance or clone if necessary, ensuring it's a distinct object for the deck
            # For basic lands from a shared repo, it's crucial they are treated as distinct if added to deck
            # or their owned_qty is specific to this deck context.
            card_to_add = card # This might need to be card.clone() or similar if card objects are globally shared
            card_to_add.owned_qty = actual_add_count
            selected_cards[card_to_add.name] = card_to_add

    _run_callback(callbacks, "after_basics", selected=selected_cards)


def _match_priority_text(card, priority_text_list):
    text = (card.text or "").lower()
    for pattern in priority_text_list:
        if pattern.startswith("/") and pattern.endswith("/"):
            try:
                if re.search(pattern[1:-1], text, re.IGNORECASE):
                    return True
            except re.error:
                continue
        elif pattern.lower() in text:
            return True
    return False


def _fill_categories(categories, repo, selected_cards, mana_min, mana_max, max_copies, deck_size, scoring_rules: Optional[ScoringRulesMeta]=None, card_constraints: Optional[CardConstraintMeta]=None, inventory_items=None, callbacks=None):
    owned_lookup = {}
    if inventory_items:
        for item in inventory_items:
            owned_lookup[item.card_name] = getattr(item, "quantity", 0)

    for cat, cat_conf in categories.items():
        if isinstance(cat_conf, dict):
            cat_conf = CategoryDefinition(**cat_conf)

        # New callback point: before_category_fill
        _run_callback(callbacks, f"before_category_fill:{cat}", category_name=cat, category_config=cat_conf, selected_cards_so_far=selected_cards, repo=repo)

        target = cat_conf.target
        priority_text_list = cat_conf.priority_text or []
        preferred_keywords = cat_conf.preferred_keywords or []
        cat_cards = []
        for card in repo.get_all_cards():
            if card.name in selected_cards:
                continue
            cmc = getattr(card, "converted_mana_cost", None)
            if mana_min is not None and cmc is not None and cmc < mana_min:
                continue
            if mana_max is not None and cmc is not None and cmc > mana_max:
                continue
            # Exclude by keywords
            if card_constraints and card_constraints.exclude_keywords:
                if any(kw.lower() in (card.text or "").lower() for kw in card_constraints.exclude_keywords):
                    continue
            # Prefer category type
            if cat == "creatures" and card.matches_type("creature"):
                cat_cards.append(card)
            # Prefer keywords
            elif any(kw.lower() in (card.text or "").lower() for kw in preferred_keywords):
                cat_cards.append(card)
            # Prefer priority text (with regex support)
            elif _match_priority_text(card, priority_text_list):
                cat_cards.append(card)

        # Scoring - Use global score_card
        if scoring_rules:
            cat_cards.sort(key=lambda c: score_card(c, scoring_rules), reverse=True)

        count = 0
        for card in cat_cards:
            if count >= target:
                break
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

        _run_callback(callbacks, f"after_category_fill:{cat}", selected=selected_cards, category=cat)


def _fill_with_any(repo, selected_cards, deck_size, mana_min, mana_max, max_copies, scoring_rules: Optional[ScoringRulesMeta]=None, card_constraints: Optional[CardConstraintMeta]=None, inventory_items=None, callbacks=None):
    owned_lookup = {}
    if inventory_items:
        for item in inventory_items:
            owned_lookup[item.card_name] = getattr(item, "quantity", 0)

    all_cards = repo.get_all_cards()
    candidate_cards = []
    for card in all_cards:
        if card.name in selected_cards:
            continue
        cmc = getattr(card, "converted_mana_cost", None)
        if mana_min is not None and cmc is not None and cmc < mana_min:
            continue
        if mana_max is not None and cmc is not None and cmc > mana_max:
            continue
        if card_constraints and card_constraints.exclude_keywords:
            if any(kw.lower() in (card.text or "").lower() for kw in card_constraints.exclude_keywords):
                continue
        candidate_cards.append(card)

    if scoring_rules:
        candidate_cards.sort(key=lambda c: score_card(c, scoring_rules), reverse=True)

    while sum(card.owned_qty for card in selected_cards.values()) < deck_size and candidate_cards:
        added_this_pass = 0
        for card in list(candidate_cards):
            if sum(card.owned_qty for card in selected_cards.values()) >= deck_size:
                break
            if card.is_basic_land():
                candidate_cards.remove(card)
                continue

            owned = owned_lookup.get(card.name, max_copies) if inventory_items else max_copies
            already = selected_cards[card.name].owned_qty if card.name in selected_cards else 0
            can_add_for_this_card = max_copies - already
            slots_left_in_deck = deck_size - sum(c.owned_qty for c in selected_cards.values())
            available_qty = owned - already

            add_now = min(can_add_for_this_card, slots_left_in_deck, available_qty)

            if add_now <= 0:
                candidate_cards.remove(card)
                continue

            if card.name in selected_cards:
                selected_cards[card.name].owned_qty += add_now
            else:
                card.owned_qty = add_now
                selected_cards[card.name] = card
            added_this_pass += add_now
            candidate_cards.remove(card)

        if added_this_pass == 0:
            break

    _run_callback(callbacks, "after_fallback_fill", selected=selected_cards)


def _finalize_deck(selected_cards, max_copies, deck_size):
    land_cards = [c for c in selected_cards.values() if c.matches_type("land")]
    non_land_cards = [c for c in selected_cards.values() if not c.matches_type("land")]

    final_list = []
    for card in land_cards:
        final_list.extend([card] * card.owned_qty)

    remaining_slots = deck_size - len(final_list)
    non_land_added = 0
    for card in non_land_cards:
        count = min(card.owned_qty, max_copies)
        for _ in range(count):
            if non_land_added >= remaining_slots:
                break
            final_list.append(card)
            non_land_added += 1

    deck_dict = {}
    for card in final_list:
        if card.name in deck_dict:
            deck_dict[card.name].owned_qty += 1
        else:
            card.owned_qty = 1
            deck_dict[card.name] = card

    return Deck(cards=deck_dict, session=None)


def score_card(card: CardDB, scoring_rules_config: Optional[ScoringRulesMeta]) -> int:
    if not scoring_rules_config:
        return 0

    score = 0
    text = (getattr(card, "text", "") or "").lower()
    rarity = (getattr(card, "rarity", "") or "").lower()
    cmc = getattr(card, "converted_mana_cost", 0) or 0

    if scoring_rules_config.priority_text:
        for pattern, weight in scoring_rules_config.priority_text.items():
            if pattern.startswith("/") and pattern.endswith("/"):
                try:
                    if re.search(pattern[1:-1], text, re.IGNORECASE):
                        score += weight
                except re.error:
                    logger.warning(f"Invalid regex in scoring_rules.priority_text: {pattern}")
                    continue
            else:
                if pattern.lower() in text:
                    score += weight

    if scoring_rules_config.rarity_bonus:
        rarity_bonus_dict = scoring_rules_config.rarity_bonus
        if isinstance(rarity_bonus_dict, dict):
            for r_key, val in rarity_bonus_dict.items():
                if r_key.lower() == rarity:
                    score += val
                    break
        else:
            logger.warning("scoring_rules.rarity_bonus is not a dictionary")

    if scoring_rules_config.mana_penalty:
        mana_penalty_dict = scoring_rules_config.mana_penalty
        if isinstance(mana_penalty_dict, dict):
            threshold = mana_penalty_dict.get("threshold")
            penalty_per_point = mana_penalty_dict.get("penalty_per_point", 0)
            if threshold is not None and cmc > threshold:
                score -= (cmc - threshold) * penalty_per_point
        else:
            logger.warning("scoring_rules.mana_penalty is not a dictionary")

    return score


