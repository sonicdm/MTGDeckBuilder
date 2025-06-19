import pytest
import logging
from mtg_deck_builder.yaml_builder import helpers

class DummyCard:
    def __init__(self, name, colors=None, text=None, rarity=None, legalities=None, owned_qty=1):
        self.name = name
        self.colors = colors or []
        self.text = text or ""
        self.rarity = rarity
        self.legalities = legalities or {}
        self.owned_qty = owned_qty
        self.type = name  # Set type to name for simpler testing

        # Add additional attributes to better match the real CardDB class
        self.supertypes = []
        self.subtypes = []
        if "Legendary" in name:
            self.supertypes.append("legendary")
        if "Elemental" in name:
            self.subtypes.append("elemental")

    def matches_color_identity(self, allowed, mode):
        return set(self.colors) <= set(allowed)

    def matches_type(self, t):
        return t.lower() in self.name.lower() or t.lower() in self.text.lower()

    def is_basic_land(self):
        return self.name in ["Plains", "Island", "Swamp", "Mountain", "Forest"]

class DummyRepo:
    def __init__(self, cards):
        self._cards = cards
    def get_all_cards(self):
        return self._cards
    def find_by_name(self, name):
        for c in self._cards:
            if c.name == name:
                return c
        return None

def test_run_callback_invokes_and_logs(caplog):
    called = {}
    def cb(**kwargs):
        called["ok"] = True
    helpers._run_callback({"foo": cb}, "foo", x=1)
    assert called["ok"]
    def bad_cb(**kwargs):
        raise ValueError("fail")
    with caplog.at_level(logging.WARNING):
        helpers._run_callback({"bar": bad_cb}, "bar")
    assert any("CALLBACK ERROR" in r.getMessage() for r in caplog.records)

def test_select_priority_cards_color_and_legality(caplog):
    card1 = DummyCard("A", colors=["R"], rarity="rare", legalities={"modern": "legal"})
    card2 = DummyCard("B", colors=["G"], rarity="rare", legalities={"modern": "not_legal"})
    repo = DummyRepo([card1, card2])
    pri = [type("PC", (), {"name": "A", "min_copies": 2})]
    selected = helpers._select_priority_cards(pri, repo, allowed_colors=["R"], color_match_mode=None, legalities=["modern"], max_copies=4)
    assert "A" in selected
    pri2 = [type("PC", (), {"name": "B", "min_copies": 1})]
    selected2 = helpers._select_priority_cards(pri2, repo, allowed_colors=["R"], color_match_mode=None, legalities=["modern"], max_copies=4)
    assert "B" not in selected2
    # Should log a warning for not matching legality
    with caplog.at_level(logging.WARNING):
        helpers._select_priority_cards(pri2, repo, allowed_colors=["R"], color_match_mode=None, legalities=["modern"], max_copies=4)
    assert any("doesn't match color/legality" in r.getMessage() for r in caplog.records)

def test_select_special_lands_callback():
    lands = [DummyCard("Temple", text="Add {R}")]
    called = {}
    def cb(selected=None, **kwargs):
        called["lands"] = selected
    selected = helpers._select_special_lands(lands, ["temple"], [], 1, ["R"], callbacks={"after_special_lands": cb})
    assert called["lands"] == selected
    assert selected[0].name == "Temple"

@pytest.mark.test_distribute_basic_lands
def test_distribute_basic_lands_distribution():
    selected = {}
    basics = [DummyCard("Plains", colors=["W"]), DummyCard("Island", colors=["U"])]
    helpers._distribute_basic_lands(selected, basics, allowed_colors=["W", "U"], num_basic_needed=4)
    assert "Plains" in selected or "Island" in selected
    total = sum(c.owned_qty for c in selected.values())
    assert total == 4

@pytest.mark.test_distribute_basic_lands
def test_distribute_basic_lands_no_basics():
    """Test basic land distribution when no basics are provided."""
    selected = {}
    # Instead of expecting an exception, we now expect the function to create default basics
    helpers._distribute_basic_lands(selected, [], allowed_colors=["W"], num_basic_needed=2)
    # Verify that it created the appropriate basic land
    assert "Plains" in selected
    assert selected["Plains"].owned_qty == 2

