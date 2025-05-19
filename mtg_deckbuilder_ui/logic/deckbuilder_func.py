import logging
import os
from pathlib import Path
from typing import Any, Dict

from mtg_deck_builder.deck_config.deck_config import DeckConfig
from mtg_deck_builder.yaml_builder.yaml_deckbuilder import build_deck_from_config
from mtg_deckbuilder_ui.app_config import DECK_CONFIGS_DIR

log = logging.getLogger(__name__)


def extract_config_from_ui(form_data: Dict[str, Any]) -> DeckConfig:
    """
    Build a DeckConfig object from flat UI form data, matching the YAML spec and DeckConfig model.
    """
    try:
        # Parse mana_curve as a dict
        mana_curve = form_data.get("mana_curve", None)
        if not mana_curve:
            mana_curve = {
                "min": int(form_data.get("mana_curve_min", 1)),
                "max": int(form_data.get("mana_curve_max", 8)),
                "curve_shape": form_data.get("mana_curve_shape", "bell"),
                "curve_slope": form_data.get("mana_curve_slope", "up"),
            }
        # Parse categories
        categories = {}
        for cat in ["creatures", "removal", "card_draw", "buffs", "utility"]:
            categories[cat] = {
                "target": int(form_data.get(f"{cat}_target", 0)),
                "preferred_keywords": [kw.strip() for kw in form_data.get(f"{cat}_keywords", "").split(",") if kw.strip()],
                "priority_text": [pt.strip() for pt in form_data.get(f"{cat}_priority_text", "").split(",") if pt.strip()],
            }
        # Parse rarity_boost
        rarity_boost = {
            "common": int(form_data.get("rarity_boost_common", 0)),
            "uncommon": int(form_data.get("rarity_boost_uncommon", 0)),
            "rare": int(form_data.get("rarity_boost_rare", 0)),
            "mythic": int(form_data.get("rarity_boost_mythic", 0)),
        }
        # Parse scoring_rules.rarity_bonus
        rarity_bonus = {
            "common": int(form_data.get("rarity_bonus_common", 0)),
            "uncommon": int(form_data.get("rarity_bonus_uncommon", 0)),
            "rare": int(form_data.get("rarity_bonus_rare", 0)),
            "mythic": int(form_data.get("rarity_bonus_mythic", 0)),
        }
        # Parse scoring_rules.priority_text
        priority_text = form_data.get("priority_text", {})
        if isinstance(priority_text, str):
            # Try to parse as JSON or YAML mapping, fallback to empty dict
            import json, yaml as pyyaml
            try:
                priority_text = json.loads(priority_text)
            except Exception:
                try:
                    priority_text = pyyaml.safe_load(priority_text)
                except Exception:
                    priority_text = {}
        # Parse mana_penalty
        mana_penalty = {
            "threshold": int(form_data.get("mana_penalty_threshold", 0)),
            "penalty_per_point": int(form_data.get("mana_penalty_per", 0)),
        }
        # Parse fill_priority
        fill_priority = [cat.strip() for cat in form_data.get("fill_priority", "").split(",") if cat.strip()]
        # Parse exclude_keywords
        exclude_keywords = [kw.strip() for kw in form_data.get("exclude_keywords", "").split(",") if kw.strip()]
        # Parse priority_cards
        priority_cards = [
            {"name": row[0], "min_copies": int(row[1])}
            for row in form_data.get("priority_cards", []) if row and row[0]
        ]
        # Parse mana_base
        mana_base = {
            "land_count": int(form_data.get("land_count", 22)),
            "special_lands": {
                "count": int(form_data.get("special_count", 0)),
                "prefer": [p.strip() for p in form_data.get("special_prefer", "").split(",") if p.strip()],
                "avoid": [a.strip() for a in form_data.get("special_avoid", "").split(",") if a.strip()],
            },
            "balance": {
                "adjust_by_mana_symbols": bool(form_data.get("adjust_mana", True))
            },
        }
        config_dict = {
            "deck": {
                "name": form_data.get("deck_name", ""),
                "colors": form_data.get("deck_colors", []),
                "size": int(form_data.get("deck_size", 60)),
                "max_card_copies": int(form_data.get("max_card_copies", 4)),
                "legalities": [form_data.get("format")] if form_data.get("format") else [],
                "color_match_mode": form_data.get("color_match_mode", "subset"),
                "allow_colorless": form_data.get("allow_colorless", False),
                "owned_cards_only": form_data.get("owned_cards_only", True),
                "mana_curve": mana_curve,
            },
            "categories": categories,
            "card_constraints": {
                "rarity_boost": rarity_boost,
                "exclude_keywords": exclude_keywords,
            },
            "priority_cards": priority_cards,
            "mana_base": mana_base,
            "fallback_strategy": {
                "fill_with_any": bool(form_data.get("fill_with_any", True)),
                "fill_priority": fill_priority,
                "allow_less_than_target": bool(form_data.get("allow_less_than_target", False)),
            },
            "scoring_rules": {
                "priority_text": priority_text,
                "rarity_bonus": rarity_bonus,
                "mana_penalty": mana_penalty,
                "min_score_to_flag": int(form_data.get("min_score_to_flag", 0)),
            },
        }
        # Remove empty/None sections for optional fields
        config_dict = {k: v for k, v in config_dict.items() if v}
        return DeckConfig.model_validate(config_dict)
    except Exception as e:
        raise ValueError(f"[extract_config_from_ui] Failed to parse config: {e}")


