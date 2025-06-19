"""
Unit tests for CardRepository filtering logic, especially type_query and names_in.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from mtg_deck_builder.db.models import Base, CardDB, CardSetDB, CardPrintingDB
from mtg_deck_builder.db.repository import CardRepository

def setup_in_memory_db():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()

def populate_basic_and_nonbasic_lands(session):
    set1 = CardSetDB(set_code='SET1', set_name='Set One', set_metadata={})
    session.add(set1)
    # Basic lands with various type strings
    basic_types = [
        'Basic Land',
        'Basic Land — Plains',
        'Basic Land — Island',
        'Basic Land — Swamp',
        'Basic Land — Mountain',
        'Basic Land — Forest',
        'Land — Basic',
        'Land — Basic — Plains',
    ]
    names = ['Plains', 'Island', 'Swamp', 'Mountain', 'Forest', 'Wastes', 'Snow-Covered Plains']
    for name, ctype in zip(names, basic_types):
        card = CardDB(name=name)
        printing = CardPrintingDB(uid=f'UID_{name}', card_name=name, set_code='SET1', card_type=ctype, rarity='common')
        printing.set = set1
        card.printings.append(printing)
        card.newest_printing_uid = f'UID_{name}'
        session.add(card)
        session.add(printing)
    # Non-basic land
    non_basic = CardDB(name='Temple of Mystery')
    nb_printing = CardPrintingDB(uid='UID_TEMPLE', card_name='Temple of Mystery', set_code='SET1', card_type='Land', rarity='rare')
    nb_printing.set = set1
    non_basic.printings.append(nb_printing)
    non_basic.newest_printing_uid = 'UID_TEMPLE'
    session.add(non_basic)
    session.add(nb_printing)
    session.commit()

def test_type_query_basic_land():
    session = setup_in_memory_db()
    populate_basic_and_nonbasic_lands(session)
    repo = CardRepository(session)
    # Should match all cards with both 'Basic' and 'Land' in type
    basic_lands = repo.filter_cards(type_query="Basic Land").get_all_cards()
    names = {c.name for c in basic_lands}
    assert 'Plains' in names
    assert 'Island' in names
    assert 'Swamp' in names
    assert 'Mountain' in names
    assert 'Forest' in names
    assert 'Wastes' in names
    assert 'Snow-Covered Plains' in names
    assert 'Temple of Mystery' not in names
    session.close()

def test_type_query_land():
    session = setup_in_memory_db()
    populate_basic_and_nonbasic_lands(session)
    repo = CardRepository(session)
    # Should match all lands (basic and non-basic)
    lands = repo.filter_cards(type_query="land").get_all_cards()
    names = {c.name for c in lands}
    assert 'Plains' in names
    assert 'Temple of Mystery' in names
    assert 'Wastes' in names
    session.close()

def test_names_in_and_type_query():
    session = setup_in_memory_db()
    populate_basic_and_nonbasic_lands(session)
    repo = CardRepository(session)
    # Should match only the specified names that are also basic lands
    names_in = ['Plains', 'Island']
    filtered = repo.filter_cards(names_in=names_in, type_query="Basic Land").get_all_cards()
    names = {c.name for c in filtered}
    assert names == {'Plains', 'Island'}
    session.close()

def test_type_query_case_insensitivity():
    session = setup_in_memory_db()
    populate_basic_and_nonbasic_lands(session)
    repo = CardRepository(session)
    # Should match regardless of case
    lands = repo.filter_cards(type_query="bAsIc lAnD").get_all_cards()
    names = {c.name for c in lands}
    assert 'Plains' in names
    assert 'Wastes' in names
    session.close()

def test_type_query_partial_match():
    session = setup_in_memory_db()
    populate_basic_and_nonbasic_lands(session)
    repo = CardRepository(session)
    # Should not match if only one keyword is present
    only_basic = repo.filter_cards(type_query="Basic").get_all_cards()
    only_land = repo.filter_cards(type_query="Land").get_all_cards()
    assert len(only_basic) < len(only_land)
    session.close()

