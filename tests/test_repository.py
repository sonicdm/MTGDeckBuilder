"""
Unit tests for mtg_deck_builder.db.repository
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from mtg_deck_builder.db.models import Base, CardDB, CardSetDB, CardPrintingDB, InventoryItemDB
from mtg_deck_builder.db.repository import CardRepository, CardSetRepository, InventoryRepository

def setup_in_memory_db():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()

def populate_sample_data(session):
    set1 = CardSetDB(set_code='SET1', set_name='Set One', set_metadata={})
    card1 = CardDB(name='Test Card')
    printing1 = CardPrintingDB(uid='UID1', card_name='Test Card', set_code='SET1')
    printing1.set = set1
    card1.printings.append(printing1)
    session.add_all([set1, card1, printing1])
    session.commit()
    inv = InventoryItemDB(card_name='Test Card', quantity=2)
    session.add(inv)
    session.commit()

def test_card_repository_get_all_cards():
    session = setup_in_memory_db()
    populate_sample_data(session)
    repo = CardRepository(session)
    cards = repo.get_all_cards()
    assert len(cards) == 1
    assert cards[0].name == 'Test Card'

def test_card_repository_find_by_name():
    session = setup_in_memory_db()
    populate_sample_data(session)
    repo = CardRepository(session)
    card = repo.find_by_name('Test')
    assert card is not None
    assert 'Test Card' in card.name

def test_card_set_repository():
    session = setup_in_memory_db()
    populate_sample_data(session)
    repo = CardSetRepository(session)
    sets = repo.get_all_sets()
    assert len(sets) == 1
    found = repo.find_by_code('SET1')
    assert found is not None
    assert found.set_name == 'Set One'

def test_inventory_repository():
    session = setup_in_memory_db()
    populate_sample_data(session)
    repo = InventoryRepository(session)
    items = repo.get_all_items()
    assert len(items) == 1
    owned = repo.get_owned_cards()
    assert len(owned) == 1
    found = repo.find_by_card_name('Test Card')
    assert found is not None
    assert found.quantity == 2

def setup_filterable_cards(session):
    # Create a set
    set1 = CardSetDB(set_code='SET1', set_name='Set One', set_metadata={})
    session.add(set1)

    # Create a variety of cards to test filtering on
    cards_data = [
        # Basic lands
        {
            'name': 'Plains',
            'uid': 'UID1',
            'card_type': 'Basic Land — Plains',
            'rarity': 'common',
            'colors': [],
            'color_identity': ['W'],
            'supertypes': ['Basic'],
            'subtypes': ['Plains'],
            'text': '{T}: Add {W}.'
        },
        {
            'name': 'Island',
            'uid': 'UID2',
            'card_type': 'Basic Land — Island',
            'rarity': 'common',
            'colors': [],
            'color_identity': ['U'],
            'supertypes': ['Basic'],
            'subtypes': ['Island'],
            'text': '{T}: Add {U}.'
        },

        # Non-basic lands
        {
            'name': 'Temple of Mystery',
            'uid': 'UID3',
            'card_type': 'Land',
            'rarity': 'rare',
            'colors': [],
            'color_identity': ['G', 'U'],
            'supertypes': [],
            'subtypes': [],
            'text': 'Temple of Mystery enters the battlefield tapped.\nWhen Temple of Mystery enters the battlefield, scry 1.\n{T}: Add {G} or {U}.'
        },

        # Creatures
        {
            'name': 'Grizzly Bears',
            'uid': 'UID4',
            'card_type': 'Creature — Bear',
            'rarity': 'common',
            'colors': ['G'],
            'color_identity': ['G'],
            'supertypes': [],
            'subtypes': ['Bear'],
            'text': '',
            'power': '2',
            'toughness': '2'
        },
        {
            'name': 'Serra Angel',
            'uid': 'UID5',
            'card_type': 'Creature — Angel',
            'rarity': 'uncommon',
            'colors': ['W'],
            'color_identity': ['W'],
            'supertypes': [],
            'subtypes': ['Angel'],
            'text': 'Flying, vigilance',
            'keywords': ['Flying', 'Vigilance'],
            'power': '4',
            'toughness': '4'
        },

        # Multicolor card
        {
            'name': 'Azorius Charm',
            'uid': 'UID6',
            'card_type': 'Instant',
            'rarity': 'uncommon',
            'colors': ['W', 'U'],
            'color_identity': ['W', 'U'],
            'supertypes': [],
            'subtypes': [],
            'text': 'Choose one —\n• Target attacking or blocking creature returns to its owner\'s hand.\n• You gain 3 life.\n• Draw a card.'
        },

        # Artifact
        {
            'name': 'Sol Ring',
            'uid': 'UID7',
            'card_type': 'Artifact',
            'rarity': 'rare',
            'colors': [],
            'color_identity': [],
            'supertypes': [],
            'subtypes': [],
            'text': '{T}: Add {C}{C}.'
        }
    ]

    # Create all the cards and their printings
    for card_data in cards_data:
        card = CardDB(name=card_data['name'])
        printing = CardPrintingDB(
            uid=card_data['uid'],
            card_name=card_data['name'],
            set_code='SET1',
            card_type=card_data['card_type'],
            rarity=card_data['rarity'],
            colors=card_data['colors'],
            color_identity=card_data['color_identity'],
            supertypes=card_data.get('supertypes', []),
            subtypes=card_data.get('subtypes', []),
            text=card_data.get('text', ''),
            keywords=card_data.get('keywords', []),
            power=card_data.get('power'),
            toughness=card_data.get('toughness')
        )
        printing.set = set1
        card.printings.append(printing)
        card.newest_printing_uid = card_data['uid']
        session.add(card)
        session.add(printing)

        # Add inventory items as well
        inv = InventoryItemDB(card_name=card_data['name'], quantity=3)
        session.add(inv)

    session.commit()

def test_land_filtering_and_non_basic_logic():
    session = setup_in_memory_db()
    setup_filterable_cards(session)

    repo = CardRepository(session)
    # Use basic_type="land" instead of type_query="land"
    all_lands = repo.filter_cards(basic_type="land").get_all_cards()
    all_land_names = {c.name for c in all_lands}
    assert 'Plains' in all_land_names
    assert 'Island' in all_land_names
    assert 'Temple of Mystery' in all_land_names
    assert 'Grizzly Bears' not in all_land_names
    assert 'Serra Angel' not in all_land_names
    assert 'Sol Ring' not in all_land_names

    non_basic_lands = [card for card in all_lands if not card.is_basic_land()]
    non_basic_land_names = {c.name for c in non_basic_lands}
    assert 'Temple of Mystery' in non_basic_land_names
    assert 'Plains' not in non_basic_land_names
    assert 'Island' not in non_basic_land_names

def test_type_query_filtering():
    session = setup_in_memory_db()
    setup_filterable_cards(session)

    repo = CardRepository(session)

    # Use basic_type="creature" instead of type_query="creature"
    creatures = repo.filter_cards(basic_type="creature").get_all_cards()
    creature_names = {c.name for c in creatures}
    assert 'Grizzly Bears' in creature_names
    assert 'Serra Angel' in creature_names
    assert 'Sol Ring' not in creature_names
    assert 'Plains' not in creature_names

    # For multiple types, we'd combine queries or implement a different approach
    # Since we're moving away from type_query, let's use two separate queries and combine results
    artifacts = repo.filter_cards(basic_type="artifact").get_all_cards()
    creatures = repo.filter_cards(basic_type="creature").get_all_cards()

    # Combine results
    artifacts_creatures = list(set(artifacts + creatures))
    artifact_creature_names = {c.name for c in artifacts_creatures}

    assert 'Grizzly Bears' in artifact_creature_names
    assert 'Serra Angel' in artifact_creature_names
    assert 'Sol Ring' in artifact_creature_names
    assert 'Plains' not in artifact_creature_names
    assert 'Azorius Charm' not in artifact_creature_names

def test_color_identity_filtering():
    session = setup_in_memory_db()
    setup_filterable_cards(session)

    repo = CardRepository(session)

    # Test subset mode (default)
    mono_white = repo.filter_cards(color_identity=['W'], color_mode="subset").get_all_cards()
    mono_white_names = {c.name for c in mono_white}
    assert 'Plains' in mono_white_names  # Basic land with W identity
    assert 'Serra Angel' in mono_white_names  # White creature
    assert 'Grizzly Bears' not in mono_white_names  # Green
    assert 'Azorius Charm' not in mono_white_names  # WU (not a subset of just W)
    assert 'Temple of Mystery' not in mono_white_names  # GU
    assert 'Sol Ring' not in mono_white_names  # Colorless

    # Test subset mode with colorless
    mono_white_with_colorless = repo.filter_cards(
        color_identity=['W'], 
        color_mode="subset",
        allow_colorless=True
    ).get_all_cards()
    mono_white_with_colorless_names = {c.name for c in mono_white_with_colorless}
    assert 'Plains' in mono_white_with_colorless_names
    assert 'Serra Angel' in mono_white_with_colorless_names
    assert 'Sol Ring' in mono_white_with_colorless_names  # Now includes colorless
    assert 'Grizzly Bears' not in mono_white_with_colorless_names
    assert 'Azorius Charm' not in mono_white_with_colorless_names

    # Test exact mode
    exactly_azorius = repo.filter_cards(color_identity=['W', 'U'], color_mode="exact").get_all_cards()
    exactly_azorius_names = {c.name for c in exactly_azorius}
    assert 'Azorius Charm' in exactly_azorius_names  # WU
    assert 'Plains' not in exactly_azorius_names  # W only
    assert 'Island' not in exactly_azorius_names  # U only
    assert 'Temple of Mystery' not in exactly_azorius_names  # GU
    assert 'Sol Ring' not in exactly_azorius_names  # Colorless

    # Test any mode
    any_blue = repo.filter_cards(color_identity=['U'], color_mode="any").get_all_cards()
    any_blue_names = {c.name for c in any_blue}
    assert 'Island' in any_blue_names  # U
    assert 'Azorius Charm' in any_blue_names  # WU
    assert 'Temple of Mystery' in any_blue_names  # GU
    assert 'Plains' not in any_blue_names  # W
    assert 'Grizzly Bears' not in any_blue_names  # G
    assert 'Sol Ring' not in any_blue_names  # Colorless

    # Test any mode with colorless
    any_blue_with_colorless = repo.filter_cards(
        color_identity=['U'], 
        color_mode="any",
        allow_colorless=True
    ).get_all_cards()
    any_blue_with_colorless_names = {c.name for c in any_blue_with_colorless}
    assert 'Island' in any_blue_with_colorless_names
    assert 'Azorius Charm' in any_blue_with_colorless_names
    assert 'Temple of Mystery' in any_blue_with_colorless_names
    assert 'Sol Ring' in any_blue_with_colorless_names  # Now includes colorless
    assert 'Plains' not in any_blue_with_colorless_names
    assert 'Grizzly Bears' not in any_blue_with_colorless_names

def test_combined_filtering():
    session = setup_in_memory_db()
    setup_filterable_cards(session)

    repo = CardRepository(session)

    # Filter for white creatures
    white_creatures = repo.filter_cards(
        color_identity=['W'],
        color_mode="subset",
        basic_type="creature"
    ).get_all_cards()

    white_creature_names = {c.name for c in white_creatures}
    assert 'Serra Angel' in white_creature_names  # White creature
    assert 'Grizzly Bears' not in white_creature_names  # Green creature
    assert 'Plains' not in white_creature_names  # White land, not a creature
    assert 'Sol Ring' not in white_creature_names  # Colorless artifact

    # Filter for white creatures with colorless
    white_creatures_with_colorless = repo.filter_cards(
        color_identity=['W'],
        color_mode="subset",
        allow_colorless=True,
        basic_type="creature"
    ).get_all_cards()

    white_creature_with_colorless_names = {c.name for c in white_creatures_with_colorless}
    assert 'Serra Angel' in white_creature_with_colorless_names
    assert 'Grizzly Bears' not in white_creature_with_colorless_names
    assert 'Plains' not in white_creature_with_colorless_names
    assert 'Sol Ring' not in white_creature_with_colorless_names  # Still not a creature

    # Filter for rare artifacts
    rare_artifacts = repo.filter_cards(
        rarity="rare",
        basic_type="artifact"
    ).get_all_cards()

    rare_artifact_names = {c.name for c in rare_artifacts}
    assert 'Sol Ring' in rare_artifact_names  # Rare artifact
    assert 'Grizzly Bears' not in rare_artifact_names  # Common creature

    # Filter for rare artifacts with specific colors
    rare_blue_artifacts = repo.filter_cards(
        rarity="rare",
        basic_type="artifact",
        color_identity=['U'],
        color_mode="any"
    ).get_all_cards()

    rare_blue_artifact_names = {c.name for c in rare_blue_artifacts}
    assert 'Sol Ring' not in rare_blue_artifact_names  # Colorless
    assert 'Grizzly Bears' not in rare_blue_artifact_names  # Not an artifact

def test_text_query_filtering():
    session = setup_in_memory_db()
    setup_filterable_cards(session)

    repo = CardRepository(session)

    # Filter for cards mentioning "flying"
    flying_cards = repo.filter_cards(text_query="flying").get_all_cards()
    flying_card_names = {c.name for c in flying_cards}
    assert 'Serra Angel' in flying_card_names  # Has flying
    assert 'Grizzly Bears' not in flying_card_names  # No flying

    # Filter for cards mentioning "add"
    mana_producing_cards = repo.filter_cards(text_query="add").get_all_cards()
    mana_producing_names = {c.name for c in mana_producing_cards}
    assert 'Plains' in mana_producing_names  # Basic land that adds mana
    assert 'Island' in mana_producing_names  # Basic land that adds mana
    assert 'Temple of Mystery' in mana_producing_names  # Non-basic land that adds mana
    assert 'Sol Ring' in mana_producing_names  # Artifact that adds mana
    assert 'Serra Angel' not in mana_producing_names  # Doesn't add mana

def test_min_quantity_filter():
    session = setup_in_memory_db()
    setup_filterable_cards(session)

    # Add a new card with a different quantity
    set1 = session.query(CardSetDB).filter_by(set_code='SET1').one()
    limited_card = CardDB(name='Limited Card')
    limited_printing = CardPrintingDB(
        uid='LIMITED1',
        card_name='Limited Card',
        set_code='SET1',
        card_type='Creature',
        rarity='mythic'
    )
    limited_printing.set = set1
    limited_card.printings.append(limited_printing)
    limited_card.newest_printing_uid = 'LIMITED1'
    session.add(limited_card)
    session.add(limited_printing)

    # Add inventory item with only 1 copy
    inv = InventoryItemDB(card_name='Limited Card', quantity=1)
    session.add(inv)
    session.commit()

    repo = CardRepository(session)

    # All cards should have standard quantity of 3 except for Limited Card
    cards_qty_3_plus = repo.filter_cards(min_quantity=3).get_all_cards()
    cards_qty_3_plus_names = {c.name for c in cards_qty_3_plus}
    assert 'Plains' in cards_qty_3_plus_names
    assert 'Serra Angel' in cards_qty_3_plus_names
    assert 'Limited Card' not in cards_qty_3_plus_names

    # All cards should be included with min_quantity of 1
    all_cards = repo.filter_cards(min_quantity=1).get_all_cards()
    all_card_names = {c.name for c in all_cards}
    assert 'Plains' in all_card_names
    assert 'Serra Angel' in all_card_names
    assert 'Limited Card' in all_card_names

def test_safe_filtering_methods():
    """Test that safe filtering methods don't crash with detached instances"""
    session = setup_in_memory_db()
    setup_filterable_cards(session)

    repo = CardRepository(session)

    # Get cards and then detach them by closing the session
    cards = repo.get_all_cards()
    session.close()

    # Try filtering detached cards - should handle errors gracefully
    filtered_repo = CardRepository(cards=cards)

    # Should not raise exceptions
    basic_type_filtered = filtered_repo.filter_cards(basic_type="creature").get_all_cards()
    assert any(c.name == 'Serra Angel' for c in basic_type_filtered)
    assert all(c.name != 'Sol Ring' for c in basic_type_filtered)

