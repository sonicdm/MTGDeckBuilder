import pytest
from mtg_deck_builder.models.deck_config import DeckConfig
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
    # --- New/Updated fields and YAML-based scoring rules ---
    scoring = config.scoring_rules
    assert hasattr(scoring, "text_matches")
    assert isinstance(scoring.text_matches, (dict, list))
    assert hasattr(scoring, "keyword_abilities")
    assert isinstance(scoring.keyword_abilities, (dict, list))
    assert hasattr(scoring, "keyword_actions")
    assert isinstance(scoring.keyword_actions, (dict, list))
    assert hasattr(scoring, "ability_words")
    assert isinstance(scoring.ability_words, (dict, list))
    assert hasattr(scoring, "type_bonus")
    assert isinstance(scoring.type_bonus, dict)
    for subkey in ("basic", "sub", "super"):
        val = scoring.type_bonus.get(subkey)
        if val is not None:
            assert isinstance(val, (dict, list))
    assert hasattr(scoring, "rarity_bonus")
    assert "common" in scoring.rarity_bonus
    assert "uncommon" in scoring.rarity_bonus
    assert "rare" in scoring.rarity_bonus
    assert "mythic" in scoring.rarity_bonus
    assert hasattr(scoring, "mana_penalty")
    assert "threshold" in scoring.mana_penalty
    assert "penalty_per_point" in scoring.mana_penalty
    assert hasattr(scoring, "min_score_to_flag")

def test_as_dict_and_to_yaml_roundtrip():
    yaml_path = Path(__file__).parent / "sample_data" / "yaml_test_template.yaml"
    config = DeckConfig.from_yaml(str(yaml_path))
    d = config.model_dump(exclude_none=True)
    yaml_str = config.to_yaml()
    loaded = yaml.safe_load(yaml_str)
    assert loaded == d
    # Remove all assertions on optional fields
    # assert d["deck"]["name"] == loaded["deck"]["name"]
    # assert d["categories"].keys() == loaded["categories"].keys()
    # assert d["scoring_rules"]["text_matches"] == loaded["scoring_rules"]["text_matches"]
    # --- New: Check roundtrip for scoring rules and priority cards ---
    # assert d["scoring_rules"]["text_matches"] == loaded["scoring_rules"]["text_matches"]
    # assert d["scoring_rules"]["keyword_abilities"] == loaded["scoring_rules"]["keyword_abilities"]
    # assert d["scoring_rules"]["keyword_actions"] == loaded["scoring_rules"]["keyword_actions"]
    # assert d["scoring_rules"]["type_bonus"] == loaded["scoring_rules"]["type_bonus"]
    # Optionally, check subkeys inside type_bonus
    # assert d["scoring_rules"]["type_bonus"]["basic_types"] == loaded["scoring_rules"]["type_bonus"]["basic_types"]
    # assert d["scoring_rules"]["type_bonus"]["sub_types"] == loaded["scoring_rules"]["type_bonus"]["sub_types"]
    # assert d["scoring_rules"]["type_bonus"]["super_types"] == loaded["scoring_rules"]["type_bonus"]["super_types"]
    # assert d["scoring_rules"]["rarity_bonus"] == loaded["scoring_rules"]["rarity_bonus"]
    # assert d["scoring_rules"]["mana_penalty"] == loaded["scoring_rules"]["mana_penalty"]
    # assert d["scoring_rules"]["min_score_to_flag"] == loaded["scoring_rules"]["min_score_to_flag"]
    # assert d["scoring_rules"]["priority_text"] == loaded["scoring_rules"]["priority_text"]
    # assert d["fallback_strategy"]["fill_with_any"] == loaded["fallback_strategy"]["fill_with_any"]
    # assert d["fallback_strategy"]["fill_priority"] == loaded["fallback_strategy"]["fill_priority"]
    # assert d["fallback_strategy"]["allow_less_than_target"] == loaded["fallback_strategy"]["allow_less_than_target"]
    assert d["scoring_rules"]["type_bonus"] == loaded["scoring_rules"]["type_bonus"]
    # Optionally, check subkeys inside type_bonus
    for subkey in ("basic", "sub", "super"):
        assert d["scoring_rules"]["type_bonus"].get(subkey) == loaded["scoring_rules"]["type_bonus"].get(subkey)
    assert d["scoring_rules"]["rarity_bonus"] == loaded["scoring_rules"]["rarity_bonus"]
    assert d["scoring_rules"]["mana_penalty"] == loaded["scoring_rules"]["mana_penalty"]
    assert d["scoring_rules"]["min_score_to_flag"] == loaded["scoring_rules"]["min_score_to_flag"]
    assert d["priority_cards"] == loaded["priority_cards"]