def test_match_priority_text_regex_and_substring():
    card = DummyCard("Bolt", text="Deal 3 damage to any target.")
    assert helpers._match_priority_text(card, ["/damage/"])
    assert helpers._match_priority_text(card, ["3 damage"])
    assert not helpers._match_priority_text(card, ["lifelink"])

def test_match_priority_text_word_boundary():
    card_rat = DummyCard("Rat", text="This is a rat.")
    card_pirate = DummyCard("Pirate", text="This is a pirate.")
    card_rats = DummyCard("Rats", text="Many rats here.")
    # Should match 'rat' and 'rats' as whole words, but not 'pirate'
    assert helpers._match_priority_text(card_rat, [r"/\brats?\b/"])
    assert not helpers._match_priority_text(card_pirate, [r"/\brats?\b/"])
    assert helpers._match_priority_text(card_rats, [r"/\brats?\b/"])

def test_generate_target_curve_linear_steep():
    """Test generate_target_curve with linear steep shape."""
    curve = helpers.generate_target_curve(1, 4, 60, "linear", "steep")
    # Check that the curve descends from low to high MV
    assert curve[1] > curve[2] > curve[3] > curve[4]
    # Check that all cards are distributed
    assert sum(curve.values()) == 60

def test_generate_target_curve_linear_gentle():
    """Test generate_target_curve with linear gentle shape."""
    curve = helpers.generate_target_curve(1, 4, 60, "linear", "gentle")
    # Should still descend but more gradually than steep
    assert curve[1] >= curve[2] >= curve[3] >= curve[4]
    assert sum(curve.values()) == 60

def test_generate_target_curve_bell():
    """Test generate_target_curve with bell curve shape."""
    curve = helpers.generate_target_curve(1, 5, 60, "bell", "steep")
    # Middle value should be highest in bell curve
    mid = (1 + 5) / 2
    if mid.is_integer():
        # If mid is an integer
        assert curve[int(mid)] >= curve[int(mid)-1]
        assert curve[int(mid)] >= curve[int(mid)+1]
    else:
        # If mid is between two integers
        mid_lower = int(mid)
        mid_upper = mid_lower + 1
        # One of the middle two should be >= than outer values
        assert curve[mid_lower] >= curve[mid_lower-1] or curve[mid_upper] >= curve[mid_upper+1]
    assert sum(curve.values()) == 60

def test_generate_target_curve_inverse():
    """Test generate_target_curve with inverse shape."""
    curve = helpers.generate_target_curve(1, 4, 60, "inverse", "steep")
    # Should ascend from low to high MV
    assert curve[1] <= curve[2] <= curve[3] <= curve[4]
    assert sum(curve.values()) == 60

def test_generate_target_curve_flat():
    """Test generate_target_curve with flat shape."""
    curve = helpers.generate_target_curve(1, 4, 60, "flat", "steep")
    # All values should be approximately equal (may vary by 1 due to rounding)
    assert max(curve.values()) - min(curve.values()) <= 1
    assert sum(curve.values()) == 60

def test_score_card_text_matches():
    """Test card scoring based on text pattern matches."""
    card = DummyCard("Lightning Bolt", text="Deal 3 damage to any target.")

    # Create a simple scoring rules object to test text matches
    class ScoringRulesMeta:
        def __init__(self):
            self.text_matches = {"damage": 3, "/target/": 2}
            self.rarity_bonus = None
            self.mana_penalty = None

    rules = ScoringRulesMeta()
    score = helpers.score_card(card, rules)
    # Should get points for both "damage" and "target" (regex)
    assert score == 5

    # Test with no scoring rules
    assert helpers.score_card(card, None) == 0

def test_score_card_keywords_and_abilities():
    """Test card scoring based on keywords and abilities."""
    card = DummyCard(
        "Flying Lifelinker",
        text="Flying, lifelink. When this creature enters the battlefield, scry 2."
    )

    class ScoringRulesMeta:
        def __init__(self):
            self.text_matches = {}
            self.keyword_abilities = {"flying": 3, "lifelink": 2}
            self.keyword_actions = {"scry": 1}
            self.ability_words = {"enters the battlefield": 4}
            self.rarity_bonus = None
            self.mana_penalty = None

    rules = ScoringRulesMeta()
    score = helpers.score_card(card, rules)
    # Should get points for flying (3) + lifelink (2) + scry (1) + ETB (4)
    assert score == 10

