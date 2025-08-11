"""
Script to update the database schema.
This will create any missing tables, but won't drop existing data.
"""

import logging
from pathlib import Path
from mtg_deck_builder.db.mtgjson_models.base import MTGJSONBase

logger = logging.getLogger(__name__)

def update_schema(db_path: Path):
    """Update database schema."""
    from sqlalchemy import create_engine
    
    db_url = f"sqlite:///{db_path}"
    engine = create_engine(db_url)
    
    # Create all tables
    MTGJSONBase.metadata.create_all(engine)
    
    logger.info(f"Schema updated for {db_path}")
    
    return engine

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
    
    # Use default database path
    db_path = Path("AllPrintings.sqlite")
    
    try:
        # Update the schema
        logging.info("Updating database schema...")
        update_schema(db_path)
        
        logging.info("Database schema update complete!")
    except Exception as e:
        logging.error(f"Error updating database schema: {e}")
        exit(1)

 