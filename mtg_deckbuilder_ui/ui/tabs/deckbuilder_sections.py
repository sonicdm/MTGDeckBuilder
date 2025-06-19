# Standard library imports
import logging
from typing import Dict, Any, List

# Third-party imports
import gradio as gr

# Local application imports
from mtg_deckbuilder_ui.ui.ui_objects import UISection
from mtg_deck_builder.models.deck_config import (
    DeckConfig,
    DeckMeta,
    ManaCurveMeta,
    CategoryDefinition,
    CardConstraintMeta,
    RarityBoostMeta,
    ManaBaseMeta,
    SpecialLandsMeta,
    ScoringRulesMeta,
    FallbackStrategyMeta,
)

# Set up logger
logger = logging.getLogger(__name__)


def validate_number(value: Any, min_val: int, max_val: int, default: int) -> int:
    """Validate and convert a number value."""
    try:
        num = int(value)
        return max(min_val, min(max_val, num))
    except (ValueError, TypeError):
        return default


def validate_bool(value: Any, default: bool) -> bool:
    """Validate and convert a boolean value."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ("true", "1", "yes", "y")
    return default


def validate_list(value: Any, default: List[str]) -> List[str]:
    """Validate and convert a list value."""
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        return [x.strip() for x in value.split(",") if x.strip()]
    return default


def create_deck_identity_section() -> UISection:
    """Create the deck identity section."""
    section = UISection("deck_identity", "Deck Identity")

    with section:
        with gr.Row():
            name = gr.Textbox(
                label="Deck Name", placeholder="Enter deck name", elem_id="name"
            )
            colors = gr.CheckboxGroup(
                label="Colors",
                choices=[
                    "⚪ White (W)",
                    "🔵 Blue (U)",
                    "⚫ Black (B)",
                    "🔴 Red (R)",
                    "🟢 Green (G)",
                    "🚫Grey (C)",
                ],
                elem_id="colors",
            )
        with gr.Row():
            size = gr.Number(
                label="Deck Size",
                value=60,
                minimum=40,
                maximum=100,
                step=1,
                elem_id="size",
            )
            max_card_copies = gr.Number(
                label="Max Copies",
                value=4,
                minimum=1,
                maximum=4,
                step=1,
                elem_id="max_card_copies",
            )
        with gr.Row():
            allow_colorless = gr.Checkbox(
                label="Allow Colorless", value=True, elem_id="allow_colorless"
            )
            color_match_mode = gr.Dropdown(
                label="Color Match Mode",
                choices=["exact", "subset", "superset"],
                value="exact",
                elem_id="color_match_mode",
            )
        legalities = gr.Dropdown(
            label="Legalities",
            choices=["standard", "modern", "pioneer", "commander"],
            multiselect=True,
            value=["standard"],
            elem_id="legalities",
        )
        owned_cards_only = gr.Checkbox(
            label="Use Owned Cards Only", value=True, elem_id="owned_cards_only"
        )

    return section


def create_mana_curve_section() -> UISection:
    """Create the mana curve section."""
    section = UISection("mana_curve", "Mana Curve")

    with section:
        with gr.Row():
            mana_curve_min = gr.Number(
                label="Min CMC",
                value=0,
                minimum=0,
                maximum=20,
                step=1,
                elem_id="mana_curve_min",
            )
            mana_curve_max = gr.Number(
                label="Max CMC",
                value=7,
                minimum=0,
                maximum=20,
                step=1,
                elem_id="mana_curve_max",
            )
        with gr.Row():
            mana_curve_shape = gr.Dropdown(
                label="Curve Shape",
                choices=["bell", "linear", "exponential"],
                value="bell",
                elem_id="mana_curve_shape",
            )
            mana_curve_slope = gr.Slider(
                label="Curve Slope",
                minimum=-1.0,
                maximum=1.0,
                value=0.0,
                step=0.1,
                elem_id="mana_curve_slope",
            )

    return section


def create_card_categories_section() -> UISection:
    """Create the card categories section."""
    section = UISection("card_categories", "Card Categories")

    with section:
        # Creatures
        with gr.Group():
            gr.Markdown("### Creatures")
            with gr.Row():
                creatures_target = gr.Number(
                    label="Target Count",
                    value=24,
                    minimum=0,
                    maximum=100,
                    step=1,
                    elem_id="creatures_target",
                )
                creatures_keywords = gr.Textbox(
                    label="Keywords",
                    placeholder="Enter keywords (comma-separated)",
                    elem_id="creatures_keywords",
                )
            with gr.Row():
                creatures_priority_text = gr.Textbox(
                    label="Priority Text",
                    placeholder="Enter priority text patterns",
                    elem_id="creatures_priority_text",
                )
                creatures_basic_type_priority = gr.Textbox(
                    label="Basic Type Priority",
                    placeholder="Enter basic type priorities",
                    elem_id="creatures_basic_type_priority",
                )

        # Removal
        with gr.Group():
            gr.Markdown("### Removal")
            with gr.Row():
                removal_target = gr.Number(
                    label="Target Count",
                    value=8,
                    minimum=0,
                    maximum=100,
                    step=1,
                    elem_id="removal_target",
                )
                removal_keywords = gr.Textbox(
                    label="Keywords",
                    placeholder="Enter keywords (comma-separated)",
                    elem_id="removal_keywords",
                )
            with gr.Row():
                removal_priority_text = gr.Textbox(
                    label="Priority Text",
                    placeholder="Enter priority text patterns",
                    elem_id="removal_priority_text",
                )
                removal_basic_type_priority = gr.Textbox(
                    label="Basic Type Priority",
                    placeholder="Enter basic type priorities",
                    elem_id="removal_basic_type_priority",
                )

        # Card Draw
        with gr.Group():
            gr.Markdown("### Card Draw")
            with gr.Row():
                card_draw_target = gr.Number(
                    label="Target Count",
                    value=8,
                    minimum=0,
                    maximum=100,
                    step=1,
                    elem_id="card_draw_target",
                )
                card_draw_keywords = gr.Textbox(
                    label="Keywords",
                    placeholder="Enter keywords (comma-separated)",
                    elem_id="card_draw_keywords",
                )
            with gr.Row():
                card_draw_priority_text = gr.Textbox(
                    label="Priority Text",
                    placeholder="Enter priority text patterns",
                    elem_id="card_draw_priority_text",
                )
                card_draw_basic_type_priority = gr.Textbox(
                    label="Basic Type Priority",
                    placeholder="Enter basic type priorities",
                    elem_id="card_draw_basic_type_priority",
                )

        # Buffs
        with gr.Group():
            gr.Markdown("### Buffs")
            with gr.Row():
                buffs_target = gr.Number(
                    label="Target Count",
                    value=8,
                    minimum=0,
                    maximum=100,
                    step=1,
                    elem_id="buffs_target",
                )
                buffs_keywords = gr.Textbox(
                    label="Keywords",
                    placeholder="Enter keywords (comma-separated)",
                    elem_id="buffs_keywords",
                )
            with gr.Row():
                buffs_priority_text = gr.Textbox(
                    label="Priority Text",
                    placeholder="Enter priority text patterns",
                    elem_id="buffs_priority_text",
                )
                buffs_basic_type_priority = gr.Textbox(
                    label="Basic Type Priority",
                    placeholder="Enter basic type priorities",
                    elem_id="buffs_basic_type_priority",
                )

        # Utility
        with gr.Group():
            gr.Markdown("### Utility")
            with gr.Row():
                utility_target = gr.Number(
                    label="Target Count",
                    value=12,
                    minimum=0,
                    maximum=100,
                    step=1,
                    elem_id="utility_target",
                )
                utility_keywords = gr.Textbox(
                    label="Keywords",
                    placeholder="Enter keywords (comma-separated)",
                    elem_id="utility_keywords",
                )
            with gr.Row():
                utility_priority_text = gr.Textbox(
                    label="Priority Text",
                    placeholder="Enter priority text patterns",
                    elem_id="utility_priority_text",
                )
                utility_basic_type_priority = gr.Textbox(
                    label="Basic Type Priority",
                    placeholder="Enter basic type priorities",
                    elem_id="utility_basic_type_priority",
                )

    return section


def create_card_constraints_section() -> UISection:
    """Create the card constraints section."""
    section = UISection("card_constraints", "Card Constraints")

    with section:
        exclude_keywords = gr.Textbox(
            label="Exclude Keywords",
            placeholder="Enter keywords to exclude (comma-separated)",
            elem_id="exclude_keywords",
        )
        with gr.Row():
            rarity_boost_common = gr.Number(
                label="Common Boost",
                value=0,
                minimum=-10,
                maximum=10,
                step=1,
                elem_id="rarity_boost_common",
            )
            rarity_boost_uncommon = gr.Number(
                label="Uncommon Boost",
                value=0,
                minimum=-10,
                maximum=10,
                step=1,
                elem_id="rarity_boost_uncommon",
            )
        with gr.Row():
            rarity_boost_rare = gr.Number(
                label="Rare Boost",
                value=0,
                minimum=-10,
                maximum=10,
                step=1,
                elem_id="rarity_boost_rare",
            )
            rarity_boost_mythic = gr.Number(
                label="Mythic Boost",
                value=0,
                minimum=-10,
                maximum=10,
                step=1,
                elem_id="rarity_boost_mythic",
            )

    return section


def create_scoring_rules_section() -> UISection:
    """Create the scoring rules section."""
    section = UISection("scoring_rules", "Scoring Rules")

    with section:
        scoring_text_match = gr.Textbox(
            label="Text Match Patterns",
            placeholder="Enter text match patterns (comma-separated)",
            elem_id="scoring_text_match",
        )
        with gr.Row():
            scoring_keyword_abilities = gr.Textbox(
                label="Keyword Abilities",
                placeholder="Enter keyword abilities (comma-separated)",
                elem_id="scoring_keyword_abilities",
            )
            scoring_keyword_actions = gr.Textbox(
                label="Keyword Actions",
                placeholder="Enter keyword actions (comma-separated)",
                elem_id="scoring_keyword_actions",
            )
        scoring_ability_words = gr.Textbox(
            label="Ability Words",
            placeholder="Enter ability words (comma-separated)",
            elem_id="scoring_ability_words",
        )
        with gr.Row():
            scoring_type_bonus_basic = gr.Number(
                label="Basic Type Bonus",
                value=1,
                minimum=0,
                maximum=10,
                step=1,
                elem_id="scoring_type_bonus_basic",
            )
            scoring_type_bonus_sub = gr.Number(
                label="Sub Type Bonus",
                value=2,
                minimum=0,
                maximum=10,
                step=1,
                elem_id="scoring_type_bonus_sub",
            )
            scoring_type_bonus_super = gr.Number(
                label="Super Type Bonus",
                value=3,
                minimum=0,
                maximum=10,
                step=1,
                elem_id="scoring_type_bonus_super",
            )
        with gr.Row():
            mana_penalty_threshold = gr.Number(
                label="Mana Penalty Threshold",
                value=4,
                minimum=0,
                maximum=20,
                step=1,
                elem_id="mana_penalty_threshold",
            )
            mana_penalty_per_point = gr.Number(
                label="Mana Penalty Per Point",
                value=1,
                minimum=0,
                maximum=10,
                step=1,
                elem_id="mana_penalty_per_point",
            )
        with gr.Row():
            rarity_bonus_common = gr.Number(
                label="Common Bonus",
                value=0,
                minimum=-10,
                maximum=10,
                step=1,
                elem_id="rarity_bonus_common",
            )
            rarity_bonus_uncommon = gr.Number(
                label="Uncommon Bonus",
                value=1,
                minimum=-10,
                maximum=10,
                step=1,
                elem_id="rarity_bonus_uncommon",
            )
        with gr.Row():
            rarity_bonus_rare = gr.Number(
                label="Rare Bonus",
                value=2,
                minimum=-10,
                maximum=10,
                step=1,
                elem_id="rarity_bonus_rare",
            )
            rarity_bonus_mythic = gr.Number(
                label="Mythic Bonus",
                value=3,
                minimum=-10,
                maximum=10,
                step=1,
                elem_id="rarity_bonus_mythic",
            )
        min_score_to_flag = gr.Number(
            label="Min Score to Flag",
            value=5,
            minimum=0,
            maximum=100,
            step=1,
            elem_id="min_score_to_flag",
        )

    return section


def create_priority_cards_section() -> UISection:
    """Create the priority cards section."""
    section = UISection("priority_cards", "Priority Cards")

    with section:
        priority_cards_yaml = gr.Textbox(
            label="Priority Cards YAML",
            placeholder="Enter priority cards in YAML format",
            lines=10,
            elem_id="priority_cards_yaml",
        )

    return section


def create_mana_base_section() -> UISection:
    """Create the mana base section."""
    section = UISection("mana_base", "Mana Base")

    with section:
        with gr.Row():
            land_count = gr.Number(
                label="Land Count",
                value=24,
                minimum=0,
                maximum=100,
                step=1,
                elem_id="land_count",
            )
            special_lands_count = gr.Number(
                label="Special Lands Count",
                value=4,
                minimum=0,
                maximum=100,
                step=1,
                elem_id="special_lands_count",
            )
        with gr.Row():
            special_lands_prefer = gr.Textbox(
                label="Prefer Lands",
                placeholder="Enter preferred land types (comma-separated)",
                elem_id="special_lands_prefer",
            )
            special_lands_avoid = gr.Textbox(
                label="Avoid Lands",
                placeholder="Enter land types to avoid (comma-separated)",
                elem_id="special_lands_avoid",
            )
        adjust_by_mana_symbols = gr.Checkbox(
            label="Adjust by Mana Symbols", value=True, elem_id="adjust_by_mana_symbols"
        )

    return section


def create_fallback_section() -> UISection:
    """Create the fallback section."""
    section = UISection("fallback", "Fallback Strategy")

    with section:
        fill_priority = gr.Dropdown(
            label="Fill Priority",
            choices=["creatures", "removal", "card_draw", "buffs", "utility"],
            multiselect=True,
            value=["creatures", "removal", "card_draw", "buffs", "utility"],
            elem_id="fill_priority",
        )
        fill_with_any = gr.Checkbox(
            label="Fill with Any Cards", value=True, elem_id="fill_with_any"
        )
        allow_less_than_target = gr.Checkbox(
            label="Allow Less Than Target",
            value=False,
            elem_id="allow_less_than_target",
        )

    return section


def create_output_section() -> UISection:
    """Create the output section."""
    section = UISection("output", "Output")

    with section:
        with gr.Row():
            card_table_columns = gr.Dropdown(
                label="Table Columns",
                choices=["name", "type", "cmc", "colors", "rarity", "set"],
                multiselect=True,
                value=["name", "type", "cmc", "colors", "rarity", "set"],
                elem_id="card_table_columns",
            )
            build_btn = gr.Button("Build Deck", variant="primary", elem_id="build_btn")
        card_table = gr.Dataframe(
            headers=["Name", "Type", "CMC", "Colors", "Rarity", "Set"],
            elem_id="card_table",
        )
        with gr.Row():
            deck_info = gr.Textbox(label="Deck Info", lines=3, elem_id="deck_info")
            deck_stats = gr.Textbox(label="Deck Stats", lines=3, elem_id="deck_stats")
        arena_export = gr.Textbox(label="Arena Export", lines=5, elem_id="arena_export")
        deck_state = gr.JSON(label="Deck State", elem_id="deck_state")
        build_status = gr.Textbox(
            label="Build Status", visible=False, elem_id="build_status"
        )
        with gr.Row():
            copy_btn = gr.Button("Copy to Clipboard", elem_id="copy_btn")
            send_to_viewer_btn = gr.Button(
                "Send to Viewer", elem_id="send_to_viewer_btn"
            )

    return section


def validate_form_data(form_data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate form data before creating DeckConfig."""
    validated = {}

    # Deck identity
    validated["name"] = str(form_data.get("name", ""))
    validated["colors"] = validate_list(form_data.get("colors", []), [])
    validated["size"] = validate_number(form_data.get("size", 60), 40, 100, 60)
    validated["max_card_copies"] = validate_number(
        form_data.get("max_card_copies", 4), 1, 4, 4
    )
    validated["allow_colorless"] = validate_bool(
        form_data.get("allow_colorless", True), True
    )
    validated["color_match_mode"] = str(form_data.get("color_match_mode", "exact"))
    validated["legalities"] = validate_list(
        form_data.get("legalities", []), ["standard"]
    )
    validated["owned_cards_only"] = validate_bool(
        form_data.get("owned_cards_only", True), True
    )

    # Mana curve
    validated["mana_curve"] = {
        "min": validate_number(form_data.get("mana_curve_min", 0), 0, 20, 0),
        "max": validate_number(form_data.get("mana_curve_max", 7), 0, 20, 7),
        "curve_shape": str(form_data.get("mana_curve_shape", "bell")),
        "curve_slope": str(form_data.get("mana_curve_slope", "0.0")),
    }

    # Categories
    categories = {}
    for category in ["creatures", "removal", "card_draw", "buffs", "utility"]:
        categories[category] = {
            "target": validate_number(
                form_data.get(f"{category}_target", 0), 0, 100, 0
            ),
            "preferred_keywords": validate_list(
                form_data.get(f"{category}_keywords", ""), []
            ),
            "priority_text": validate_list(
                form_data.get(f"{category}_priority_text", ""), []
            ),
            "preferred_basic_type_priority": validate_list(
                form_data.get(f"{category}_basic_type_priority", ""), []
            ),
        }
    validated["categories"] = categories

    # Card constraints
    validated["card_constraints"] = {
        "exclude_keywords": validate_list(form_data.get("exclude_keywords", ""), []),
        "rarity_boost": {
            "common": validate_number(
                form_data.get("rarity_boost_common", 0), -10, 10, 0
            ),
            "uncommon": validate_number(
                form_data.get("rarity_boost_uncommon", 0), -10, 10, 0
            ),
            "rare": validate_number(form_data.get("rarity_boost_rare", 0), -10, 10, 0),
            "mythic": validate_number(
                form_data.get("rarity_boost_mythic", 0), -10, 10, 0
            ),
        },
    }

    # Scoring rules
    validated["scoring_rules"] = {
        "text_matches": validate_list(form_data.get("scoring_text_match", ""), []),
        "keyword_abilities": validate_list(
            form_data.get("scoring_keyword_abilities", ""), []
        ),
        "keyword_actions": validate_list(
            form_data.get("scoring_keyword_actions", ""), []
        ),
        "ability_words": validate_list(form_data.get("scoring_ability_words", ""), []),
        "type_bonus": {
            "basic": validate_number(
                form_data.get("scoring_type_bonus_basic", 1), 0, 10, 1
            ),
            "sub": validate_number(
                form_data.get("scoring_type_bonus_sub", 2), 0, 10, 2
            ),
            "super": validate_number(
                form_data.get("scoring_type_bonus_super", 3), 0, 10, 3
            ),
        },
        "mana_penalty": {
            "threshold": validate_number(
                form_data.get("mana_penalty_threshold", 4), 0, 20, 4
            ),
            "per_point": validate_number(
                form_data.get("mana_penalty_per_point", 1), 0, 10, 1
            ),
        },
        "rarity_bonus": {
            "common": validate_number(
                form_data.get("rarity_bonus_common", 0), -10, 10, 0
            ),
            "uncommon": validate_number(
                form_data.get("rarity_bonus_uncommon", 1), -10, 10, 1
            ),
            "rare": validate_number(form_data.get("rarity_bonus_rare", 2), -10, 10, 2),
            "mythic": validate_number(
                form_data.get("rarity_bonus_mythic", 3), -10, 10, 3
            ),
        },
        "min_score_to_flag": validate_number(
            form_data.get("min_score_to_flag", 5), 0, 100, 5
        ),
    }

    # Mana base
    validated["mana_base"] = {
        "land_count": validate_number(form_data.get("land_count", 24), 0, 100, 24),
        "special_lands": {
            "count": validate_number(
                form_data.get("special_lands_count", 4), 0, 100, 4
            ),
            "prefer": validate_list(form_data.get("special_lands_prefer", ""), []),
            "avoid": validate_list(form_data.get("special_lands_avoid", ""), []),
        },
        "balance": {
            "adjust_by_mana_symbols": validate_bool(
                form_data.get("adjust_by_mana_symbols", True), True
            )
        },
    }

    # Fallback strategy
    validated["fallback_strategy"] = {
        "fill_priority": validate_list(
            form_data.get("fill_priority", []),
            ["creatures", "removal", "card_draw", "buffs", "utility"],
        ),
        "fill_with_any": validate_bool(form_data.get("fill_with_any", True), True),
        "allow_less_than_target": validate_bool(
            form_data.get("allow_less_than_target", False), False
        ),
    }

    return validated
