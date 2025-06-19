import json
import logging
import re
from typing import Any, Dict, List, Optional, Union

import gradio as gr
import pandas as pd
import yaml
from mtg_deck_builder.models.deck_config import DeckConfig

from mtg_deckbuilder_ui.app_config import app_config
from mtg_deckbuilder_ui.utils.ui_helpers import get_config_path, refresh_dropdown
from mtg_deckbuilder_ui.ui.ui_objects import UIElement, UISection, UITab

logger = logging.getLogger(__name__)

__all__ = [
    "get_component_value",
    "extract_color_identities",
    "extract_priority_text",
    "extract_fill_priority",
    "yaml_to_dict",
    "dict_to_yaml",
    "apply_config_to_ui",
    "extract_config_from_ui",
    "safe_update",
    "on_refresh_configs",
    "on_refresh_inventories",
    "on_save_config",
    "on_load_config",
]

# --- Type Definitions ---
ComponentValue = Union[str, int, float, bool, List[Any], Dict[str, Any], None]
Component = Union[gr.Component, None]

# --- Component Type Handlers ---


def handle_text_component(value: Any) -> str:
    """Handle text-based components (Markdown, Code, Textbox)."""
    if value is None:
        return ""
    if isinstance(value, list):
        return "\n".join(
            str(x).encode("utf-8", errors="replace").decode("utf-8") for x in value
        )
    if isinstance(value, dict):
        return yaml.dump(value, default_flow_style=False, allow_unicode=True)
    return str(value).encode("utf-8", errors="replace").decode("utf-8")


def handle_dropdown_component(
    value: Any, is_multiselect: bool
) -> Union[str, List[str]]:
    """Handle dropdown components."""
    if value is None:
        return [] if is_multiselect else ""

    if is_multiselect:
        if isinstance(value, str):
            return [v.strip() for v in value.splitlines() if v.strip()]
        if isinstance(value, list):
            return [str(v) for v in value]
        return []
    else:
        if isinstance(value, list):
            return str(value[0]) if value else ""
        return str(value)


def handle_number_component(value: Any) -> float:
    """Handle number components."""
    if value is None:
        return 0.0
    try:
        return float(value)
    except (ValueError, TypeError):
        logger.warning(
            "[handle_number_component] Failed to convert value to float: %r", value
        )
        return 0.0


def handle_checkbox_component(value: Any) -> bool:
    """Handle checkbox components."""
    if value is None:
        return False
    if isinstance(value, str):
        return value.lower() in ("true", "1", "yes", "on")
    return bool(value)


def handle_dataframe_component(value: Any) -> pd.DataFrame:
    """Handle dataframe components."""
    if value is None:
        return pd.DataFrame()
    if isinstance(value, pd.DataFrame):
        return value
    if isinstance(value, list):
        return pd.DataFrame(value)
    logger.warning(
        "[handle_dataframe_component] Invalid value type for dataframe: %r", type(value)
    )
    return pd.DataFrame()


# --- Main Component Value Coercion ---


def coerce_value_for_component(value: Any, component: Component) -> ComponentValue:
    """Coerce a value to the correct type for a Gradio component."""
    if component is None:
        return value

    try:
        if isinstance(component, (gr.Markdown, gr.Code, gr.Textbox)):
            return handle_text_component(value)

        if isinstance(component, gr.Dropdown):
            return handle_dropdown_component(
                value, getattr(component, "multiselect", False)
            )

        if isinstance(component, gr.CheckboxGroup):
            if not value:
                return []
            if isinstance(value, list):
                return value
            return [str(v).strip() for v in str(value).split(",") if v.strip()]

        if isinstance(component, gr.Number):
            return handle_number_component(value)

        if isinstance(component, gr.Checkbox):
            return handle_checkbox_component(value)

        if isinstance(component, gr.Dataframe):
            return handle_dataframe_component(value)

        logger.warning(
            "[coerce_value_for_component] Unknown component type: %r", type(component)
        )
        return value
    except Exception as e:
        logger.error(
            "[coerce_value_for_component] " "Error coercing value for component: %r", e
        )
        return value


def safe_update(element: UIElement, value: Any = None, **kwargs) -> gr.update:
    """Safely update a UIElement with the given value."""
    if element is None:
        return gr.update(**kwargs)

    try:
        component = element.get_component()
        if component is None:
            return gr.update(**kwargs)

        coerced_value = coerce_value_for_component(value, component)
        return gr.update(value=coerced_value, **kwargs)
    except Exception as e:
        logger.error("[safe_update] Error updating element: %r", e)
        return gr.update(**kwargs)


