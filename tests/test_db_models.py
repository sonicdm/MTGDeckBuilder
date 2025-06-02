import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import date
from mtg_deck_builder.db.models import Base, CardDB, CardPrintingDB, CardSetDB

def setup_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session

def test_cardprintingdb_repr_str():
    cp = CardPrintingDB(uid="u1", card_name="Test Card", set_code="SET1")
    assert "Test Card" in repr(cp)
    assert "SET1" in repr(cp)
    assert str(cp) == "Test Card [SET1]"

def test_carddb_properties_and_relationships():
    Session = setup_db()
    session = Session()
    # Create set
    set1 = CardSetDB(set_code="SET1", set_name="Set One", release_date=date(2020,1,1))
    session.add(set1)
    # Create card and printings
    card = CardDB(name="Test Card")
    printing1 = CardPrintingDB(uid="p1", card_name="Test Card", set_code="SET1", card_type="Creature", rarity="rare", mana_cost="{R}", power="2", toughness="2", abilities=["Haste"], flavor_text="Fast!", text="Some rules text.", colors=["R"], color_identity=["R"])
    printing1.set = set1
    card.printings.append(printing1)
    card.newest_printing_uid = "p1"
    session.add(card)
    session.add(printing1)
    session.commit()
    # Test relationships
    assert printing1.card == card
    assert printing1.set == set1
    # Test proxy properties
    assert card.newest_printing == printing1
    assert card.type == "Creature"
    assert card.rarity == "rare"
    assert card.mana_cost == "{R}"
    assert card.power == "2"
    assert card.toughness == "2"
    assert card.abilities == ["Haste"]
    assert card.flavor_text == "Fast!"
    assert card.text == "Some rules text."
    assert card.colors == ["R"]
    session.close()

def test_carddb_newest_printing_logic():
    Session = setup_db()
    session = Session()
    set1 = CardSetDB(set_code="S1", set_name="Set1", release_date=date(2020,1,1))
    set2 = CardSetDB(set_code="S2", set_name="Set2", release_date=date(2021,1,1))
    card = CardDB(name="Test Card")
    p1 = CardPrintingDB(uid="p1", card_name="Test Card", set_code="S1")
    p1.set = set1
    p2 = CardPrintingDB(uid="p2", card_name="Test Card", set_code="S2")
    p2.set = set2
    card.printings.extend([p1, p2])
    session.add_all([set1, set2, card, p1, p2])
    session.commit()
    # Should pick p2 as newest (latest release_date)
    assert card.newest_printing == p2
    session.close()

def test_carddb_newest_printing_no_printings():
    Session = setup_db()
    session = Session()
    card = CardDB(name="Empty Card")
    session.add(card)
    session.commit()
    assert card.newest_printing is None
    session.close()

