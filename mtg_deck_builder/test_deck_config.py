import pytest
from mtg_deck_builder.models.deck_config import DeckConfig

def test_deckconfig_json_roundtrip():
    # Minimal DeckConfig
    config = DeckConfig(
        deck=DeckConfig.Deck(
            name="Test Deck",
            colors=["G"],
            size=60,
            max_card_copies=4,
            allow_colorless=True,
            color_match_mode="subset",
            legalities=["standard"],
            owned_cards_only=True,
            mana_curve={"min": 1, "max": 7, "curve_shape": "bell", "curve_slope": "flat"},
            inventory="test_inventory.txt",
            priority_cards=[],
        ),
        categories={},
        scoring_rules={},
        fallback_strategy={},
    )
    config_json = config.model_dump_json()
    config2 = DeckConfig.model_validate_json(config_json)
    assert config == config2 