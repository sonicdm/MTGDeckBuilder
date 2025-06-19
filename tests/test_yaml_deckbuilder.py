import pytest
import logging
from unittest.mock import MagicMock, patch
from mtg_deck_builder.yaml_builder import yaml_deckbuilder
from mtg_deck_builder.yaml_builder.helpers import (
    _select_priority_cards,
    _select_special_lands,
    _distribute_basic_lands,
    _fill_categories,
    _fill_with_any,
    _prune_lowest_scoring,
    score_card,
    generate_target_curve
)
from mtg_deck_builder.deck_config.deck_config import DeckConfig, DeckMeta
from tests.fixtures import DummyCard, DummyInventoryRepo
import os

# Mapping of test names to sample YAML file paths
SAMPLE_YAML_PATHS = {
    "test_schema_validation_missing_fields": "tests/sample_data/sample_deck_configs/test_missing_fields.yaml",
    "test_tag_exclusion": "tests/sample_data/sample_deck_configs/test_tag_exclude.yaml",
    "test_prefer_exclude_conflict": "tests/sample_data/sample_deck_configs/test_prefer_and_exclude.yaml",
    "test_ramp_curve_interaction": "tests/sample_data/sample_deck_configs/test_ramp_curve.yaml",
    "test_budget_constraints": "tests/sample_data/sample_deck_configs/test_budget_low.yaml",
}

# List of main sample deck YAMLs to test
MAIN_SAMPLE_YAMLS = [
    "tests/sample_data/sample_deck_configs/cobra-kai.yaml",
    "tests/sample_data/sample_deck_configs/test_control_uw.yaml",
    "tests/sample_data/sample_deck_configs/black_white_midrange.yaml",
    "tests/sample_data/sample_deck_configs/blue_white_control.yaml",
    "tests/sample_data/sample_deck_configs/green_ramp_modern.yaml",
    "tests/sample_data/sample_deck_configs/mono_red_burn.yaml",
    "tests/sample_data/sample_deck_configs/test-aggro-red.yaml",
]

@pytest.fixture
def minimal_deck_config_fixture():
    return DeckConfig(
        deck=DeckMeta(name="Test Deck", colors=["R"], size=3, max_card_copies=4, legalities=["modern"], owned_cards_only=False),
        categories={},
        priority_cards=[],
        mana_base={"land_count": 1},
        card_constraints=None,
        scoring_rules=None,
        fallback_strategy=None,
    )

# Helper for test_yaml_deckbuilder.py tests (Red Deck)
def setup_mock_repos_for_r_deck(mock_card_repo, mock_inventory_repo, test_specific_cards=None):
    test_specific_cards = test_specific_cards or []

    # Define all 5 basic lands, REMOVING type kwarg
    plains = DummyCard("Plains", text="Basic Land - Plains", rarity="common")
    island = DummyCard("Island", text="Basic Land - Island", rarity="common")
    swamp = DummyCard("Swamp", text="Basic Land - Swamp", rarity="common")
    mountain = DummyCard("Mountain", text="Basic Land - Mountain", rarity="common", colors=['R']) # R deck
    forest = DummyCard("Forest", text="Basic Land - Forest", rarity="common")

    basic_lands_for_general_pool = [mountain]
    all_available_cards = test_specific_cards + basic_lands_for_general_pool

    def find_by_name_side_effect(name_arg):
        if name_arg == "Plains": return plains
        if name_arg == "Island": return island
        if name_arg == "Swamp": return swamp
        if name_arg == "Mountain": return mountain
        if name_arg == "Forest": return forest
        return next((c for c in test_specific_cards if c.name == name_arg), None)

    mock_card_repo.filter_cards.return_value = mock_card_repo
    mock_card_repo.get_all_cards.return_value = all_available_cards
    mock_card_repo.__iter__.return_value = iter(all_available_cards)
    mock_card_repo.find_by_name.side_effect = find_by_name_side_effect

    # Inventory mock (less critical here as owned_cards_only=False, but good for consistency)
    if mock_inventory_repo:
        def inventory_side_effect(card_name_arg):
            if card_name_arg == "Mountain":
                return (100, True) # Basic land for the deck is available
            # For other basic lands, not strictly needed by R deck but can be (100,True)
            if card_name_arg in ["Plains", "Island", "Swamp", "Forest"]:
                return (100, True)

            card_in_test_specific = next((c for c in test_specific_cards if c.name == card_name_arg), None)
            if card_in_test_specific:
                return (card_in_test_specific.owned_qty, False)
            return (1, False) # Default for other cards if queried
        mock_inventory_repo.get_inventory_for_card.side_effect = inventory_side_effect


