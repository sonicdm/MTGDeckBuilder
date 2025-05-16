from mtg_deck_builder.db.models import InventoryItemDB, CardDB, CardSetDB, ImportLog, Base

def get_session():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine("sqlite:///cards.db")
    Session = sessionmaker(bind=engine)
    return Session()