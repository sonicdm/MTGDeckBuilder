from sqlalchemy import create_engine
from mtg_deck_builder.db.models import Base

def setup_database(db_url: str, poolclass=None, connect_args=None):
    if poolclass and connect_args:
        engine = create_engine(db_url, poolclass=poolclass, connect_args=connect_args)
    elif poolclass:
        engine = create_engine(db_url, poolclass=poolclass)
    elif connect_args:
        engine = create_engine(db_url, connect_args=connect_args)
    else:
        engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    return engine