def test_build_deck_from_config_basic():
    """Test basic deck building from config."""
    mock_repo = MagicMock()
    mock_inventory_repo = MagicMock()

    # Create test cards
    test_cards = [
        DummyCard("Card1", colors=["R"], owned_qty=4),
        DummyCard("Card2", colors=["R"], owned_qty=4),
        DummyCard("Card3", colors=["R"], owned_qty=4)
    ]
    mock_repo.get_all_cards.return_value = test_cards

    config = DeckConfig(
        deck=DeckMeta(
            name="Test Deck",
            colors=["R"],
            size=60,
            max_card_copies=4,
            legalities=["modern"]
        )
    )

    deck = yaml_deckbuilder.build_deck_from_config(
        config,
        mock_repo,
        mock_inventory_repo
    )

    assert deck is not None
    assert len(deck.cards) == 3
    assert all(card.name in ["Card1", "Card2", "Card3"] for card in deck.cards.values())


def test_build_deck_from_config_with_callbacks():
    """Test deck building with callbacks."""
    mock_repo = MagicMock()
    mock_inventory_repo = MagicMock()

    # Create test cards
    test_cards = [
        DummyCard("Bolt", colors=["R"], owned_qty=4),
        DummyCard("Card2", colors=["R"], owned_qty=4)
    ]
    mock_repo.get_all_cards.return_value = test_cards

    config = DeckConfig(
        deck=DeckMeta(
            name="Test Deck",
            colors=["R"],
            size=60,
            max_card_copies=4,
            legalities=["modern"]
        ),
        priority_cards=[{"name": "Bolt", "min_copies": 4}]
    )

    callbacks = {
        "on_priority_cards_selected": lambda cards: None,
        "on_categories_filled": lambda cards: None,
        "on_deck_complete": lambda deck: None
    }

    deck = yaml_deckbuilder.build_deck_from_config(
        config,
        mock_repo,
        mock_inventory_repo,
        callbacks=callbacks
    )

    assert deck is not None
    assert "Bolt" in deck.cards


def test_build_deck_from_config_callback_error(minimal_deck_config_fixture, caplog):
    mock_card_repo = MagicMock()
    mock_inventory_repo = MagicMock()

    # Corrected: DummyCard takes name as first positional argument
    error_mock_cards = [DummyCard("Bolt", colors=["R"])]
    setup_mock_repos_for_r_deck(mock_card_repo, mock_inventory_repo, error_mock_cards)

    def bad_cb(**kwargs):
        raise ValueError("fail")

    with caplog.at_level(logging.WARNING):
        yaml_deckbuilder.build_deck_from_config(minimal_deck_config_fixture, mock_card_repo, mock_inventory_repo, callbacks={"after_priority_card_select": bad_cb})
    assert any("Callback 'after_priority_card_select' raised an error" in r.getMessage() for r in caplog.records)


def test_score_card():
    """Test the card scoring function with various rules."""
    card = DummyCard("Test Card", text="Flying, Haste\nDraw a card\nDestroy target creature")
    scoring_rules = MagicMock()
    scoring_rules.keyword_abilities = {"flying": 2, "haste": 1}
    scoring_rules.keyword_actions = {"draw": 2, "destroy": 3}
    scoring_rules.text_matches = {"draw a card": 2, "destroy target": 3}
    scoring_rules.rarity_bonus = {"rare": 2}
    scoring_rules.mana_penalty = {"threshold": 3, "penalty_per_point": 1}
    
    # Test basic scoring
    score = score_card(card, scoring_rules)
    assert score > 0, "Card should have a positive score"
    
    # Test with deck context
    deck_context = {
        "cards": [],
        "role_counts": {"removal": 0},
        "role_targets": {"removal": 4}
    }
    score_with_context = score_card(card, scoring_rules, deck_context)
    assert score_with_context > score, "Score should be higher with role bonus"