def test_keyword_filtering():
    session = setup_in_memory_db()
    setup_filterable_cards(session)

    repo = CardRepository(session)

    # Filter for cards with Flying
    flying_cards = repo.filter_cards(keyword_multi="Flying").get_all_cards()
    flying_card_names = {c.name for c in flying_cards}
    assert 'Serra Angel' in flying_card_names  # Has Flying
    assert 'Grizzly Bears' not in flying_card_names  # No keywords

    # Filter for cards with both Flying and Vigilance
    flying_vigilance_cards = repo.filter_cards(keyword_multi=["Flying", "Vigilance"]).get_all_cards()
    flying_vigilance_names = {c.name for c in flying_vigilance_cards}
    assert 'Serra Angel' in flying_vigilance_names  # Has both keywords
    assert 'Grizzly Bears' not in flying_vigilance_names

def test_color_filtering():
    """Test color identity filtering in all modes."""
    session = setup_in_memory_db()
    repo = CardRepository(session)

    # Test data setup
    test_cards = [
        # Mono-colored
        CardDB(name="Red Card", colors=["R"]),
        CardDB(name="Blue Card", colors=["U"]),
        # Multi-colored
        CardDB(name="UR Card", colors=["U", "R"]),
        CardDB(name="BR Card", colors=["B", "R"]),
        CardDB(name="WUBRG Card", colors=["W", "U", "B", "R", "G"]),
        # Colorless
        CardDB(name="Colorless Card", colors=[]),
    ]
    session.add_all(test_cards)
    session.commit()

    # Test exact mode
    exact_repo = repo.filter_cards(color_identity=["U", "R"], color_mode="exact")
    exact_cards = exact_repo.get_all_cards()
    assert len(exact_cards) == 1
    assert exact_cards[0].name == "UR Card"

    # Test any mode
    any_repo = repo.filter_cards(color_identity=["U", "R"], color_mode="any")
    any_cards = any_repo.get_all_cards()
    assert len(any_cards) == 3  # UR, U, R
    assert all(card.name in ["UR Card", "Red Card", "Blue Card"] for card in any_cards)

    # Test subset mode without colorless
    subset_repo = repo.filter_cards(color_identity=["U", "R"], color_mode="subset")
    subset_cards = subset_repo.get_all_cards()
    assert len(subset_cards) == 3  # UR, U, R
    assert all(card.name in ["UR Card", "Red Card", "Blue Card"] for card in subset_cards)

    # Test subset mode with colorless
    subset_colorless_repo = repo.filter_cards(
        color_identity=["U", "R"], 
        color_mode="subset",
        allow_colorless=True
    )
    subset_colorless_cards = subset_colorless_repo.get_all_cards()
    assert len(subset_colorless_cards) == 4  # UR, U, R, Colorless
    assert all(card.name in ["UR Card", "Red Card", "Blue Card", "Colorless Card"] 
              for card in subset_colorless_cards)

    # Test that cards with unwanted colors are excluded
    unwanted_repo = repo.filter_cards(color_identity=["U", "R"], color_mode="subset")
    unwanted_cards = unwanted_repo.get_all_cards()
    assert "BR Card" not in [card.name for card in unwanted_cards]
    assert "WUBRG Card" not in [card.name for card in unwanted_cards]

    # Cleanup
    session.close()