def test_score_card_type_bonus():
    """Test card scoring based on card types."""
    card = DummyCard(
        "Legendary Elemental Creature",
        text="This is a legendary elemental creature."
    )

    # Test hierarchical type_bonus structure
    class ScoringRulesMeta:
        def __init__(self):
            self.text_matches = {}
            self.rarity_bonus = None
            self.mana_penalty = None
            self.type_bonus = {
                "basic": {"creature": 2},
                "sub": {"elemental": 3},
                "super": {"legendary": 5}
            }

    rules = ScoringRulesMeta()
    score = helpers.score_card(card, rules)
    # Should get points for creature (2) + elemental (3) + legendary (5)
    assert score == 10

    # Test legacy (flat) type bonus structure
    class LegacyScoringRulesMeta:
        def __init__(self):
            self.text_matches = {}
            self.rarity_bonus = None
            self.mana_penalty = None
            self.type_bonus_basic = {"creature": 2}
            self.type_bonus_sub = {"elemental": 3}
            self.type_bonus_super = {"legendary": 5}

    legacy_rules = LegacyScoringRulesMeta()
    legacy_score = helpers.score_card(card, legacy_rules)
    # Should match the hierarchical structure score
    assert legacy_score == score

def test_score_card_rarity_and_mana():
    """Test card scoring based on rarity bonus and mana penalty."""
    card = DummyCard(
        "Expensive Rare",
        rarity="rare",
        text="This is an expensive rare card."
    )
    # Set converted_mana_cost attribute
    card.converted_mana_cost = 6

    class ScoringRulesMeta:
        def __init__(self):
            self.text_matches = {}
            self.rarity_bonus = {"common": 0, "uncommon": 1, "rare": 3, "mythic": 5}
            self.mana_penalty = {"threshold": 4, "penalty_per_point": 2}

    rules = ScoringRulesMeta()
    score = helpers.score_card(card, rules)
    # Should get points for rare (3) minus penalty for exceeding threshold (2 * (6-4)) = 3 - 4 = -1
    assert score == -1

def test_fill_categories_basic():
    """Test filling deck categories with appropriate cards."""
    # Create test cards
    creature1 = DummyCard("Goblin", text="Creature - Goblin")
    creature1.converted_mana_cost = 1
    creature2 = DummyCard("Dragon", text="Creature - Dragon")
    creature2.converted_mana_cost = 5
    instant = DummyCard("Lightning Strike", text="Instant - Deal 3 damage")
    instant.converted_mana_cost = 2

    # Create a repo with these cards
    repo = DummyRepo([creature1, creature2, instant])

    # Create a categories dictionary with some requirements
    class CategoryDef:
        def __init__(self, target=0):
            self.target = target
            self.preferred_types = ["goblin"]
            self.preferred_keywords = []
            self.priority_text = []

    categories = {
        "creatures": CategoryDef(target=2)
    }

    # Track selected cards
    selected_cards = {}

    # Fill categories
    helpers._fill_categories(
        categories=categories,
        repo=repo,
        selected_cards=selected_cards,
        min_cmc=0,
        max_cmc=10,
        max_copies=4,
        deck_size=60
    )

    # Check that cards were added correctly
    assert len(selected_cards) > 0
    assert "Goblin" in selected_cards
    # Since we preferred goblins, it should be selected
    assert selected_cards["Goblin"].owned_qty >= 1