def test_generate_target_curve():
    """Test the mana curve generation function."""
    # Test linear steep curve
    curve = generate_target_curve(1, 4, 20, "linear", "steep")
    assert len(curve) == 4, "Should generate curve for all mana values"
    assert curve[1] > curve[4], "Steep curve should favor lower mana values"
    
    # Test bell curve
    curve = generate_target_curve(1, 5, 20, "bell", "gentle")
    assert curve[3] > curve[1], "Bell curve should peak in the middle"
    assert curve[3] > curve[5], "Bell curve should peak in the middle"

def test_prune_lowest_scoring():
    """Test the card pruning function."""
    mock_repo = MagicMock()
    selected_cards = {
        "Card1": DummyCard("Card1", text="Flying"),
        "Card2": DummyCard("Card2", text="Haste"),
        "Card3": DummyCard("Card3", text="Draw a card")
    }
    
    # Mock scoring rules
    scoring_rules = MagicMock()
    scoring_rules.keyword_abilities = {"flying": 3, "haste": 1}
    scoring_rules.text_matches = {"draw a card": 2}
    scoring_rules.mana_penalty = {"threshold": 3, "penalty_per_point": 1}
    scoring_rules.keyword_actions = {}
    scoring_rules.ability_words = {}
    scoring_rules.type_bonus = {}
    scoring_rules.rarity_bonus = {}
    
    # Mock better candidates
    better_cards = [
        DummyCard("Better1", text="Flying, Haste"),
        DummyCard("Better2", text="Flying, Draw a card")
    ]
    mock_repo.get_all_cards.return_value = better_cards
    
    _prune_lowest_scoring(selected_cards, mock_repo, 60, scoring_rules)
    assert len(selected_cards) == 3, "Should maintain deck size"
    assert any("Better" in card.name for card in selected_cards.values()), "Should include better cards"

def test_fill_categories_with_curve():
    """Test filling categories while respecting mana curve."""
    mock_repo = MagicMock()
    selected_cards = {}

    # Create test cards with various CMCs
    test_cards = [
        DummyCard("OneDrop", converted_mana_cost=1, type="Creature"),
        DummyCard("TwoDrop", converted_mana_cost=2, type="Creature"),
        DummyCard("ThreeDrop", converted_mana_cost=3, type="Creature")
    ]
    mock_repo.get_all_cards.return_value = test_cards

    categories = {
        "creatures": {
            "target": 12,
            "priority_text": ["creature"]
        }
    }

    _fill_categories_with_curve(
        mock_repo,
        selected_cards,
        categories,
        mana_min=1,
        mana_max=3,
        max_copies=4
    )

    assert len(selected_cards) > 0
    assert all(card.converted_mana_cost >= 1 and card.converted_mana_cost <= 3 
              for card in selected_cards.values())

def test_fill_with_any_with_pruning():
    """Test fill_with_any with pruning of low-scoring cards."""
    mock_repo = MagicMock()
    selected_cards = {}

    # Create test cards with varying scores
    test_cards = [
        DummyCard("GoodCard", text="Flying, Draw a card", converted_mana_cost=2),
        DummyCard("BadCard", text="Defender", converted_mana_cost=2),
        DummyCard("WorseCard", text="Defender, Pacifist", converted_mana_cost=2)
    ]
    mock_repo.get_all_cards.return_value = test_cards

    # Mock scoring rules
    scoring_rules = MagicMock()
    scoring_rules.keyword_abilities = {"flying": 2}
    scoring_rules.text_matches = {"draw a card": 2}
    scoring_rules.min_score_to_flag = 3
    scoring_rules.mana_penalty = {"threshold": 3, "penalty_per_point": 1}
    scoring_rules.keyword_actions = {}
    scoring_rules.ability_words = {}
    scoring_rules.type_bonus = {}
    scoring_rules.rarity_bonus = {}

    _fill_with_any(
        mock_repo,
        selected_cards,
        deck_size=60,
        mana_min=1,
        mana_max=4,
        max_copies=4,
        scoring_rules=scoring_rules
    )

    assert len(selected_cards) > 0
    assert "GoodCard" in selected_cards
    assert "BadCard" not in selected_cards
    assert "WorseCard" not in selected_cards

