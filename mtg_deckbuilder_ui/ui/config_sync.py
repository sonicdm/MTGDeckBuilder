import gradio as gr
from mtg_deck_builder.deck_config.deck_config import DeckConfig
import pandas as pd

def apply_config_to_ui(cfg: DeckConfig, ui_map):
    """
    Takes a DeckConfig object and returns a dict of gr.update(...) for each UI component key in ui_map.
    Handles all fields in the YAML spec.
    """
    print("[DEBUG] apply_config_to_ui called")
    print(f"[DEBUG] cfg: {cfg}")
    print(f"[DEBUG] ui_map keys: {list(ui_map.keys())}")

    if not cfg:
        return {k: gr.update(value=None) for k in ui_map}

    color_labels = {
        "W": "⚪ White (W)",
        "U": "🔵 Blue (U)",
        "B": "⚫ Black (B)",
        "R": "🔴 Red (R)",
        "G": "🟢 Green (G)",
        "C": "Grey (C)",
    }
    color_display = [color_labels.get(c, c) for c in (cfg.deck.colors if cfg.deck else [])]

    updates = {
        "name": gr.update(value=cfg.deck.name),
        "colors": gr.update(value=color_display),
        "size": gr.update(value=cfg.deck.size),
        "max_card_copies": gr.update(value=cfg.deck.max_card_copies),
        "allow_colorless": gr.update(value=cfg.deck.allow_colorless),
        "legalities": gr.update(value=cfg.deck.legalities),
        "owned_cards_only": gr.update(value=cfg.deck.owned_cards_only),
        "color_match_mode": gr.update(value=cfg.deck.color_match_mode),
        "mana_curve_min": gr.update(value=cfg.deck.mana_curve.get("min")),
        "mana_curve_max": gr.update(value=cfg.deck.mana_curve.get("max")),
        "mana_curve_shape": gr.update(value=cfg.deck.mana_curve.get("curve_shape")),
        "mana_curve_slope": gr.update(value=cfg.deck.mana_curve.get("curve_slope")),
        "exclude_keywords": gr.update(value=cfg.card_constraints.exclude_keywords or []),
        "rarity_boost_common": gr.update(value=cfg.card_constraints.rarity_boost.common),
        "rarity_boost_uncommon": gr.update(value=cfg.card_constraints.rarity_boost.uncommon),
        "rarity_boost_rare": gr.update(value=cfg.card_constraints.rarity_boost.rare),
        "rarity_boost_mythic": gr.update(value=cfg.card_constraints.rarity_boost.mythic),
        "priority_cards": gr.update(value=[[c.name, c.min_copies] for c in cfg.priority_cards]),
        "land_count": gr.update(value=cfg.mana_base.land_count),
        "special_count": gr.update(value=cfg.mana_base.special_lands.count),
        "special_prefer": gr.update(value=cfg.mana_base.special_lands.prefer or []),
        "special_avoid": gr.update(value=cfg.mana_base.special_lands.avoid or []),
        "adjust_mana": gr.update(value=cfg.mana_base.balance.get("adjust_by_mana_symbols", True)),
        "fill_with_any": gr.update(value=cfg.fallback_strategy.fill_with_any),
        "fill_priority": gr.update(value=", ".join(cfg.fallback_strategy.fill_priority or [])),
        "allow_less_than_target": gr.update(value=cfg.fallback_strategy.allow_less_than_target),
        "rarity_bonus_common": gr.update(value=cfg.scoring_rules.rarity_bonus.get("common", 0)),
        "rarity_bonus_uncommon": gr.update(value=cfg.scoring_rules.rarity_bonus.get("uncommon", 0)),
        "rarity_bonus_rare": gr.update(value=cfg.scoring_rules.rarity_bonus.get("rare", 0)),
        "rarity_bonus_mythic": gr.update(value=cfg.scoring_rules.rarity_bonus.get("mythic", 0)),
        "mana_penalty_threshold": gr.update(value=cfg.scoring_rules.mana_penalty.get("threshold")),
        "mana_penalty_per": gr.update(value=cfg.scoring_rules.mana_penalty.get("penalty_per_point")),
        "min_score_to_flag": gr.update(value=cfg.scoring_rules.min_score_to_flag),
    }
    # Convert dict to list of lists for Dataframe
    priority_text_val = []
    if cfg.scoring_rules and cfg.scoring_rules.priority_text:
        if isinstance(cfg.scoring_rules.priority_text, dict):
            priority_text_val = [[k, v] for k, v in cfg.scoring_rules.priority_text.items()]
        elif isinstance(cfg.scoring_rules.priority_text, list):
            priority_text_val = cfg.scoring_rules.priority_text

    updates["priority_text"] = gr.update(value=priority_text_val)
    # Add dynamic category updates
    defined_categories = ["creatures", "removal", "card_draw", "buffs", "utility"]
    for cat_name in defined_categories:
        category_data = cfg.categories.get(cat_name) if cfg.categories else None
        ui_key_target = f"{cat_name}_target"
        if ui_key_target in ui_map:
            updates[ui_key_target] = gr.update(value=category_data.target if category_data else 0)
        ui_key_keywords = f"{cat_name}_keywords"
        if ui_key_keywords in ui_map:
            keywords_list = category_data.preferred_keywords if category_data else []
            updates[ui_key_keywords] = gr.update(value=keywords_list)
        ui_key_priority_text = f"{cat_name}_priority_text"
        if ui_key_priority_text in ui_map:
            priority_text_list = category_data.priority_text if category_data else []
            updates[ui_key_priority_text] = gr.update(value=priority_text_list)

    print(f"[DEBUG] updates dict: {updates}")
    # Only update keys that exist in the UI map
    return {k: updates[k] for k in ui_map if k in updates}

