"""
Script to force update the database schema.
This will drop and recreate all tables, so use with caution!
"""

import logging
from mtg_deck_builder.db.setup import force_update_schema
from mtg_deck_builder.db.bootstrap import bootstrap
import os
import sys

def main():
    # Configure logging
    logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
    
    # Get the database URL from environment or use default
    db_url = os.getenv('MTG_DB_URL', 'sqlite:///cards.db')
    
    # Get the JSON data path from environment or use default
    json_path = os.getenv('MTG_JSON_PATH', 'data/cards.json')
    
    if not os.path.exists(json_path):
        logging.error(f"JSON data file not found: {json_path}")
        sys.exit(1)
    
    try:
        # Force update the schema
        logging.info("Updating database schema...")
        force_update_schema(db_url)
        
        # Re-bootstrap the database with card data
        logging.info("Re-bootstrapping database with card data...")
        bootstrap(json_path, db_url=db_url)
        
        logging.info("Database schema update complete!")
    except Exception as e:
        logging.error(f"Error updating database schema: {e}")
        sys.exit(1)

 