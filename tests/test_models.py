"""
Unit tests for mtg_deck_builder.db.models
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from mtg_deck_builder.db.models import Base, CardDB, CardSetDB, CardPrintingDB, InventoryItemDB
from datetime import date

def setup_in_memory_db():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()

def test_card_db_properties():
    session = setup_in_memory_db()
    set1 = CardSetDB(set_code='SET1', set_name='Set One', release_date=date(2020,1,1), set_metadata={})
    card = CardDB(name='Test Card')
    printing = CardPrintingDB(uid='UID1', card_name='Test Card', set_code='SET1', card_type='Creature', rarity='rare', mana_cost='{1}{G}', power='2', toughness='2', colors=['G'], color_identity=['G'])
    printing.set = set1
    card.printings.append(printing)
    session.add_all([set1, card, printing])
    session.commit()
    # Test properties
    assert card.type == 'Creature'
    assert card.rarity == 'rare'
    assert card.mana_cost == '{1}{G}'
    assert card.power == '2'
    assert card.toughness == '2'
    assert card.colors == ['G']
    assert card.converted_mana_cost == 2
    assert card.matches_type('creature')
    assert card.matches_color_identity(['G'])
    assert not card.matches_color_identity(['U'])
    assert not card.is_basic_land()

def test_inventory_item_db():
    session = setup_in_memory_db()
    inv = InventoryItemDB(card_name='Test Card', quantity=3)
    session.add(inv)
    session.commit()
    item = session.query(InventoryItemDB).first()
    assert item.card_name == 'Test Card'
    assert item.quantity == 3

