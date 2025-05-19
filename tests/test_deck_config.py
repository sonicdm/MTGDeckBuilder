import pytest
from mtg_deck_builder.deck_config.deck_config import DeckConfig
from pathlib import Path
import yaml

def test_load_deck_config_from_yaml():
    yaml_path = Path(__file__).parent / "sample_data" / "yaml_template.yaml"
    config = DeckConfig.from_yaml(str(yaml_path))
    # Deck section
    assert config.deck.name == "My Sample Deck"
    assert config.deck.colors == ["R", "G"]
    assert config.deck.color_match_mode == "subset"
    assert config.deck.size == 60
    assert config.deck.max_card_copies == 4
    assert config.deck.allow_colorless is True
    assert config.deck.legalities == ["standard"]
    assert config.deck.owned_cards_only is True
    assert config.deck.mana_curve["min"] == 1
    assert config.deck.mana_curve["max"] == 8
    assert config.deck.mana_curve["curve_shape"] == "bell"
    assert config.deck.mana_curve["curve_slope"] == "up"
    # Priority cards
    assert len(config.priority_cards) == 2
    assert config.priority_cards[0].name == "Lightning Bolt"
    assert config.priority_cards[0].min_copies == 2
    # Mana base
    assert config.mana_base.land_count == 22
    assert config.mana_base.special_lands.count == 6
    assert "Add {R} or {G}" in config.mana_base.special_lands.prefer
    assert config.mana_base.balance["adjust_by_mana_symbols"] is True
    # Categories
    assert "creatures" in config.categories
    assert config.categories["creatures"].target == 24
    assert "Haste" in config.categories["creatures"].preferred_keywords
    assert "Aggressive" in config.categories["creatures"].priority_text
    # Card constraints
    assert config.card_constraints.rarity_boost.rare == 2
    assert config.card_constraints.rarity_boost.mythic == 1
    assert "Defender" in config.card_constraints.exclude_keywords
    # Fallback strategy
    assert config.fallback_strategy.fill_with_any is True
    assert "creatures" in config.fallback_strategy.fill_priority
    assert config.fallback_strategy.allow_less_than_target is False

def test_as_dict_and_to_yaml_roundtrip():
    yaml_path = Path(__file__).parent / "sample_data" / "yaml_template.yaml"
    config = DeckConfig.from_yaml(str(yaml_path))
    d = config.as_dict()
    yaml_str = config.to_yaml()
    loaded = yaml.safe_load(yaml_str)
    assert d["deck"]["name"] == loaded["deck"]["name"]
    assert d["categories"].keys() == loaded["categories"].keys()

def test_ignore_deprecated_fields():
    # The loader should ignore prefer_cards_with_text and avoid_cards_with_text if present
    yaml_path = Path(__file__).parent / "sample_data" / "yaml_template.yaml"
    with open(yaml_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    # Remove deprecated fields if present
    data["card_constraints"].pop("prefer_cards_with_text", None)
    data["card_constraints"].pop("avoid_cards_with_text", None)
    config = DeckConfig.parse_obj(data)
    assert hasattr(config.card_constraints, "exclude_keywords")
    assert not hasattr(config.card_constraints, "prefer_cards_with_text")
    assert not hasattr(config.card_constraints, "avoid_cards_with_text")