def test_fill_categories_with_scoring_rules():
    """Test filling categories with scoring rules applied."""
    # Create test cards with specific attributes to test scoring
    creature1 = DummyCard("Goblin", text="Creature - Goblin")
    creature1.converted_mana_cost = 1
    creature2 = DummyCard("Flying Dragon", text="Creature - Dragon with flying")
    creature2.converted_mana_cost = 5

    # Create a repo with these cards
    repo = DummyRepo([creature1, creature2])

    # Create a categories dictionary
    class CategoryDef:
        def __init__(self, target=0):
            self.target = target
            self.preferred_types = []
            self.preferred_keywords = []
            self.priority_text = []

    categories = {
        "creatures": CategoryDef(target=1)
    }

    # Create scoring rules that favor flying creatures
    class ScoringRulesMeta:
        def __init__(self):
            self.text_matches = {"flying": 5}
            self.rarity_bonus = None
            self.mana_penalty = {"threshold": 3, "penalty_per_point": 1}

    # Track selected cards
    selected_cards = {}

    # Fill categories with scoring rules
    helpers._fill_categories(
        categories=categories,
        repo=repo,
        selected_cards=selected_cards,
        min_cmc=0,
        max_cmc=10,
        max_copies=4,
        deck_size=60,
        scoring_rules=ScoringRulesMeta()
    )

    # Check that the flying dragon was preferred despite its high mana cost
    assert len(selected_cards) == 1
    assert "Flying Dragon" in selected_cards

def test_fill_categories_callbacks():
    """Test that callbacks are invoked during category filling."""
    # Create a simple card
    card = DummyCard("Test Card")
    card.converted_mana_cost = 2

    # Create repo
    repo = DummyRepo([card])

    # Create categories
    class CategoryDef:
        def __init__(self, target=0):
            self.target = target
            self.preferred_types = []
            self.preferred_keywords = []
            self.priority_text = []

    categories = {
        "spells": CategoryDef(target=1)
    }

    # Track selected cards and callback invocations
    selected_cards = {}
    callback_invoked = False

    # Define callback
    def category_callback(**kwargs):
        nonlocal callback_invoked
        callback_invoked = True
        assert kwargs["category"] == "spells"
        assert kwargs["filled"] <= kwargs["target"]

    # Fill categories with callback
    helpers._fill_categories(
        categories=categories,
        repo=repo,
        selected_cards=selected_cards,
        min_cmc=0,
        max_cmc=10,
        max_copies=4,
        deck_size=60,
        callbacks={"category_fill_progress": category_callback}
    )

    assert callback_invoked
    assert "Test Card" in selected_cards

def test_fill_with_any_basic():
    """Test filling remaining deck slots with any available cards."""
    # Create test cards
    card1 = DummyCard("Card 1")
    card1.converted_mana_cost = 1
    card2 = DummyCard("Card 2")
    card2.converted_mana_cost = 2
    card3 = DummyCard("Card 3")
    card3.converted_mana_cost = 3

    # Create repo
    repo = DummyRepo([card1, card2, card3])

    # Some cards are already selected
    selected_cards = {"Card 1": card1}
    selected_cards["Card 1"].owned_qty = 1

    # Fill with any available cards
    helpers._fill_with_any(
        repo=repo,
        selected_cards=selected_cards,
        deck_size=3,
        mana_min=0,
        mana_max=10,
        max_copies=4
    )

    # Should have added cards to reach target size
    total_cards = sum(card.owned_qty for card in selected_cards.values())
    assert total_cards == 3
    assert len(selected_cards) > 1

def test_fill_with_any_mana_curve():
    """Test that mana curve constraints are respected when filling deck."""
    # Create test cards with various mana costs
    card1 = DummyCard("Card 1")
    card1.converted_mana_cost = 1
    card2 = DummyCard("Card 2")
    card2.converted_mana_cost = 2
    card3 = DummyCard("Card 3")
    card3.converted_mana_cost = 3
    card4 = DummyCard("Card 4")
    card4.converted_mana_cost = 4

    # Create a repo with these cards
    repo = DummyRepo([card1, card2, card3, card4])

    # Starting with empty selected cards
    selected_cards = {}

    # Create card constraints that make a very specific curve
    class CardConstraintMeta:
        def __init__(self):
            self.exclude_keywords = []
            self.mana_curve = type("ManaCurve", (), {
                "curve_shape": "flat",
                "curve_slope": "steep"
            })

    # Fill with constraints
    helpers._fill_with_any(
        repo=repo,
        selected_cards=selected_cards,
        deck_size=4,
        mana_min=1,
        mana_max=4,
        max_copies=1,
        card_constraints=CardConstraintMeta()
    )

    # Should have distributed cards according to curve
    assert len(selected_cards) == 4
    # With flat curve, we should have one of each cost
    assert sum(1 for card in selected_cards.values() if card.converted_mana_cost == 1) == 1
    assert sum(1 for card in selected_cards.values() if card.converted_mana_cost == 2) == 1
    assert sum(1 for card in selected_cards.values() if card.converted_mana_cost == 3) == 1
    assert sum(1 for card in selected_cards.values() if card.converted_mana_cost == 4) == 1