def extract_config_from_ui(ui_map):
    """
    Pulls current UI component values from Gradio state and builds a DeckConfig object.
    """
    color_display = ui_map["colors"].value or []
    color_identities = [c.split("(")[-1].strip(")") for c in color_display]
    config_dict = {
        "deck": {
            "name": ui_map["name"].value,
            "colors": color_identities,
            "size": int(ui_map["size"].value),
            "max_card_copies": int(ui_map["max_card_copies"].value),
            "allow_colorless": ui_map["allow_colorless"].value,
            "legalities": ui_map["legalities"].value,
            "owned_cards_only": ui_map["owned_cards_only"].value,
            "color_match_mode": ui_map["color_match_mode"].value if "color_match_mode" in ui_map else "subset",
            "mana_curve": {
                "min": ui_map.get("mana_curve_min").value if "mana_curve_min" in ui_map else None,
                "max": ui_map.get("mana_curve_max").value if "mana_curve_max" in ui_map else None,
                "curve_shape": ui_map.get("mana_curve_shape").value if "mana_curve_shape" in ui_map else None,
                "curve_slope": ui_map.get("mana_curve_slope").value if "mana_curve_slope" in ui_map else None,
            },
        },
        "card_constraints": {
            "exclude_keywords": ui_map["exclude_keywords"].value or [],
            "rarity_boost": {
                "common": int(ui_map.get("rarity_boost_common").value or 0) if "rarity_boost_common" in ui_map else 0,
                "uncommon": int(ui_map.get("rarity_boost_uncommon").value or 0) if "rarity_boost_uncommon" in ui_map else 0,
                "rare": int(ui_map.get("rarity_boost_rare").value or 0) if "rarity_boost_rare" in ui_map else 0,
                "mythic": int(ui_map.get("rarity_boost_mythic").value or 0) if "rarity_boost_mythic" in ui_map else 0,
            },
        },
        "priority_cards": [
            {"name": row[0], "min_copies": int(row[1])}
            for row in ui_map.get("priority_cards").value if "priority_cards" in ui_map and ui_map.get("priority_cards").value and row[0]
        ],
        "mana_base": {
            "land_count": int(ui_map.get("land_count").value or 0) if "land_count" in ui_map else 22,
            "special_lands": {
                "count": int(ui_map.get("special_count").value or 0) if "special_count" in ui_map else 0,
                "prefer": ui_map.get("special_prefer").value or [] if "special_prefer" in ui_map else [],
                "avoid": ui_map.get("special_avoid").value or [] if "special_avoid" in ui_map else []
            },
            "balance": {
                "adjust_by_mana_symbols": ui_map.get("adjust_mana").value if "adjust_mana" in ui_map else True
            }
        },
        "fallback_strategy": {
            "fill_with_any": ui_map.get("fill_with_any").value if "fill_with_any" in ui_map else True,
            "fill_priority": ui_map.get("fill_priority").value if "fill_priority" in ui_map else [],
            "allow_less_than_target": ui_map.get("allow_less_than_target").value if "allow_less_than_target" in ui_map else False,
        },
        "scoring_rules": {
            "priority_text": ui_map.get("priority_text").value if "priority_text" in ui_map else {},
            "rarity_bonus": {
                "common": int(ui_map.get("rarity_bonus_common").value or 0) if "rarity_bonus_common" in ui_map else 0,
                "uncommon": int(ui_map.get("rarity_bonus_uncommon").value or 0) if "rarity_bonus_uncommon" in ui_map else 0,
                "rare": int(ui_map.get("rarity_bonus_rare").value or 0) if "rarity_bonus_rare" in ui_map else 0,
                "mythic": int(ui_map.get("rarity_bonus_mythic").value or 0) if "rarity_bonus_mythic" in ui_map else 0,
            },
            "mana_penalty": {
                "threshold": int(ui_map.get("mana_penalty_threshold").value or 0) if "mana_penalty_threshold" in ui_map else 0,
                "penalty_per_point": int(ui_map.get("mana_penalty_per").value or 0) if "mana_penalty_per" in ui_map else 0,
            },
            "min_score_to_flag": int(ui_map.get("min_score_to_flag").value or 0) if "min_score_to_flag" in ui_map else None,
        },
    }

    # Dynamically build categories for config_dict
    config_categories = {}
    defined_categories_for_extract = ["creatures", "removal", "card_draw", "buffs", "utility"]
    for cat_name in defined_categories_for_extract:
        cat_data_from_ui = {}
        target_key = f"{cat_name}_target"
        if target_key in ui_map and ui_map.get(target_key).value is not None:
            cat_data_from_ui["target"] = int(ui_map.get(target_key).value or 0)
        keywords_key = f"{cat_name}_keywords"
        if keywords_key in ui_map and ui_map.get(keywords_key).value is not None:
            cat_data_from_ui["preferred_keywords"] = ui_map.get(keywords_key).value or []
        priority_text_key = f"{cat_name}_priority_text"
        if priority_text_key in ui_map and ui_map.get(priority_text_key).value is not None:
            cat_data_from_ui["priority_text"] = ui_map.get(priority_text_key).value or []
        if cat_data_from_ui:
            config_categories[cat_name] = cat_data_from_ui
    if config_categories:
        config_dict["categories"] = config_categories
    # Remove empty/None sections for optional fields
    config_dict = {k: v for k, v in config_dict.items() if v}
    return DeckConfig.model_validate(config_dict)