def test_build_deck_with_theme():
    """Test building a deck with a theme."""
    mock_repo = MagicMock()
    mock_inventory_repo = MagicMock()

    # Create test cards
    test_cards = [
        DummyCard("ThemeCard1", text="Flying, Draw a card", colors=["U"]),
        DummyCard("ThemeCard2", text="Flying, Scry", colors=["U"]),
        DummyCard("NonThemeCard", text="Defender", colors=["U"])
    ]
    mock_repo.get_all_cards.return_value = test_cards

    config = DeckConfig(
        deck=DeckMeta(
            name="Theme Test",
            colors=["U"],
            size=60,
            max_card_copies=4,
            legalities=["modern"]
        ),
        theme_keywords=["flying", "draw"]
    )

    deck = yaml_deckbuilder.build_deck_from_config(
        config,
        mock_repo,
        mock_inventory_repo
    )

    assert deck is not None
    assert "ThemeCard1" in deck.cards
    assert "ThemeCard2" in deck.cards

def test_build_deck_with_curve():
    """Test building a deck with mana curve constraints."""
    mock_repo = MagicMock()
    mock_inventory_repo = MagicMock()

    # Create test cards with various CMCs, enough to fill the deck
    test_cards = [
        DummyCard(f"OneDrop{i}", converted_mana_cost=1) for i in range(20)
    ] + [
        DummyCard(f"TwoDrop{i}", converted_mana_cost=2) for i in range(20)
    ] + [
        DummyCard(f"ThreeDrop{i}", converted_mana_cost=3) for i in range(20)
    ]
    mock_repo.get_all_cards.return_value = test_cards

    config = DeckConfig(
        deck=DeckMeta(
            name="Curve Test",
            colors=["R"],
            size=60,
            max_card_copies=4,
            legalities=["modern"]
        ),
        mana_curve={
            "min": 1,
            "max": 3,
            "shape": "linear",
            "slope": "up"
        }
    )

    deck = yaml_deckbuilder.build_deck_from_config(
        config,
        mock_repo,
        mock_inventory_repo
    )

    assert deck is not None
    curve = deck.mana_curve()
    assert len(curve) > 0
    assert all(cmc >= 1 and cmc <= 3 for cmc in curve.keys())

def test_schema_validation():
    """Test YAML schema validation."""
    # Test missing required fields
    with pytest.raises(ValueError):
        yaml_deckbuilder.build_deck_from_yaml(
            SAMPLE_YAML_PATHS["test_schema_validation_missing_fields"],
            MagicMock(),
            MagicMock()
        )

    # Test invalid field types
    with pytest.raises(ValueError):
        config = DeckConfig(
            deck=DeckMeta(
                name="Invalid Test",
                colors="R",  # Should be a list
                size=60,
                max_card_copies=4,
                legalities=["modern"]
            )
        )
        yaml_deckbuilder.build_deck_from_config(
            config,
            MagicMock(),
            MagicMock()
        )

def test_tag_exclusion():
    """Test tag and keyword exclusion logic."""
    mock_repo = MagicMock()
    mock_inventory_repo = MagicMock()
    
    # Create test cards with various tags
    test_cards = [
        DummyCard("Aggro1", text="Haste, First Strike"),
        DummyCard("Defender1", text="Defender, Lifelink"),
        DummyCard("Pacifist1", text="Defender, Pacifist"),
        DummyCard("Healing1", text="Gain life, Healing")
    ]
    mock_repo.get_all_cards.return_value = test_cards
    
    deck = yaml_deckbuilder.build_deck_from_yaml(
        SAMPLE_YAML_PATHS["test_tag_exclusion"],
        mock_repo,
        mock_inventory_repo
    )
    
    assert deck is not None
    assert all("Defender" not in card.name for card in deck.cards.values())
    assert all("Pacifist" not in card.name for card in deck.cards.values())
    assert all("Healing" not in card.name for card in deck.cards.values())