def load_config_to_ui(config_or_path: Any) -> Dict[str, Any]:
    try:
        if isinstance(config_or_path, str) or isinstance(config_or_path, Path):
            log.debug(f"[DEBUG] Interpreting config input as file path: {config_or_path}")
            config = DeckConfig.from_yaml(Path(DECK_CONFIGS_DIR) / config_or_path)
        elif isinstance(config_or_path, DeckConfig):
            config = config_or_path
        else:
            raise TypeError("Unsupported input type for load_config_to_ui")

        # Extract deck fields
        deck = config.deck
        categories = config.categories or {}
        card_constraints = config.card_constraints or {}
        scoring_rules = config.scoring_rules or {}
        mana_base = config.mana_base or {}
        fallback_strategy = config.fallback_strategy or {}

        def get_cat_attr(cat, attr, default):
            if cat is None:
                return default
            if isinstance(cat, dict):
                return cat.get(attr, default)
            return getattr(cat, attr, default)

        ui_data = {
            "deck_name": deck.name,
            "deck_colors": deck.colors,
            "deck_size": deck.size,
            "max_card_copies": deck.max_card_copies,
            "format": deck.legalities[0] if deck.legalities else None,
            "color_match_mode": deck.color_match_mode,
            "allow_colorless": deck.allow_colorless,
            "owned_cards_only": deck.owned_cards_only,
            "mana_curve": deck.mana_curve,
            "land_count": mana_base.land_count if hasattr(mana_base, 'land_count') else 22,
            "special_lands_count": mana_base.special_lands.count if hasattr(mana_base, 'special_lands') and mana_base.special_lands else 0,
            "special_lands_prefer": mana_base.special_lands.prefer if hasattr(mana_base, 'special_lands') and mana_base.special_lands else [],
            "special_lands_avoid": mana_base.special_lands.avoid if hasattr(mana_base, 'special_lands') and mana_base.special_lands else [],
            "adjust_by_mana_symbols": mana_base.balance.get("adjust_by_mana_symbols", True) if hasattr(mana_base, 'balance') and mana_base.balance else True,
            # Categories
            "creature_target": get_cat_attr(categories.get("creatures"), "target", 0),
            "creature_keywords": get_cat_attr(categories.get("creatures"), "preferred_keywords", []),
            "creature_priority_text": get_cat_attr(categories.get("creatures"), "priority_text", []),
            "removal_target": get_cat_attr(categories.get("removal"), "target", 0),
            "removal_priority_text": get_cat_attr(categories.get("removal"), "priority_text", []),
            "card_draw_target": get_cat_attr(categories.get("card_draw"), "target", 0),
            "card_draw_priority_text": get_cat_attr(categories.get("card_draw"), "priority_text", []),
            "buffs_target": get_cat_attr(categories.get("buffs"), "target", 0),
            "buffs_priority_text": get_cat_attr(categories.get("buffs"), "priority_text", []),
            "utility_target": get_cat_attr(categories.get("utility"), "target", 0),
            # Card constraints
            "rarity_boost": getattr(card_constraints, 'rarity_boost', {}),
            "exclude_keywords": getattr(card_constraints, 'exclude_keywords', []),
            # Priority cards
            "priority_cards": [[card.name, card.min_copies] for card in (config.priority_cards or [])],
            # Fallback strategy
            "fill_with_any": getattr(fallback_strategy, 'fill_with_any', True),
            "fill_priority": getattr(fallback_strategy, 'fill_priority', []),
            "allow_less_than_target": getattr(fallback_strategy, 'allow_less_than_target', False),
            # Scoring rules
            "priority_text": getattr(scoring_rules, 'priority_text', {}),
            "rarity_bonus": getattr(scoring_rules, 'rarity_bonus', {}),
            "mana_penalty": getattr(scoring_rules, 'mana_penalty', {}),
            "min_score_to_flag": getattr(scoring_rules, 'min_score_to_flag', None),
        }
        return ui_data
    except Exception as e:
        log.exception("[load_config_to_ui] Error loading config")
        raise


def run_deckbuilder(form_data: Dict[str, Any], session, card_repo, inventory_repo):
    try:
        config = extract_config_from_ui(form_data)
        deck = build_deck_from_config(config, card_repo, inventory_repo)
        deck.session = session

        summary = f"Deck generated with {sum(card.owned_qty for card in deck.cards.values())} cards."
        card_rows = [
            [
                card.name,
                card.type or "",
                card.rarity or "",
                ", ".join(card.colors or []),
                card.mana_cost or "",
                card.converted_mana_cost or 0,
                card.owned_qty,
            ]
            for card in deck.cards.values()
        ]
        tooltips = [card.text or "" for card in deck.cards.values()]
        return summary, card_rows, tooltips
    except Exception as e:
        log.exception("[run_deckbuilder] Deck generation failed")
        return f"Deck generation failed: {e}", [], [], None


def save_deckbuilder_config(filename: str, form_data: Dict[str, Any]):
    try:
        config = extract_config_from_ui(form_data)
        if not filename.endswith(".yaml"):
            filename += ".yaml"
        output_path = Path(DECK_CONFIGS_DIR) / filename
        config.to_yaml(output_path)
        log.debug(f"[save_deckbuilder_config] Saved to {output_path}")
    except Exception as e:
        log.exception(f"[save_deckbuilder_config] Failed to save config to {filename}")
        raise
