import tempfile
import os
from pathlib import Path
import pytest
from mtg_deck_builder.deck_config.deck_config import DeckConfig
from .helpers import get_sample_data_path

yaml_sample = '''
deck:
  name: "My Sample Deck"
  colors: ["R", "G"]
  color_match_mode: "subset"
  size: 60
  max_card_copies: 4
  allow_colorless: true
  legalities: ["standard"]
  mana_curve:
    min: 1
    max: 8
    curve_shape: "bell"
    curve_slope: "up"
  owned_cards_only: true

priority_cards:
  - name: "Lightning Bolt"
    min_copies: 2
  - name: "Monastery Swiftspear"
    min_copies: 4

mana_base:
  land_count: 22
  special_lands:
    count: 6
    prefer:
      - "Add {R} or {G}"
      - "Untapped"
      - "Mana fixing"
      - "Gain life"
    avoid:
      - "Enters tapped unless"
      - "Deals damage to you"
  balance:
    adjust_by_mana_symbols: true

categories:
  creatures:
    target: 24
    preferred_keywords: ["Haste", "Trample", "Menace"]
    priority_text: ["Aggressive", "Attacks each turn", "Deals damage"]
  removal:
    target: 6
    priority_text: ["Destroy", "Exile", "Deal damage", "Fight"]
  card_draw:
    target: 4
    priority_text: ["Draw a card", "Impulse draw"]
  buffs:
    target: 4
    priority_text: ["+X/+0", "Until end of turn", "Give haste", "Pump spell"]
  utility:
    target: 2
    priority_text: ["Treasure", "Scry", "Loot", "Double strike"]

card_constraints:
  rarity_boost:
    common: 0
    uncommon: 0
    rare: 2
    mythic: 1
  exclude_keywords: ["Defender", "Cannot attack"]

scoring_rules:
  priority_text:
    "Aggressive": 2
    "Haste": 2
    /deal[s]? damage/: 3
  rarity_bonus:
    common: 0
    uncommon: 0
    rare: 2
    mythic: 1
  mana_penalty:
    threshold: 5
    penalty_per_point: 1
  min_score_to_flag: 5

fallback_strategy:
  fill_with_any: true
  fill_priority:
    - creatures
    - removal
    - buffs
  allow_less_than_target: false
'''
yaml_file = get_sample_data_path("yaml_template.yaml")

def test_from_yaml_string():
    cfg = DeckConfig.from_yaml(yaml_sample)
    assert cfg.deck.name == "My Sample Deck"
    assert cfg.deck.colors == ["R", "G"]
    assert cfg.deck.size == 60
    assert cfg.categories["creatures"].target == 24
    assert cfg.mana_base.land_count == 22
    assert cfg.fallback_strategy.fill_with_any is True

def test_from_yaml_file():
    cfg = DeckConfig.from_yaml(yaml_file)
    assert cfg.deck.name == "My Sample Deck"
    assert cfg.deck.colors == ["R", "G"]

def test_to_yaml_and_as_dict():
    cfg = DeckConfig.from_yaml(yaml_sample)
    yaml_out = cfg.to_yaml()
    assert isinstance(yaml_out, str)
    dct = cfg.as_dict()
    assert isinstance(dct, dict)
    assert dct["deck"]["name"] == "My Sample Deck"

def test_yaml_round_trip():
    cfg1 = DeckConfig.from_yaml(yaml_sample)
    yaml_out = cfg1.to_yaml()
    cfg2 = DeckConfig.from_yaml(yaml_out)
    assert cfg2.deck.name == cfg1.deck.name
    assert cfg2.deck.colors == cfg1.deck.colors
    assert cfg2.categories["creatures"].target == cfg1.categories["creatures"].target

def test_to_yaml_file(tmp_path):
    cfg = DeckConfig.from_yaml(yaml_sample)
    out_path = tmp_path / "test_output.yaml"
    cfg.to_yaml(out_path)
    assert out_path.exists()
    loaded = DeckConfig.from_yaml(out_path)
    assert loaded.deck.name == cfg.deck.name

def test_inventory_file_field():
    # Test that inventory_file can be set and accessed
    from mtg_deck_builder.deck_config.deck_config import DeckMeta, DeckConfig
    deck_meta = DeckMeta(name="Test", inventory_file="card inventory.txt")
    assert deck_meta.inventory_file == "card inventory.txt"
    config = DeckConfig(deck=deck_meta)
    assert config.deck.inventory_file == "card inventory.txt"

def test_inventory_file_not_in_yaml():
    # Test that inventory_file is not present in YAML output
    from mtg_deck_builder.deck_config.deck_config import DeckMeta, DeckConfig
    deck_meta = DeckMeta(name="Test", inventory_file="card inventory.txt")
    config = DeckConfig(deck=deck_meta)
    yaml_str = config.to_yaml()
    assert "inventory_file" not in yaml_str
    dct = config.as_dict()
    assert "inventory_file" not in dct["deck"]