def test_prefer_exclude_conflict():
    """Test that exclude rules take precedence over prefer rules."""
    mock_repo = MagicMock()
    mock_inventory_repo = MagicMock()
    
    # Create test cards that match both prefer and exclude
    test_cards = [
        DummyCard("FastDefender", text="Haste, Defender"),
        DummyCard("AggroPacifist", text="First Strike, Pacifist"),
        DummyCard("DirectHealing", text="Instant, Healing")
    ]
    mock_repo.get_all_cards.return_value = test_cards
    
    deck = yaml_deckbuilder.build_deck_from_yaml(
        SAMPLE_YAML_PATHS["test_prefer_exclude_conflict"],
        mock_repo,
        mock_inventory_repo
    )
    
    assert deck is not None
    assert all("Defender" not in card.name for card in deck.cards.values())
    assert all("Pacifist" not in card.name for card in deck.cards.values())
    assert all("Healing" not in card.name for card in deck.cards.values())

def test_ramp_curve_interaction():
    """Test interaction between ramp spells and mana curve."""
    mock_repo = MagicMock()
    mock_inventory_repo = MagicMock()

    # Create test cards with various CMCs, enough to fill the deck
    test_cards = [
        DummyCard(f"Ramp1_{i}", text="Add {G}", converted_mana_cost=1) for i in range(10)
    ] + [
        DummyCard(f"Ramp2_{i}", text="Search your library for a land", converted_mana_cost=2) for i in range(10)
    ] + [
        DummyCard(f"Threat3_{i}", text="Trample", converted_mana_cost=3) for i in range(10)
    ] + [
        DummyCard(f"Threat4_{i}", text="Hexproof", converted_mana_cost=4) for i in range(10)
    ]
    mock_repo.get_all_cards.return_value = test_cards

    deck = yaml_deckbuilder.build_deck_from_yaml(
        SAMPLE_YAML_PATHS["test_ramp_curve_interaction"],
        mock_repo,
        mock_inventory_repo
    )

    assert deck is not None
    curve = deck.mana_curve()
    assert len(curve) > 0
    assert all(cmc >= 1 and cmc <= 4 for cmc in curve.keys())

def test_budget_constraints():
    """Test budget constraints on card selection."""
    mock_repo = MagicMock()
    mock_inventory_repo = MagicMock()

    # Create test cards with various rarities
    test_cards = [
        DummyCard("Common1", rarity="common", type="Creature"),
        DummyCard("Uncommon1", rarity="uncommon", type="Creature"),
        DummyCard("Rare1", rarity="rare", type="Creature"),
        DummyCard("Mythic1", rarity="mythic", type="Creature"),
        DummyCard("Mountain", type="Basic Land")
    ]
    mock_repo.get_all_cards.return_value = test_cards

    deck = yaml_deckbuilder.build_deck_from_yaml(
        SAMPLE_YAML_PATHS["test_budget_constraints"],
        mock_repo,
        mock_inventory_repo
    )

    assert deck is not None
    # Only check rarity for non-land cards
    non_land_cards = [card for card in deck.cards.values() if not (hasattr(card, 'is_basic_land') and card.is_basic_land()) and not (hasattr(card, 'type') and 'land' in card.type.lower())]
    assert all(card.rarity in ["common", "uncommon"] for card in non_land_cards)

def test_priority_card_truncation():
    """Test that priority cards are truncated when exceeding max copies."""
    mock_repo = MagicMock()
    mock_inventory_repo = MagicMock()

    # Create test cards
    test_cards = [
        DummyCard("Card1", owned_qty=4),
        DummyCard("Card2", owned_qty=4),
        DummyCard("Card3", owned_qty=4)
    ]
    mock_repo.get_all_cards.return_value = test_cards
    def find_by_name_side_effect(name):
        for c in test_cards:
            if c.name == name:
                return c
        return None
    mock_repo.find_by_name.side_effect = find_by_name_side_effect

    config = DeckConfig(
        deck=DeckMeta(
            name="Priority Test",
            colors=["R"],
            size=60,
            max_card_copies=4,
            legalities=["modern"]
        ),
        priority_cards=[
            {"name": "Card1", "min_copies": 5},  # Exceeds max_copies
            {"name": "Card2", "min_copies": 4},
            {"name": "Card3", "min_copies": 4}
        ]
    )

    deck = yaml_deckbuilder.build_deck_from_config(
        config,
        mock_repo,
        mock_inventory_repo
    )

    assert deck is not None
    assert deck.cards["Card1"].owned_qty == 4  # Should be truncated to max_copies
    assert deck.cards["Card2"].owned_qty == 4
    assert deck.cards["Card3"].owned_qty == 4