# --- Utility Functions ---


def get_component_value(element: UIElement, default: Any = None) -> Any:
    """Get the value from a UIElement."""
    if element is None:
        return default

    component = element.get_component()
    if component is None:
        return default

    if hasattr(component, "value"):
        return component.value
    return component if component is not None else default


def extract_color_identities(color_display: List[str]) -> List[str]:
    """Extract color identities (WUBRG) from color display strings."""
    color_identities = []
    if not color_display:
        return []
    for c in color_display:
        if not c:
            continue
        match = re.search(r"\(([WUBRGC])\)", c)
        if match:
            color_identities.append(match.group(1))
        else:
            code = c.strip()
            if code in {"W", "U", "B", "R", "G", "C"}:
                color_identities.append(code)
    logger.debug("[extract_color_identities] Extracted colors: %r", color_identities)
    return color_identities


def parse_priority_cards_text(text: str) -> List[Dict[str, Any]]:
    """Parse priority cards from text format."""
    if not text:
        return []
    cards = []
    for line in text.splitlines():
        if ":" in line:
            name, qty = line.split(":", 1)
            name = name.strip()
            try:
                qty = int(qty.strip())
                if name:
                    cards.append({"name": name, "min_copies": qty})
            except ValueError:
                logger.warning(
                    "[parse_priority_cards_text] " "Invalid quantity format: %r", line
                )
                continue
    logger.debug("[parse_priority_cards_text] Parsed %d priority cards", len(cards))
    return cards


def priority_cards_to_text(cards) -> str:
    """Convert priority cards to simple text format."""
    if not cards:
        return ""
    lines = []
    for card in cards:
        if isinstance(card, dict):
            name = card.get("name", "")
            copies = card.get("min_copies", 1)
        else:
            name = getattr(card, "name", "")
            copies = getattr(card, "min_copies", 1)
        if name:
            lines.append(f"{name}: {copies}")
    logger.debug("[priority_cards_to_text] Converted %d cards to text", len(lines))
    return "\n".join(lines)


def extract_priority_text(priority_text_val):
    """Extracts and validates priority text from various input formats."""
    if isinstance(priority_text_val, dict) and "data" in priority_text_val:
        priority_text_rows = priority_text_val["data"]
    elif isinstance(priority_text_val, pd.DataFrame):
        priority_text_rows = priority_text_val.values.tolist()
    elif priority_text_val is None:
        priority_text_rows = []
    else:
        priority_text_rows = priority_text_val
    priority_text_dict = {}
    for row in priority_text_rows:
        if isinstance(row, (list, tuple)) and len(row) == 2 and row[0]:
            try:
                priority_text_dict[row[0]] = int(row[1])
            except Exception as e:
                logger.warning(
                    "[extract_priority_text] Invalid row format: %r - %r", row, e
                )
                continue
    logger.debug(
        "[extract_priority_text] Extracted %d priority text entries",
        len(priority_text_dict),
    )
    return priority_text_dict


def extract_fill_priority(fill_priority_val):
    """Parses fill priority from string or list."""
    if not fill_priority_val:
        return []
    elif isinstance(fill_priority_val, str):
        result = [x.strip() for x in fill_priority_val.split(",") if x.strip()]
    else:
        result = fill_priority_val
    logger.debug("[extract_fill_priority] Extracted fill priority: %r", result)
    return result


def yaml_to_dict(yaml_str: Optional[str]) -> Dict:
    """Convert YAML string to dictionary."""
    if not yaml_str or not isinstance(yaml_str, str):
        return {}
    try:
        result = yaml.safe_load(yaml_str) or {}
        logger.debug("[yaml_to_dict] Successfully parsed YAML")
        return result
    except Exception as e:
        logger.error("[yaml_to_dict] Failed to parse YAML: %r", e)
        return {}


def dict_to_yaml(d: Dict) -> str:
    """Convert dictionary to YAML string."""
    if not d:
        return ""
    try:
        result = yaml.dump(d, sort_keys=False, allow_unicode=True)
        logger.debug("[dict_to_yaml] Successfully converted dict to YAML")
        return result
    except Exception as e:
        logger.error("[dict_to_yaml] Failed to convert dict to YAML: %r", e)
        return str(d)