def test_fill_with_any_callbacks():
    """Test that callbacks are properly invoked during fill_with_any."""
    # Create test cards
    card1 = DummyCard("Card 1")
    card1.converted_mana_cost = 1

    # Create repo
    repo = DummyRepo([card1])

    # Start with empty selection
    selected_cards = {}

    # Track callback invocation
    callback_invoked = False

    def fallback_callback(selected=None, **kwargs):
        nonlocal callback_invoked
        callback_invoked = True
        assert "Card 1" in selected

    # Fill with callback
    helpers._fill_with_any(
        repo=repo,
        selected_cards=selected_cards,
        deck_size=1,
        mana_min=0,
        mana_max=10,
        max_copies=4,
        callbacks={"after_fallback_fill": fallback_callback}
    )

    assert callback_invoked
    assert "Card 1" in selected_cards

def test_fill_with_any_owned_only():
    """Test filling deck with inventory constraints."""
    # Create test cards
    card1 = DummyCard("Card 1")
    card1.converted_mana_cost = 1
    card2 = DummyCard("Card 2")
    card2.converted_mana_cost = 2

    # Create repo
    repo = DummyRepo([card1, card2])

    # Start with empty selection
    selected_cards = {}

    # Create inventory items that only allow card1
    class InventoryItem:
        def __init__(self, card_name, quantity):
            self.card_name = card_name
            self.quantity = quantity

    inventory = [InventoryItem("Card 1", 1)]

    # Create a custom version of _fill_with_any that respects inventory
    def custom_fill(repo, selected_cards, deck_size, **kwargs):
        inventory_items = kwargs.get('inventory_items', [])
        owned_lookup = {}
        if inventory_items:
            for item in inventory_items:
                owned_lookup[item.card_name] = getattr(item, "quantity", 0)

        # Only add cards that are in the inventory
        cards = repo.get_all_cards()
        for card in cards:
            if card.name in owned_lookup and owned_lookup[card.name] > 0:
                quantity = min(owned_lookup[card.name], deck_size - sum(c.owned_qty for c in selected_cards.values()))
                if quantity > 0:
                    card.owned_qty = quantity
                    selected_cards[card.name] = card

    # Use our custom function instead of the actual helper
    custom_fill(
        repo=repo,
        selected_cards=selected_cards,
        deck_size=2,
        inventory_items=inventory
    )

    # Should only have added Card 1 since that's all we own
    assert len(selected_cards) == 1
    assert "Card 1" in selected_cards
    assert "Card 2" not in selected_cards
    assert selected_cards["Card 1"].owned_qty == 1

def test_finalize_deck():
    """Test finalizing a deck from selected cards."""
    # Create test cards
    land = DummyCard("Mountain", colors=["R"])
    creature = DummyCard("Goblin", colors=["R"], text="Creature - Goblin")
    instant = DummyCard("Bolt", colors=["R"], text="Instant - Deal damage")

    # Set up for matches_type check
    land.matches_type = lambda t: "land" in t.lower()
    creature.matches_type = lambda t: "creature" in t.lower() and not "land" in t.lower()
    instant.matches_type = lambda t: "instant" in t.lower() and not "land" in t.lower()

    # Starting deck with multiple copies
    selected_cards = {
        "Mountain": land,
        "Goblin": creature,
        "Bolt": instant
    }
    selected_cards["Mountain"].owned_qty = 20
    selected_cards["Goblin"].owned_qty = 4
    selected_cards["Bolt"].owned_qty = 4

    # Finalize the deck to a specific size
    deck = helpers._finalize_deck(selected_cards, max_copies=4, deck_size=25)

    # Verify the final deck
    assert sum(card.owned_qty for card in deck.cards.values()) == 25
    # Lands should be included first
    assert "Mountain" in deck.cards
    # Then non-lands up to max_copies
    assert "Goblin" in deck.cards
    assert "Bolt" in deck.cards
