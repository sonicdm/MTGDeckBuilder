import pytest
import gradio as gr
from unittest.mock import MagicMock
from mtg_deck_builder.deck_config.deck_config import (
    DeckConfig,
    DeckMeta,
    CategoryDefinition,
    CardConstraintMeta,
    PriorityCardEntry,
    ManaBaseMeta,
    SpecialLandsMeta,
    FallbackStrategyMeta,
)
from mtg_deckbuilder_ui.ui import config_sync
from mtg_deckbuilder_ui.logic.deckbuilder_func import build_deck
import json


def make_sample_deckconfig():
    return DeckConfig(
        deck=DeckMeta(
            name="Test Deck",
            colors=["B", "G"],
            size=60,
            max_card_copies=4,
            legalities=["standard", "modern"],
            allow_colorless=True,
            owned_cards_only=False,
            color_match_mode="subset",
            mana_curve={"min": 1, "max": 8, "curve_shape": "normal", "curve_slope": 1},
        ),
        categories={
            "creatures": CategoryDefinition(
                target=20, preferred_keywords=["elf"], priority_text=["flying"]
            ),
            "removal": CategoryDefinition(target=8, priority_text=["destroy"]),
        },
        card_constraints=CardConstraintMeta(
            exclude_keywords=["defender"],
            rarity_boost={"common": 0, "uncommon": 0, "rare": 0, "mythic": 0},
        ),
        priority_cards=[PriorityCardEntry(name="Llanowar Elves", min_copies=4)],
        mana_base=ManaBaseMeta(
            land_count=24,
            special_lands=SpecialLandsMeta(
                count=2, prefer=["Overgrown Tomb"], avoid=["Temple of Malady"]
            ),
            balance={"adjust_by_mana_symbols": False},
        ),
        fallback_strategy=FallbackStrategyMeta(
            fill_with_any=False,
            fill_priority=["creatures", "removal"],
            allow_less_than_target=True,
        ),
        scoring_rules={
            "text_matches": {"flying": 2},
            "keyword_abilities": {"haste": 1},
            "keyword_actions": {"scry": 1},
            "ability_words": {"battalion": 1},
            "type_bonus": {"basic": {}, "sub": {}, "super": {}},
            "rarity_bonus": {"common": 0, "uncommon": 0, "rare": 0, "mythic": 0},
            "mana_penalty": {"threshold": 5, "penalty_per_point": 1},
            "min_score_to_flag": 5,
        },
    )


def make_mock_ui_map():
    # Each value is a MagicMock with a .value attribute
    keys = [
        "deck_name",
        "deck_colors",
        "deck_size",
        "max_card_copies",
        "allow_colorless",
        "legalities",
        "owned_cards_only",
        "mana_curve_min",
        "mana_curve_max",
        "creature_target",
        "creature_keywords",
        "creature_priority_text",
        "removal_target",
        "removal_priority_text",
        "avoid_cards_with_text",
        "priority_cards",
        "land_count",
        "special_lands_count",
        "special_lands_prefer",
        "special_lands_avoid",
        "adjust_by_mana_symbols",
        "fill_with_any",
        "priority_text",
        "rarity_bonus",
        "mana_penalty",
        "min_score_to_flag",
    ]
    ui_map = {}
    for k in keys:
        mock = MagicMock()
        mock.value = None
        ui_map[k] = mock
    # Fill with some values for extract_config_from_ui test
    ui_map["deck_name"].value = "Test Deck"
    ui_map["deck_colors"].value = ["⚫ Black (B)", "🟢 Green (G)"]
    ui_map["deck_size"].value = 60
    ui_map["max_card_copies"].value = 4
    ui_map["allow_colorless"].value = True
    ui_map["legalities"].value = ["standard"]
    ui_map["owned_cards_only"].value = False
    ui_map["mana_curve_min"].value = None
    ui_map["mana_curve_max"].value = None
    ui_map["creature_target"].value = 20
    ui_map["creature_keywords"].value = ["elf"]
    ui_map["creature_priority_text"].value = ["flying"]
    ui_map["removal_target"].value = 8
    ui_map["removal_priority_text"].value = ["destroy"]
    ui_map["avoid_cards_with_text"].value = ["lose the game"]
    ui_map["priority_cards"].value = [["Llanowar Elves", 4]]
    ui_map["land_count"].value = 24
    ui_map["special_lands_count"].value = 2
    ui_map["special_lands_prefer"].value = ["Overgrown Tomb"]
    ui_map["special_lands_avoid"].value = ["Temple of Malady"]
    ui_map["adjust_by_mana_symbols"].value = False
    ui_map["fill_with_any"].value = False
    ui_map["priority_text"].value = {}
    ui_map["rarity_bonus"].value = {}
    ui_map["mana_penalty"].value = {}
    ui_map["min_score_to_flag"].value = None
    return ui_map


