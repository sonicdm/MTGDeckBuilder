import pytest
from mtg_deck_builder.deck_config.deck_config import DeckConfig
from pathlib import Path
import yaml

def test_load_deck_config_from_yaml():
    yaml_path = Path(__file__).parent / "sample_data" / "yaml_test_template.yaml"
    config = DeckConfig.from_yaml(str(yaml_path))
    # Deck section
    assert config.deck.name == "Test Deck - Full Feature Coverage"
    assert config.deck.colors == ["B", "R"]
    assert config.deck.color_match_mode == "subset"
    assert config.deck.size == 60
    assert config.deck.max_card_copies == 4
    assert config.deck.allow_colorless is True
    assert config.deck.legalities == ["standard"]
    assert config.deck.owned_cards_only is True
    assert config.deck.mana_curve["min"] == 1
    assert config.deck.mana_curve["max"] == 7
    assert config.deck.mana_curve["curve_shape"] == "bell"
    assert config.deck.mana_curve["curve_slope"] == "up"
    # Priority cards
    assert len(config.priority_cards) == 3
    assert config.priority_cards[0].name == "Cut Down"
    assert config.priority_cards[0].min_copies == 4
    assert config.priority_cards[1].name == "Go for the Throat"
    assert config.priority_cards[1].min_copies == 2
    assert config.priority_cards[2].name == "Lightning Bolt"
    assert config.priority_cards[2].min_copies == 4
    # Mana base
    assert config.mana_base.land_count == 22
    assert config.mana_base.special_lands.count == 4
    assert "Add {B} or {R}" in config.mana_base.special_lands.prefer
    assert config.mana_base.balance["adjust_by_mana_symbols"] is True
    # Categories
    assert "creatures" in config.categories
    assert config.categories["creatures"].target == 24
    assert "Haste" in config.categories["creatures"].preferred_keywords
    assert "Aggressive" in config.categories["creatures"].priority_text
    # Card constraints
    assert config.card_constraints.rarity_boost.rare == 2
    assert config.card_constraints.rarity_boost.mythic == 3
    assert "Defender" in config.card_constraints.exclude_keywords
    # Fallback strategy
    assert config.fallback_strategy.fill_with_any is True
    assert "creatures" in config.fallback_strategy.fill_priority
    assert config.fallback_strategy.allow_less_than_target is False

def test_as_dict_and_to_yaml_roundtrip():
    yaml_path = Path(__file__).parent / "sample_data" / "yaml_test_template.yaml"
    config = DeckConfig.from_yaml(str(yaml_path))
    d = config.as_dict()
    yaml_str = config.to_yaml()
    loaded = yaml.safe_load(yaml_str)
    assert d["deck"]["name"] == loaded["deck"]["name"]
    assert d["categories"].keys() == loaded["categories"].keys()