def to_dict_or_obj(val):
    """
    Convert a Pydantic model to dict,
    or return as is if already dict or primitive.
    """
    if hasattr(val, "model_dump"):
        return val.model_dump()
    elif hasattr(val, "dict"):
        return val.dict()
    return val


def get_value(root, path: str, default: Any = None) -> Any:
    """
    Get a value from the config using dot notation,
    handling dicts and Pydantic models recursively.
    """
    try:
        value = root
        for key in path.split("."):
            value = to_dict_or_obj(value)
            if isinstance(value, dict):
                value = value.get(key, None)
            elif hasattr(value, key):
                value = getattr(value, key)
            else:
                value = None
        return value if value is not None else default
    except Exception as e:
        logger.error("[get_value] Error getting value at path %r: %r", path, e)
        return default


# --- Main Config Functions ---

COLOR_DISPLAY_MAP = {
    "W": "⚪ White (W)",
    "U": "🔵 Blue (U)",
    "B": "⚫ Black (B)",
    "R": "🔴 Red (R)",
    "G": "🟢 Green (G)",
    "C": "🚫Grey (C)",
}

COLOR_CODE_MAP = {v: k for k, v in COLOR_DISPLAY_MAP.items()}


def apply_config_to_ui(cfg: DeckConfig, tab: UITab) -> Dict[UIElement, Any]:
    """Apply a DeckConfig to UI elements."""
    logger.info("[apply_config_to_ui] Starting to apply config to UI")

    # Always ensure cfg is a DeckConfig model, not a dict
    if isinstance(cfg, dict):
        logger.debug("[apply_config_to_ui] Converting dict to DeckConfig model")
        cfg = DeckConfig.model_validate(cfg)

    # Re-validate to ensure all nested models are instantiated correctly
    if cfg:
        cfg = DeckConfig.model_validate(cfg.model_dump())

    updates = {}

    try:
        # Basic deck info
        logger.debug("[apply_config_to_ui] Applying basic deck info")
        updates[tab.get_element("name")] = safe_update(
            tab.get_element("name"), value=cfg.deck.name
        )
        updates[tab.get_element("size")] = safe_update(
            tab.get_element("size"), value=cfg.deck.size
        )
        updates[tab.get_element("max_card_copies")] = safe_update(
            tab.get_element("max_card_copies"), value=cfg.deck.max_card_copies
        )
        updates[tab.get_element("allow_colorless")] = safe_update(
            tab.get_element("allow_colorless"), value=cfg.deck.allow_colorless
        )
        updates[tab.get_element("color_match_mode")] = safe_update(
            tab.get_element("color_match_mode"), value=cfg.deck.color_match_mode
        )
        updates[tab.get_element("legalities")] = safe_update(
            tab.get_element("legalities"), value=cfg.deck.legalities
        )
        updates[tab.get_element("owned_cards_only")] = safe_update(
            tab.get_element("owned_cards_only"), value=cfg.deck.owned_cards_only
        )

        # Colors
        colors_element = tab.get_element("colors")
        if colors_element:
            # Convert color codes to display format with emojis
            color_display = []
            for color in cfg.deck.colors:
                if color in COLOR_DISPLAY_MAP:
                    color_display.append(COLOR_DISPLAY_MAP[color])
                else:
                    # Handle unknown colors by adding them as is
                    color_display.append(color)
            updates[colors_element] = safe_update(colors_element, value=color_display)

        # Mana curve
        if cfg.deck.mana_curve:
            updates[tab.get_element("mana_curve_min")] = safe_update(
                tab.get_element("mana_curve_min"), value=cfg.deck.mana_curve.min
            )
            updates[tab.get_element("mana_curve_max")] = safe_update(
                tab.get_element("mana_curve_max"), value=cfg.deck.mana_curve.max
            )
            updates[tab.get_element("mana_curve_shape")] = safe_update(
                tab.get_element("mana_curve_shape"),
                value=cfg.deck.mana_curve.curve_shape,
            )
            updates[tab.get_element("mana_curve_slope")] = safe_update(
                tab.get_element("mana_curve_slope"),
                value=cfg.deck.mana_curve.curve_slope,
            )

        # Categories
        for cat_name in ["creatures", "removal", "card_draw", "buffs", "utility"]:
            prefix = f"{cat_name}_"
            cat_config = cfg.categories.get(cat_name)
            if cat_config:
                updates[tab.get_element(f"{prefix}target")] = safe_update(
                    tab.get_element(f"{prefix}target"), value=cat_config.target
                )
                updates[tab.get_element(f"{prefix}keywords")] = safe_update(
                    tab.get_element(f"{prefix}keywords"),
                    value=cat_config.preferred_keywords,
                )
                updates[tab.get_element(f"{prefix}priority_text")] = safe_update(
                    tab.get_element(f"{prefix}priority_text"),
                    value=cat_config.priority_text,
                )
                updates[tab.get_element(f"{prefix}basic_type_priority")] = safe_update(
                    tab.get_element(f"{prefix}basic_type_priority"),
                    value=cat_config.preferred_basic_type_priority,
                )

        # Card constraints
        if cfg.card_constraints:
            updates[tab.get_element("exclude_keywords")] = safe_update(
                tab.get_element("exclude_keywords"),
                value=cfg.card_constraints.exclude_keywords,
            )
            if cfg.card_constraints.rarity_boost:
                updates[tab.get_element("rarity_boost_common")] = safe_update(
                    tab.get_element("rarity_boost_common"),
                    value=cfg.card_constraints.rarity_boost.common,
                )
                updates[tab.get_element("rarity_boost_uncommon")] = safe_update(
                    tab.get_element("rarity_boost_uncommon"),
                    value=cfg.card_constraints.rarity_boost.uncommon,
                )
                updates[tab.get_element("rarity_boost_rare")] = safe_update(
                    tab.get_element("rarity_boost_rare"),
                    value=cfg.card_constraints.rarity_boost.rare,
                )
                updates[tab.get_element("rarity_boost_mythic")] = safe_update(
                    tab.get_element("rarity_boost_mythic"),
                    value=cfg.card_constraints.rarity_boost.mythic,
                )

        # Priority cards
        priority_cards_element = tab.get_element("priority_cards_yaml")
        if priority_cards_element and cfg.priority_cards:
            # Convert priority cards to YAML-like text
            priority_text = []
            for card in cfg.priority_cards:
                priority_text.append(f"{card.name}: {card.min_copies}")
            updates[priority_cards_element] = safe_update(
                priority_cards_element, value="\n".join(priority_text)
            )

        # Mana base
        if cfg.mana_base:
            updates[tab.get_element("land_count")] = safe_update(
                tab.get_element("land_count"), value=cfg.mana_base.land_count
            )
            if cfg.mana_base.special_lands:
                updates[tab.get_element("special_lands_count")] = safe_update(
                    tab.get_element("special_lands_count"),
                    value=cfg.mana_base.special_lands.count,
                )
                updates[tab.get_element("special_lands_prefer")] = safe_update(
                    tab.get_element("special_lands_prefer"),
                    value=cfg.mana_base.special_lands.prefer,
                )
                updates[tab.get_element("special_lands_avoid")] = safe_update(
                    tab.get_element("special_lands_avoid"),
                    value=cfg.mana_base.special_lands.avoid,
                )
            if cfg.mana_base.balance:
                updates[tab.get_element("adjust_by_mana_symbols")] = safe_update(
                    tab.get_element("adjust_by_mana_symbols"),
                    value=cfg.mana_base.balance.adjust_by_mana_symbols,
                )

        # Fallback strategy
        if cfg.fallback_strategy:
            updates[tab.get_element("fill_with_any")] = safe_update(
                tab.get_element("fill_with_any"),
                value=cfg.fallback_strategy.fill_with_any,
            )
            updates[tab.get_element("fill_priority")] = safe_update(
                tab.get_element("fill_priority"),
                value=cfg.fallback_strategy.fill_priority,
            )
            updates[tab.get_element("allow_less_than_target")] = safe_update(
                tab.get_element("allow_less_than_target"),
                value=cfg.fallback_strategy.allow_less_than_target,
            )

        # Scoring rules
        if cfg.scoring_rules:
            # Text matches
            updates[tab.get_element("scoring_text_match")] = safe_update(
                tab.get_element("scoring_text_match"),
                value="\n".join(
                    f"{k}: {v}" for k, v in cfg.scoring_rules.text_matches.items()
                ),
            )
            # Keyword abilities
            updates[tab.get_element("scoring_keyword_abilities")] = safe_update(
                tab.get_element("scoring_keyword_abilities"),
                value="\n".join(
                    f"{k}: {v}" for k, v in cfg.scoring_rules.keyword_abilities.items()
                ),
            )
            # Keyword actions
            updates[tab.get_element("scoring_keyword_actions")] = safe_update(
                tab.get_element("scoring_keyword_actions"),
                value="\n".join(
                    f"{k}: {v}" for k, v in cfg.scoring_rules.keyword_actions.items()
                ),
            )
            # Ability words
            updates[tab.get_element("scoring_ability_words")] = safe_update(
                tab.get_element("scoring_ability_words"),
                value="\n".join(
                    f"{k}: {v}" for k, v in cfg.scoring_rules.ability_words.items()
                ),
            )
            # Type bonuses
            if cfg.scoring_rules.type_bonus:
                updates[tab.get_element("scoring_type_bonus_basic")] = safe_update(
                    tab.get_element("scoring_type_bonus_basic"),
                    value="\n".join(
                        f"{k}: {v}"
                        for k, v in cfg.scoring_rules.type_bonus.basic_types.items()
                    ),
                )
                updates[tab.get_element("scoring_type_bonus_sub")] = safe_update(
                    tab.get_element("scoring_type_bonus_sub"),
                    value="\n".join(
                        f"{k}: {v}"
                        for k, v in cfg.scoring_rules.type_bonus.sub_types.items()
                    ),
                )
                updates[tab.get_element("scoring_type_bonus_super")] = safe_update(
                    tab.get_element("scoring_type_bonus_super"),
                    value="\n".join(
                        f"{k}: {v}"
                        for k, v in cfg.scoring_rules.type_bonus.super_types.items()
                    ),
                )
            # Rarity bonus
            if cfg.scoring_rules.rarity_bonus:
                updates[tab.get_element("rarity_bonus_common")] = safe_update(
                    tab.get_element("rarity_bonus_common"),
                    value=cfg.scoring_rules.rarity_bonus.common,
                )
                updates[tab.get_element("rarity_bonus_uncommon")] = safe_update(
                    tab.get_element("rarity_bonus_uncommon"),
                    value=cfg.scoring_rules.rarity_bonus.uncommon,
                )
                updates[tab.get_element("rarity_bonus_rare")] = safe_update(
                    tab.get_element("rarity_bonus_rare"),
                    value=cfg.scoring_rules.rarity_bonus.rare,
                )
                updates[tab.get_element("rarity_bonus_mythic")] = safe_update(
                    tab.get_element("rarity_bonus_mythic"),
                    value=cfg.scoring_rules.rarity_bonus.mythic,
                )
            # Mana penalty
            if cfg.scoring_rules.mana_penalty:
                updates[tab.get_element("mana_penalty_threshold")] = safe_update(
                    tab.get_element("mana_penalty_threshold"),
                    value=cfg.scoring_rules.mana_penalty.threshold,
                )
                updates[tab.get_element("mana_penalty_per_point")] = safe_update(
                    tab.get_element("mana_penalty_per_point"),
                    value=cfg.scoring_rules.mana_penalty.penalty_per_point,
                )
            # Min score to flag
            updates[tab.get_element("min_score_to_flag")] = safe_update(
                tab.get_element("min_score_to_flag"),
                value=cfg.scoring_rules.min_score_to_flag,
            )

        logger.info("[apply_config_to_ui] Successfully applied config to UI")
        return updates

    except Exception as e:
        logger.error(
            "[apply_config_to_ui] Error applying config to UI: %r", e, exc_info=True
        )
        raise ValueError(f"Error applying config to UI: {str(e)}")


