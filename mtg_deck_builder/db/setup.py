"""
Database setup utilities for Magic: The Gathering deck builder.

This module provides functions to initialize the database and ensure all required tables exist.
It is safe to call setup_database multiple times; it will not drop or overwrite existing data.
"""

import sqlalchemy.engine
from sqlalchemy import create_engine
from mtg_deck_builder.db.models import Base

def setup_database(db_url: str, poolclass=None, connect_args=None) -> sqlalchemy.engine.Engine:
    """
    Ensures all tables exist in the database specified by db_url.

    This function creates any missing tables defined in the ORM models.
    It does NOT drop or destroy existing tables or data.
    Safe to call multiple times, including in production or test environments.

    Args:
        db_url (str): SQLAlchemy database URL (e.g., 'sqlite:///path/to/db.sqlite').
        poolclass: Optional SQLAlchemy pool class.
        connect_args: Optional SQLAlchemy connect arguments.

    Returns:
        sqlalchemy.engine.Engine: The SQLAlchemy engine connected to the database.
    """
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