def make_real_ui_map():
    # Simulate the real UI map with Gradio components
    return {
        "name": gr.Textbox(),
        "colors": gr.Textbox(),  # In UI, this is a string of color labels
        "size": gr.Number(),
        "max_card_copies": gr.Number(),
        "allow_colorless": gr.Checkbox(),
        "legalities": gr.Dropdown(multiselect=True),
        "owned_cards_only": gr.Checkbox(),
        "color_match_mode": gr.Dropdown(),
        "mana_curve_min": gr.Number(),
        "mana_curve_max": gr.Number(),
        "mana_curve_shape": gr.Textbox(),
        "mana_curve_slope": gr.Number(),
        "exclude_keywords": gr.Dropdown(multiselect=True),
        "rarity_boost_common": gr.Number(),
        "rarity_boost_uncommon": gr.Number(),
        "rarity_boost_rare": gr.Number(),
        "rarity_boost_mythic": gr.Number(),
        "creatures_target": gr.Number(),
        "creatures_keywords": gr.Dropdown(multiselect=True),
        "creatures_priority_text": gr.Dropdown(multiselect=True),
        "removal_target": gr.Number(),
        "removal_keywords": gr.Dropdown(multiselect=True),
        "removal_priority_text": gr.Dropdown(multiselect=True),
        "card_draw_target": gr.Number(),
        "card_draw_keywords": gr.Dropdown(multiselect=True),
        "card_draw_priority_text": gr.Dropdown(multiselect=True),
        "buffs_target": gr.Number(),
        "buffs_keywords": gr.Dropdown(multiselect=True),
        "buffs_priority_text": gr.Dropdown(multiselect=True),
        "utility_target": gr.Number(),
        "utility_keywords": gr.Dropdown(multiselect=True),
        "utility_priority_text": gr.Dropdown(multiselect=True),
        "land_count": gr.Number(),
        "special_count": gr.Number(),
        "special_prefer": gr.Dropdown(multiselect=True),
        "special_avoid": gr.Dropdown(multiselect=True),
        "adjust_mana": gr.Checkbox(),
        "fill_with_any": gr.Checkbox(),
        "fill_priority": gr.Textbox(),
        "allow_less_than_target": gr.Checkbox(),
        "rarity_bonus_common": gr.Number(),
        "rarity_bonus_uncommon": gr.Number(),
        "rarity_bonus_rare": gr.Number(),
        "rarity_bonus_mythic": gr.Number(),
        "mana_penalty_threshold": gr.Number(),
        "mana_penalty_per_point": gr.Number(),
        "min_score_to_flag": gr.Number(),
        "scoring_text_match": gr.Code(),
        "scoring_keyword_abilities": gr.Code(),
        "scoring_keyword_actions": gr.Code(),
        "scoring_ability_words": gr.Code(),
        "scoring_type_bonus_basic": gr.Code(),
        "scoring_type_bonus_sub": gr.Code(),
        "scoring_type_bonus_super": gr.Code(),
        "priority_cards_yaml": gr.Code(),
    }


def test_apply_config_to_ui_types():
    cfg = make_sample_deckconfig()
    ui_map = make_real_ui_map()
    updates = config_sync.apply_config_to_ui(cfg, ui_map)
    for key, component in ui_map.items():
        val = updates[key].get("value", None)
        if isinstance(component, (gr.Markdown, gr.Code, gr.Textbox)):
            assert isinstance(val, str), f"{key} should be str, got {type(val)}"
        elif isinstance(component, gr.Dropdown) and getattr(
            component, "multiselect", False
        ):
            assert isinstance(val, list), f"{key} should be list, got {type(val)}"
        elif isinstance(component, gr.Number):
            assert isinstance(
                val, (int, float)
            ), f"{key} should be int/float, got {type(val)}"
        elif isinstance(component, gr.Checkbox):
            assert isinstance(val, bool), f"{key} should be bool, got {type(val)}"
        # Add more checks as needed


def test_extract_config_from_ui_roundtrip():
    cfg = make_sample_deckconfig()
    ui_map = make_real_ui_map()
    # Simulate UI values as if loaded from config
    updates = config_sync.apply_config_to_ui(cfg, ui_map)
    # Assert all updates have a 'value' key
    for key, update in updates.items():
        assert "value" in update, f"Update for {key} missing 'value' key"
    # Now simulate extracting config from UI
    # Fake UI state: each component gets a .value attribute
    fake_ui_state = {}
    for key, component in ui_map.items():
        mock = type("MockComp", (), {})()
        mock.value = updates[key].get("value", None)
        fake_ui_state[key] = mock
    roundtrip_cfg = config_sync.extract_config_from_ui(fake_ui_state)
    # Check some key fields survived roundtrip
    assert roundtrip_cfg.deck.name == cfg.deck.name
    assert set(roundtrip_cfg.deck.colors) == set(cfg.deck.colors)
    assert roundtrip_cfg.deck.size == cfg.deck.size
    assert roundtrip_cfg.priority_cards[0].name == cfg.priority_cards[0].name
    assert roundtrip_cfg.mana_base.land_count == cfg.mana_base.land_count
    assert (
        roundtrip_cfg.mana_base.special_lands.prefer
        == cfg.mana_base.special_lands.prefer
    )
    assert (
        roundtrip_cfg.categories["creatures"].target
        == cfg.categories["creatures"].target
    )


