import pytest
from unittest.mock import MagicMock
from mtg_deck_builder.deck_config.deck_config import DeckConfig, DeckMeta, CategoryDefinition, CardConstraintMeta, KeyCardEntry, ManaBaseMeta, SpecialLandsMeta, FallbackStrategyMeta, KeyCardsMeta
from mtg_deckbuilder_ui.ui import config_sync

def make_sample_deckconfig():
    return DeckConfig(
        deck=DeckMeta(
            name="Test Deck",
            colors=["B", "G"],
            size=60,
            max_card_copies=4,
            legalities=["standard"],
            allow_colorless=True,
            owned_cards_only=False
        ),
        categories={
            "creatures": CategoryDefinition(target=20, preferred_keywords=["elf"], priority_text=["flying"]),
            "removal": CategoryDefinition(target=8, priority_text=["destroy"]),
        },
        card_constraints=CardConstraintMeta(avoid_cards_with_text=["lose the game"]),
        priority_cards=[KeyCardEntry(name="Llanowar Elves", min_copies=4)],
        mana_base=ManaBaseMeta(
            land_count=24,
            special_lands=SpecialLandsMeta(count=2, prefer=["Overgrown Tomb"], avoid=["Temple of Malady"]),
            balance={"adjust_by_mana_symbols": False}
        ),
        fallback_strategy=FallbackStrategyMeta(fill_with_any=False),
        key_cards=KeyCardsMeta(priority_cards=[], priority_text={}),
    )

def make_mock_ui_map():
    # Each value is a MagicMock with a .value attribute
    keys = [
        "deck_name", "deck_colors", "deck_size", "max_card_copies", "allow_colorless", "legalities", "owned_cards_only",
        "mana_curve_min", "mana_curve_max", "creature_target", "creature_keywords", "creature_priority_text",
        "removal_target", "removal_priority_text", "avoid_cards_with_text", "priority_cards", "land_count",
        "special_lands_count", "special_lands_prefer", "special_lands_avoid", "adjust_by_mana_symbols", "fill_with_any",
        "priority_text", "rarity_bonus", "mana_penalty", "min_score_to_flag"
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

def test_apply_config_to_ui_basic():
    cfg = make_sample_deckconfig()
    ui_map = {k: None for k in [
        "deck_name", "deck_colors", "deck_size", "max_card_copies", "allow_colorless", "legalities", "owned_cards_only",
        "creature_target", "creature_keywords", "creature_priority_text", "removal_target", "removal_priority_text",
        "avoid_cards_with_text", "priority_cards", "land_count", "special_lands_count", "special_lands_prefer",
        "special_lands_avoid", "adjust_by_mana_symbols", "fill_with_any"
    ]}
    updates = config_sync.apply_config_to_ui(cfg, ui_map)
    assert updates["deck_name"]["value"] == "Test Deck"
    assert "⚫ Black (B)" in updates["deck_colors"]["value"]
    assert updates["creature_target"]["value"] == 20
    assert updates["priority_cards"]["value"] == [["Llanowar Elves", 4]]
    assert updates["land_count"]["value"] == 24
    assert updates["special_lands_prefer"]["value"] == ["Overgrown Tomb"]
    assert updates["adjust_by_mana_symbols"]["value"] is False
    assert updates["fill_with_any"]["value"] is False

def test_extract_config_from_ui_basic():
    ui_map = make_mock_ui_map()
    config_obj = config_sync.extract_config_from_ui(ui_map)
    assert config_obj.deck.name == "Test Deck"
    assert config_obj.deck.colors == ["B", "G"]
    assert config_obj.categories["creatures"].target == 20
    assert config_obj.priority_cards[0].name == "Llanowar Elves"
    assert config_obj.mana_base.special_lands.prefer == ["Overgrown Tomb"]
    assert config_obj.mana_base.special_lands.avoid == ["Temple of Malady"]
    assert config_obj.mana_base.land_count == 24
    assert config_obj.mana_base.special_lands.count == 2
    assert config_obj.card_constraints.avoid_cards_with_text == ["lose the game"]
