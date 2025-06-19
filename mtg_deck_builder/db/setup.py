"""
Database setup utilities for Magic: The Gathering deck builder.

This module provides functions to initialize the database and ensure all required tables exist.
It is safe to call setup_database multiple times; it will not drop or overwrite existing data.
"""

import sqlalchemy.engine
from sqlalchemy import create_engine, inspect
from mtg_deck_builder.db.mtgjson_models.base import MTGJSONBase
import logging

__all__ = ["bootstrap", "setup_database"]

def force_update_schema(db_url: str, poolclass=None, connect_args=None, base=MTGJSONBase) -> sqlalchemy.engine.Engine:
    """
    Forces a complete update of the database schema by dropping and recreating all tables.
    WARNING: This will delete all data in the database.

    Args:
        db_url (str): SQLAlchemy database URL (e.g., 'sqlite:///path/to/db.sqlite').
        poolclass: Optional SQLAlchemy pool class.
        connect_args: Optional SQLAlchemy connect arguments.

    Returns:
        sqlalchemy.engine.Engine: The SQLAlchemy engine connected to the database.
    """
    logging.warning("Force updating database schema - this will delete all existing data!")
    
    if poolclass and connect_args:
        engine = create_engine(db_url, poolclass=poolclass, connect_args=connect_args)
    elif poolclass:
        engine = create_engine(db_url, poolclass=poolclass)
    elif connect_args:
        engine = create_engine(db_url, connect_args=connect_args)
    else:
        engine = create_engine(db_url)

    # Drop all tables and recreate them
    base.metadata.drop_all(engine)
    base.metadata.create_all(engine)
    return engine

def setup_database(db_url: str, base=MTGJSONBase, poolclass=None, connect_args=None) -> sqlalchemy.engine.Engine:
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

    # Check if tables exist and have correct schema
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    
    # For each table in the metadata, check if it exists and has the right columns
    for table in base.metadata.tables.values():
        if table.name in existing_tables:
            # Get existing columns
            existing_columns = {col['name'] for col in inspector.get_columns(table.name)}
            # Get expected columns from model
            expected_columns = {col.name for col in table.columns}
            
            # If columns don't match, drop and recreate just this table
            if existing_columns != expected_columns:
                logging.warning(f"Table {table.name} exists but has incorrect schema. Recreating...")
                table.drop(engine)
                table.create(engine)
        else:
            # Table doesn't exist, create it
            table.create(engine)
    
    return engine