def extract_config_from_ui(tab: UITab) -> DeckConfig:
    """Extract a DeckConfig from UI values.

    Args:
        tab: UITab containing all UI elements

    Returns:
        DeckConfig: Configuration extracted from UI

    Raises:
        ValueError: If required fields are missing or invalid
    """
    logger.debug("[extract_config_from_ui] Starting config extraction")

    # Helper function to get value from UI element
    def get_val(section_name: str, element_name: str) -> Any:
        section = tab.get_section(section_name)
        if not section:
            raise ValueError(f"Section {section_name} not found")
        element = section.get_element(element_name)
        if not element:
            raise ValueError(
                f"Element {element_name} not found in section {section_name}"
            )
        return element.get_value()

    # Helper function to parse scoring text
    def parse_scoring_text(text: str) -> Dict[str, float]:
        if not text:
            return {}
        try:
            return yaml.safe_load(text) or {}
        except Exception as e:
            raise ValueError(f"Invalid scoring text format: {e}")

    # Helper function to parse comma-separated list
    def parse_list(text: str) -> List[str]:
        if not text:
            return []
        return [x.strip() for x in text.split(",") if x.strip()]

    # Helper function to parse priority cards
    def parse_priority_cards(text: str) -> Dict[str, int]:
        if not text:
            return {}
        try:
            return yaml.safe_load(text) or {}
        except Exception as e:
            raise ValueError(f"Invalid priority cards format: {e}")

    try:
        # Extract basic deck info
        deck_info = {
            "name": get_val("deck_identity", "name"),
            "colors": extract_color_identities(get_val("deck_identity", "colors")),
            "size": get_val("deck_identity", "size"),
            "max_card_copies": get_val("deck_identity", "max_card_copies"),
            "allow_colorless": get_val("deck_identity", "allow_colorless"),
            "color_match_mode": get_val("deck_identity", "color_match_mode"),
            "legalities": get_val("deck_identity", "legalities"),
            "owned_cards_only": get_val("inventory", "owned_cards_only"),
            "mana_curve": {
                "min": get_val("mana_curve", "mana_curve_min"),
                "max": get_val("mana_curve", "mana_curve_max"),
                "shape": get_val("mana_curve", "mana_curve_shape"),
                "slope": get_val("mana_curve", "mana_curve_slope"),
            },
            "inventory": get_val("inventory", "inventory_select"),
            "priority_cards": parse_priority_cards(
                get_val("priority_cards", "priority_cards_yaml")
            ),
        }

        # Extract categories
        categories = {
            "creatures": {
                "target": get_val("card_categories", "creatures_target"),
                "keywords": parse_list(
                    get_val("card_categories", "creatures_keywords")
                ),
                "priority_text": parse_list(
                    get_val("card_categories", "creatures_priority_text")
                ),
                "basic_type_priority": parse_list(
                    get_val("card_categories", "creatures_basic_type_priority")
                ),
            },
            "removal": {
                "target": get_val("card_categories", "removal_target"),
                "keywords": parse_list(get_val("card_categories", "removal_keywords")),
                "priority_text": parse_list(
                    get_val("card_categories", "removal_priority_text")
                ),
                "basic_type_priority": parse_list(
                    get_val("card_categories", "removal_basic_type_priority")
                ),
            },
            "card_draw": {
                "target": get_val("card_categories", "card_draw_target"),
                "keywords": parse_list(
                    get_val("card_categories", "card_draw_keywords")
                ),
                "priority_text": parse_list(
                    get_val("card_categories", "card_draw_priority_text")
                ),
                "basic_type_priority": parse_list(
                    get_val("card_categories", "card_draw_basic_type_priority")
                ),
            },
            "buffs": {
                "target": get_val("card_categories", "buffs_target"),
                "keywords": parse_list(get_val("card_categories", "buffs_keywords")),
                "priority_text": parse_list(
                    get_val("card_categories", "buffs_priority_text")
                ),
                "basic_type_priority": parse_list(
                    get_val("card_categories", "buffs_basic_type_priority")
                ),
            },
            "utility": {
                "target": get_val("card_categories", "utility_target"),
                "keywords": parse_list(get_val("card_categories", "utility_keywords")),
                "priority_text": parse_list(
                    get_val("card_categories", "utility_priority_text")
                ),
                "basic_type_priority": parse_list(
                    get_val("card_categories", "utility_basic_type_priority")
                ),
            },
        }

        # Extract scoring rules
        scoring_rules = {
            "text_match": parse_scoring_text(
                get_val("scoring_rules", "scoring_text_match")
            ),
            "keyword_abilities": parse_scoring_text(
                get_val("scoring_rules", "scoring_keyword_abilities")
            ),
            "keyword_actions": parse_scoring_text(
                get_val("scoring_rules", "scoring_keyword_actions")
            ),
            "ability_words": parse_scoring_text(
                get_val("scoring_rules", "scoring_ability_words")
            ),
            "type_bonus_basic": parse_scoring_text(
                get_val("scoring_rules", "scoring_type_bonus_basic")
            ),
            "type_bonus_sub": parse_scoring_text(
                get_val("scoring_rules", "scoring_type_bonus_sub")
            ),
            "type_bonus_super": parse_scoring_text(
                get_val("scoring_rules", "scoring_type_bonus_super")
            ),
            "mana_penalty_threshold": get_val(
                "scoring_rules", "mana_penalty_threshold"
            ),
            "mana_penalty_per_point": get_val(
                "scoring_rules", "mana_penalty_per_point"
            ),
            "rarity_bonus": {
                "common": get_val("scoring_rules", "rarity_bonus_common"),
                "uncommon": get_val("scoring_rules", "rarity_bonus_uncommon"),
                "rare": get_val("scoring_rules", "rarity_bonus_rare"),
                "mythic": get_val("scoring_rules", "rarity_bonus_mythic"),
            },
            "min_score_to_flag": get_val("scoring_rules", "min_score_to_flag"),
        }

        # Extract mana base settings
        mana_base = {
            "land_count": get_val("mana_base", "land_count"),
            "special_lands_count": get_val("mana_base", "special_lands_count"),
            "special_lands_prefer": parse_list(
                get_val("mana_base", "special_lands_prefer")
            ),
            "special_lands_avoid": parse_list(
                get_val("mana_base", "special_lands_avoid")
            ),
            "adjust_by_mana_symbols": get_val("mana_base", "adjust_by_mana_symbols"),
        }

        # Extract fallback strategy
        fallback_strategy = {
            "fill_priority": parse_list(get_val("fallback", "fill_priority")),
            "fill_with_any": get_val("fallback", "fill_with_any"),
            "allow_less_than_target": get_val("fallback", "allow_less_than_target"),
        }

        # Construct and validate DeckConfig
        config = DeckConfig(
            deck=deck_info,
            categories=categories,
            scoring_rules=scoring_rules,
            mana_base=mana_base,
            fallback_strategy=fallback_strategy,
        )

        logger.debug("[extract_config_from_ui] Config extraction complete")
        return config

    except Exception as e:
        logger.exception("[extract_config_from_ui] Error extracting config")
        raise ValueError(f"Error extracting config: {str(e)}")


