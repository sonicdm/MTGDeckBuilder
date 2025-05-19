from mtg_deck_builder.db.models import InventoryItemDB, CardDB, CardSetDB, ImportLog, Base

def get_session(db_url: str = "sqlite:///cards.db"):
    """
    :param db_url:
    :return:
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    return Session()