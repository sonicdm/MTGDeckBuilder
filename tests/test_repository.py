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
    inv = InventoryItemDB(card_name='Test Card', quantity=2, is_infinite=False)
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