def test_deckconfig_json_serialization():
    # Create a minimal DeckConfig
    config = DeckConfig(
        deck=DeckConfig.Deck(
            name="Test Deck",
            colors=["B", "R"],
            size=60,
            max_card_copies=4,
            allow_colorless=True,
            color_match_mode="subset",
            legalities=["standard"],
            owned_cards_only=True,
            mana_curve={
                "min": 1,
                "max": 7,
                "curve_shape": "bell",
                "curve_slope": "up"
            },
            inventory="test_inventory.txt",
            priority_cards=[]
        ),
        categories={
            "creatures": {
                "target": 24,
                "keywords": ["flying", "trample"],
                "priority_text": ["haste", "first strike"]
            },
            "removal": {
                "target": 8,
                "keywords": ["destroy", "exile"],
                "priority_text": ["instant", "sorcery"]
            }
        },
        scoring_rules={
            "text_matches": {},
            "keyword_abilities": {},
            "keyword_actions": {},
            "ability_words": {},
            "type_bonus": {
                "basic": {},
                "sub": {},
                "super": {}
            },
            "rarity_bonus": {
                "common": 0.0,
                "uncommon": 0.0,
                "rare": 0.0,
                "mythic": 0.0
            },
            "mana_penalty": {
                "threshold": 4,
                "penalty_per_point": 0.5
            },
            "min_score_to_flag": 6.0
        },
        fallback_strategy={
            "land_count": 24.0,
            "special_count": 4.0,
            "special_prefer": ["Sulfurous Springs", "Blackcleave Cliffs"],
            "special_avoid": [],
            "adjust_mana": False,
            "fill_with_any": True,
            "fill_priority": "creatures\nremoval",
            "allow_less_than_target": False
        }
    )

    # Test serialization
    config_dict = config.as_dict()
    
    # Verify deck section
    assert config_dict["deck"]["name"] == "Test Deck"
    assert config_dict["deck"]["colors"] == ["B", "R"]
    assert config_dict["deck"]["size"] == 60
    assert config_dict["deck"]["max_card_copies"] == 4
    assert config_dict["deck"]["allow_colorless"] is True
    assert config_dict["deck"]["color_match_mode"] == "subset"
    assert config_dict["deck"]["legalities"] == ["standard"]
    assert config_dict["deck"]["owned_cards_only"] is True
    assert config_dict["deck"]["mana_curve"]["min"] == 1
    assert config_dict["deck"]["mana_curve"]["max"] == 7
    assert config_dict["deck"]["mana_curve"]["curve_shape"] == "bell"
    assert config_dict["deck"]["mana_curve"]["curve_slope"] == "up"
    
    # Verify categories
    assert "creatures" in config_dict["categories"]
    assert "removal" in config_dict["categories"]
    assert config_dict["categories"]["creatures"]["target"] == 24
    assert config_dict["categories"]["removal"]["target"] == 8
    
    # Verify scoring rules
    scoring = config_dict["scoring_rules"]
    assert "text_matches" in scoring
    assert "keyword_abilities" in scoring
    assert "keyword_actions" in scoring
    assert "ability_words" in scoring
    assert "type_bonus" in scoring
    assert "rarity_bonus" in scoring
    assert "mana_penalty" in scoring
    assert "min_score_to_flag" in scoring
    
    # Verify fallback strategy
    fallback = config_dict["fallback_strategy"]
    assert fallback["land_count"] == 24.0
    assert fallback["special_count"] == 4.0
    assert fallback["special_prefer"] == ["Sulfurous Springs", "Blackcleave Cliffs"]
    assert fallback["special_avoid"] == []
    assert fallback["adjust_mana"] is False
    assert fallback["fill_with_any"] is True
    assert fallback["fill_priority"] == "creatures\nremoval"
    assert fallback["allow_less_than_target"] is False
