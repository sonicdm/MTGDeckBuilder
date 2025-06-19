import json
import pytest
from .helpers import get_sample_data_path
from .fixtures import DummyCard, DummyRepo
from mtg_deck_builder.db.repository import CardRepository

def test_sample_data_exists():
    """Test that the sample data file exists and can be loaded"""
    sample_file = get_sample_data_path("sample_allprintings.json")
    with open(sample_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    assert 'data' in data
    assert len(data['data']) > 0

def test_sample_data_structure():
    """Test that the sample data has the expected structure"""
    sample_file = get_sample_data_path("sample_allprintings.json")
    with open(sample_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Check a few random sets
    for set_code, set_data in data['data'].items():
        assert 'name' in set_data
        assert 'code' in set_data
        assert 'cards' in set_data
        assert isinstance(set_data['cards'], list)

def test_dummy_repo_with_sample_data():
    """Test that we can create a DummyRepo with cards from the sample data"""
    sample_file = get_sample_data_path("sample_allprintings.json")
    with open(sample_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Create some dummy cards from the sample data
    dummy_cards = []
    for set_code, set_data in data['data'].items():
        for card in set_data['cards'][:5]:  # Take first 5 cards from each set
            if 'name' in card:
                dummy_cards.append(DummyCard(
                    name=card['name'],
                    colors=card.get('colors', []),
                    rarity=card.get('rarity'),
                    legalities=card.get('legalities', {}),
                    text=card.get('text', '')
                ))
    
    # Create a dummy repo with these cards
    repo = DummyRepo(dummy_cards)
    
    # Test some basic repo operations
    assert len(list(repo.get_all_cards())) > 0
    
    # Test finding a card by name
    if dummy_cards:
        test_card = dummy_cards[0]
        found_card = repo.find_by_name(test_card.name)
        assert found_card is not None
        assert found_card.name == test_card.name

def test_dummy_card_operations():
    """Test the DummyCard operations with sample data"""
    # Create a test card
    card = DummyCard(
        name="Test Card",
        colors=["W", "U"],
        rarity="rare",
        legalities={"standard": "legal"},
        text="This is a test card"
    )
    
    # Test color identity matching
    assert card.matches_color_identity(["W", "U"], "exact")
    assert not card.matches_color_identity(["W"], "exact")
    
    # Test type matching
    assert card.matches_type("test")
    assert not card.matches_type("dragon")
    
    # Test basic land check
    assert not card.is_basic_land()
    basic_land = DummyCard(name="Plains")
    assert basic_land.is_basic_land()

def test_card_filtering(create_dummy_db):
    """
    Test real SQL filtering using the sample data loaded into a temporary DB.
    """
    session = create_dummy_db
    repo = CardRepository(session)

    # Test filtering by color identity
    red_cards = repo.filter_cards(color_identity=['R'], color_mode='any').get_all_cards()
    assert all('R' in (c.colors or []) for c in red_cards)

    # Test filtering by name
    bolt_cards = repo.filter_cards(name_query='Bolt').get_all_cards()
    assert all('Bolt' in c.card_name for c in bolt_cards)

    # Test filtering by rarity
    rare_cards = repo.filter_cards(rarity='rare').get_all_cards()
    assert all(c.rarity == 'rare' for c in rare_cards)

    # Test filtering by type
    creature_cards = repo.filter_cards(basic_type='Creature').get_all_cards()
    assert all('Creature' in (c.type or '') for c in creature_cards)

    # Test filtering by text
    text_cards = repo.filter_cards(text_query='damage').get_all_cards()
    assert all('damage' in (c.text or '').lower() for c in text_cards)

    # Test filtering by legalities
    legal_cards = repo.filter_cards(legal_in='standard').get_all_cards()
    assert all((c.legalities or {}).get('standard', '').lower() == 'legal' for c in legal_cards)

    # Test filtering by multiple criteria
    red_creatures = repo.filter_cards(color_identity=['R'], color_mode='any', basic_type='Creature').get_all_cards()
    assert all('R' in (c.colors or []) and 'Creature' in (c.type or '') for c in red_creatures)

    # Test filtering by inventory quantity
    owned_cards = repo.filter_cards(min_quantity=1).get_all_cards()
    assert all(getattr(c, 'owned_qty', 0) >= 1 for c in owned_cards)

    # Test filtering for colorless cards
    colorless_cards = repo.filter_cards(color_identity=['R', 'C'], color_mode='subset').get_all_cards()
    failed = [c for c in colorless_cards if not (set(c.colors or []) <= {'R'})]
    if failed:
        print('Cards failing colorless filter:')
        for c in failed:
            print(f"{c.card_name}: {c.colors}")
    assert not failed

    # Test filtering by supertype
    legendary_cards = repo.filter_cards(supertype='Legendary').get_all_cards()
    assert all('Legendary' in (c.type or '') for c in legendary_cards)

    # Test filtering by subtype
    dragon_cards = repo.filter_cards(subtype='Dragon').get_all_cards()
    assert all('Dragon' in (c.type or '') for c in dragon_cards)

    # Test filtering by keyword
    keyword_cards = repo.filter_cards(keyword_multi=['Flying']).get_all_cards()
    assert all(
        'flying' in (c.text or '').lower() or 
        'flying' in (c.type or '').lower() or 
        'flying' in (c.card_name or '').lower() 
        for c in keyword_cards
    )

    # Test filtering by type query (list)
    type_query_cards = repo.filter_cards(type_query=['Artifact', 'Creature']).get_all_cards()
    assert all('Artifact' in (c.type or '') and 'Creature' in (c.type or '') for c in type_query_cards)

    # Test filtering by type query (string)
    type_query_cards = repo.filter_cards(type_query='Artifact').get_all_cards()
    assert all('Artifact' in (c.type or '') for c in type_query_cards)

    # Test filtering by names_in
    names_in_cards = repo.filter_cards(names_in=['Lightning Bolt', 'Monastery Swiftspear']).get_all_cards()
    assert all(c.card_name in ['Lightning Bolt', 'Monastery Swiftspear'] for c in names_in_cards)

    # Test filtering by printing_field_filters
    printing_field_cards = repo.filter_cards(printing_field_filters={'rarity': 'rare'}).get_all_cards()
    assert all(c.rarity == 'rare' for c in printing_field_cards) 