def on_refresh_configs(config_select: UIElement) -> gr.update:
    """Callback to refresh the list of config files."""
    component = config_select.get_component()
    if component is None:
        return gr.update()
    return refresh_dropdown(
        component, app_config.get_path("deck_configs_dir"), [".yaml", ".yml"]
    )


def on_refresh_inventories(inventory_select: UIElement) -> gr.update:
    """Callback to refresh the list of inventory files."""
    component = inventory_select.get_component()
    if component is None:
        return gr.update()
    return refresh_dropdown(
        component, app_config.get_path("inventory_dir"), [".csv", ".json"]
    )


def on_save_config(save_filename: str, cfg: Dict[str, Any]) -> gr.Info:
    """Callback to save a config to file."""
    try:
        file_path = get_config_path(save_filename)
        # Convert to a clean dict before saving
        deck_config = DeckConfig.model_validate(cfg)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(deck_config.model_dump(), f, indent=4)
        return gr.Info(f"Config saved to {file_path}")
    except Exception as e:
        logger.error("[on_save_config] Failed to save config: %r", e, exc_info=True)
        return gr.Error(f"Failed to save config: {e}")


def on_load_config(selected_file: str, tab: UITab) -> List[gr.update]:
    """Load a YAML config file and update the UI.

    Args:
        selected_file: The selected config file
        tab: The deckbuilder tab

    Returns:
        List of updates for UI components
    """
    try:
        if not selected_file:
            return [gr.update(value="No config file selected")] + [
                gr.update() for _ in tab.get_components().values()
            ]

        # Save the selected config
        app_config.config["UI"]["last_loaded_config"] = selected_file
        app_config.save()

        # Load and apply the config
        config_path = get_config_path(selected_file)
        with open(config_path, "r") as f:
            config_data = yaml.safe_load(f)

        # Update UI components with config data
        updates = []
        for component in tab.get_components().values():
            if hasattr(component, "elem_id"):
                value = config_data.get(component.elem_id)
                if value is not None:
                    updates.append(gr.update(value=value))
                else:
                    updates.append(gr.update())
            else:
                updates.append(gr.update())

        return [gr.update(value=f"Loaded config: {selected_file}")] + updates
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        return [gr.update(value=f"Error loading config: {str(e)}")] + [
            gr.update() for _ in tab.get_components().values()
        ]