def test_fill_with_any_threshold():
    """Test that _fill_with_any respects minimum score threshold."""
    mock_repo = MagicMock()
    selected_cards = {}

    # Create test cards with varying scores
    test_cards = [
        DummyCard("GoodCard", text="Flying, Draw a card", converted_mana_cost=2),
        DummyCard("BadCard", text="Defender", converted_mana_cost=2),
        DummyCard("WorseCard", text="Defender, Pacifist", converted_mana_cost=2)
    ]
    mock_repo.get_all_cards.return_value = test_cards

    # Mock scoring rules with high threshold
    scoring_rules = MagicMock()
    scoring_rules.keyword_abilities = {"flying": 2}
    scoring_rules.text_matches = {"draw a card": 2}
    scoring_rules.min_score_to_flag = 4
    scoring_rules.mana_penalty = {"threshold": 3, "penalty_per_point": 1}
    scoring_rules.keyword_actions = {}
    scoring_rules.ability_words = {}
    scoring_rules.type_bonus = {}
    scoring_rules.rarity_bonus = {}

    _fill_with_any(
        mock_repo,
        selected_cards,
        deck_size=60,
        mana_min=1,
        mana_max=4,
        max_copies=4,
        scoring_rules=scoring_rules
    )

    assert len(selected_cards) > 0
    assert "GoodCard" in selected_cards
    assert "BadCard" not in selected_cards
    assert "WorseCard" not in selected_cards

def test_sample_hand_validity():
    """Test that sample hands are valid and representative."""
    mock_repo = MagicMock()
    mock_inventory_repo = MagicMock()

    # Create test cards, enough to fill the deck
    test_cards = [
        DummyCard(f"OneDrop{i}", converted_mana_cost=1, owned_qty=4) for i in range(5)
    ] + [
        DummyCard(f"TwoDrop{i}", converted_mana_cost=2, owned_qty=4) for i in range(5)
    ] + [
        DummyCard(f"ThreeDrop{i}", converted_mana_cost=3, owned_qty=4) for i in range(5)
    ]
    mock_repo.get_all_cards.return_value = test_cards

    config = DeckConfig(
        deck=DeckMeta(
            name="Sample Hand Test",
            colors=["R"],
            size=60,
            max_card_copies=4,
            legalities=["modern"]
        ),
        categories={
            "creatures": {
                "target": 20,
                "priority_text": ["creature"]
            }
        }
    )

    deck = yaml_deckbuilder.build_deck_from_config(
        config,
        mock_repo,
        mock_inventory_repo
    )

    # Test multiple sample hands
    for _ in range(10):
        hand = deck.sample_hand(7)
        assert len(hand) == 7
        assert all(card.converted_mana_cost >= 1 and card.converted_mana_cost <= 3 
                  for card in hand)

@pytest.mark.parametrize("yaml_path", MAIN_SAMPLE_YAMLS)
def test_sample_deck_configs_smoke(yaml_path, create_dummy_db):
    """Test that each main sample YAML config can build a deck without error using full database integration."""
    session = create_dummy_db
    # Use the real session for the smoke test
    deck = yaml_deckbuilder.build_deck_from_yaml(yaml_path, session, None)
    assert deck is not None, f"Deck should be built for {os.path.basename(yaml_path)}"
    assert deck.size() > 0, f"Deck should not be empty for {os.path.basename(yaml_path)}"
    # Optionally, check the deck size matches the config if possible
    if hasattr(deck, 'config') and deck.config and hasattr(deck.config, 'deck') and hasattr(deck.config.deck, 'size'):
        assert deck.size() == deck.config.deck.size, f"Deck size mismatch for {os.path.basename(yaml_path)}"