def test_markdown_list_handling():
    cfg = make_sample_deckconfig()
    ui_map = make_real_ui_map()
    # Simulate a markdown list in the config
    cfg.deck.name = "- item1\n- item2"
    updates = config_sync.apply_config_to_ui(cfg, ui_map)
    # Assert that the markdown list is correctly displayed
    assert (
        updates["name"]["value"] == "- item1\n- item2"
    ), "Markdown list not correctly displayed"


def test_empty_list_handling():
    cfg = make_sample_deckconfig()
    ui_map = make_real_ui_map()
    # Simulate an empty list in the config
    cfg.deck.name = ""
    updates = config_sync.apply_config_to_ui(cfg, ui_map)
    # Assert that the empty list is correctly displayed
    assert updates["name"]["value"] == "", "Empty list not correctly displayed"


def test_special_characters_handling():
    cfg = make_sample_deckconfig()
    ui_map = make_real_ui_map()
    # Simulate a list with special characters in the config
    cfg.deck.name = "- item1\n- item2\n- item3\n- item4"
    updates = config_sync.apply_config_to_ui(cfg, ui_map)
    # Assert that the list with special characters is correctly displayed
    assert (
        updates["name"]["value"] == "- item1\n- item2\n- item3\n- item4"
    ), "List with special characters not correctly displayed"


def test_nested_list_handling():
    cfg = make_sample_deckconfig()
    ui_map = make_real_ui_map()
    # Simulate a nested list in the config
    cfg.deck.name = "- item1\n  - nested1\n  - nested2\n- item2"
    updates = config_sync.apply_config_to_ui(cfg, ui_map)
    # Assert that the nested list is correctly displayed
    assert (
        updates["name"]["value"] == "- item1\n  - nested1\n  - nested2\n- item2"
    ), "Nested list not correctly displayed"


def test_component_type_safety():
    cfg = make_sample_deckconfig()
    ui_map = make_real_ui_map()
    # Simulate a markdown list in the config
    cfg.deck.name = "- item1\n- item2"
    updates = config_sync.apply_config_to_ui(cfg, ui_map)
    # Assert that the component type is correctly handled
    assert isinstance(
        updates["name"]["value"], str
    ), "Component type not correctly handled"


def test_deckconfig_ui_extraction_and_roundtrip():
    # Simulate UI arguments (minimal valid deck)
    args = dict(
        name="Test Deck",
        colors=["R"],
        size=60,
        max_card_copies=4,
        allow_colorless=True,
        color_match_mode="subset",
        legalities=["standard"],
        owned_cards_only=True,
        mana_curve_min=1,
        mana_curve_max=7,
        mana_curve_shape="bell",
        mana_curve_slope="flat",
        inventory_select="test_inventory.txt",
        priority_cards_yaml="Lightning Bolt: 4",
        creatures_target=20,
        creatures_keywords=["Haste"],
        creatures_priority_text=["Haste"],
        removal_target=8,
        removal_keywords=["Destroy"],
        removal_priority_text=["Destroy"],
        card_draw_target=4,
        card_draw_keywords=["Draw"],
        card_draw_priority_text=["Draw"],
        buffs_target=2,
        buffs_keywords=["Pump"],
        buffs_priority_text=["Pump"],
        utility_target=2,
        utility_keywords=["Scry"],
        utility_priority_text=["Scry"],
        scoring_text_match="kicker: 2",
        scoring_keyword_abilities="haste: 1",
        scoring_keyword_actions="destroy: 1",
        scoring_ability_words="draw: 1",
        scoring_type_bonus_basic="instant: 1",
        scoring_type_bonus_sub="wizard: 1",
        scoring_type_bonus_super="legendary: 1",
        mana_penalty_threshold=5.0,
        mana_penalty_per_point=0.5,
        rarity_bonus_common=0.1,
        rarity_bonus_uncommon=0.2,
        rarity_bonus_rare=0.3,
        rarity_bonus_mythic=0.4,
        min_score_to_flag=6.0,
        fill_priority="creatures,removal",
        fill_with_any=True,
        allow_less_than_target=False,
        card_table_columns=["Name", "Type", "Qty"],
    )
    # Build DeckConfig via build_deck (should construct DeckConfig internally)
    result = build_deck(**args)
    assert result["status"] == "success"
    # Extract DeckConfig for round-trip test
    deck_obj = result["deck_state"]
    # DeckConfig round-trip (to_json/from_json)
    if hasattr(deck_obj, "config"):
        config = deck_obj.config
        config_json = config.model_dump_json()
        config2 = DeckConfig.model_validate_json(config_json)
        assert config == config2
    # Deck round-trip (to_json/from_json) if supported
    if hasattr(deck_obj, "to_json") and hasattr(deck_obj.__class__, "from_json"):
        deck_json = deck_obj.to_json()
        deck2 = deck_obj.__class__.from_json(deck_json)
        # Compare key fields
        assert deck_obj.name == deck2.name
        assert deck_obj.cards.keys() == deck2.cards.keys()
