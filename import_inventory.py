#!/usr/bin/env python3
"""
Inventory Import Script

This script imports a Magic: The Gathering inventory file into the MTGJSON database.
It supports Arena export format and simple "quantity cardname" format.

Usage:
    python import_inventory.py <inventory_file> [--db-path <database_path>]

Options:
    --db-path    Path to the MTGJSON database (default: data/mtgjson/AllPrintings.sqlite)
"""

import os
import sys
import logging
import argparse
from pathlib import Path
from typing import Optional, Dict, List
from collections import defaultdict
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Default database path
DEFAULT_DB_PATH = "data/mtgjson/AllPrintings.sqlite"

def parse_arena_export_line(line: str) -> Optional[tuple[int, str]]:
    """
    Parses a single line from an Arena export file.
    Returns quantity and card name, or None if parsing fails.
    A line without a leading number is treated as a section header and skipped.
    """
    line = line.strip()
    if not line:
        return None

    # If the line does not start with a number, it's a section header and should be skipped.
    if not re.match(r'^\d', line):
        logger.debug(f"Skipping header line: {line}")
        return None

    # Strip set and collector number info, e.g., " (M21) 193"
    # This makes parsing the name much more reliable.
    card_part = re.sub(r'\s*\([\w\d]+\)\s+[\w\d]+$', '', line).strip()

    # Extract quantity and name from the remaining string
    match = re.match(r'^(\d+)\s+(.*)', card_part)
    if not match:
        logger.warning(f"Could not extract quantity and name from: '{card_part}' (original: '{line}')")
        return None

    quantity = int(match.group(1))
    name_part = match.group(2).strip()

    # Handle double-faced cards by taking the front face
    card_name = name_part.split('//')[0].strip()

    return quantity, card_name

def parse_arena_export(deck_lines: list[str]) -> dict:
    """
    Parse a decklist from MTG Arena export format.
    Returns a dict with 'main', 'sideboard', and 'deck_name' if present.
    
    Args:
        deck_lines: List of lines from the Arena export
    """
    card_quantities = defaultdict(int)
    sideboard_quantities = defaultdict(int)
    deck_name = None
    in_sideboard = False

    for idx, line in enumerate(deck_lines):
        line = line.strip()
        # Deck name extraction (About/Name header)
        if line.lower() == 'about' and idx + 1 < len(deck_lines):
            next_line = deck_lines[idx + 1].strip()
            if next_line.lower().startswith('name '):
                deck_name = next_line[5:].strip()
            continue
        if line.lower().startswith('name '):
            deck_name = line[5:].strip()
            continue
        # Sideboard detection
        if line.lower() == 'sideboard':
            in_sideboard = True
            continue
        # Only process lines that start with a number and a space
        if not re.match(r'^\d+\s', line):
            continue
        # Remove set/collector info (e.g., (GRN) 153)
        card_part = re.sub(r'\s*\([\w\d]+\)\s+[\w\d]+$', '', line).strip()
        match = re.match(r'^(\d+)\s+(.*)', card_part)
        if not match:
            continue
        quantity = int(match.group(1))
        card_name = match.group(2).strip()
        if in_sideboard:
            sideboard_quantities[card_name] += quantity
        else:
            card_quantities[card_name] += quantity

    return {
        'main': dict(card_quantities),
        'sideboard': dict(sideboard_quantities) if sideboard_quantities else None,
        'deck_name': deck_name
    }

def parse_simple_inventory(deck_lines: list[str]) -> dict:
    """
    Parse a simple inventory format (quantity cardname).
    Returns a dict with 'main' containing card quantities.
    
    Args:
        deck_lines: List of lines from the inventory file
    """
    card_quantities = defaultdict(int)
    
    for line in deck_lines:
        line = line.strip()
        if not line:
            continue
            
        # Try to match "quantity cardname" format
        match = re.match(r'^(\d+)\s+(.+)$', line)
        if match:
            quantity = int(match.group(1))
            card_name = match.group(2).strip()
            card_quantities[card_name] += quantity
        else:
            logger.warning(f"Could not parse line: {line}")
    
    return {
        'main': dict(card_quantities),
        'sideboard': None,
        'deck_name': None
    }

def detect_inventory_format(lines: list[str]) -> str:
    """
    Detect the format of the inventory file.
    Returns 'arena' or 'simple'.
    """
    arena_indicators = ['sideboard', 'about', 'name']
    simple_indicators = 0
    
    for line in lines:
        line_lower = line.strip().lower()
        if any(indicator in line_lower for indicator in arena_indicators):
            return 'arena'
        # Check for simple format (number followed by card name)
        if re.match(r'^\d+\s+[A-Za-z]', line):
            simple_indicators += 1
    
    # If we have mostly simple format lines, assume simple format
    if simple_indicators > len(lines) * 0.8:
        return 'simple'
    
    # Default to arena format
    return 'arena'

def load_inventory_items(inventory_file: str, db_path: str) -> None:
    """
    Take card inventory and load it into the database.
    
    Args:
        inventory_file: Path to the inventory file
        db_path: Path to the MTGJSON database
    """
    logger.info(f"Loading inventory items from {inventory_file}")
    
    # Read inventory file
    inventory_file_path = Path(inventory_file)
    with inventory_file_path.open("r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]
    
    # Detect format and parse
    format_type = detect_inventory_format(lines)
    logger.info(f"Detected inventory format: {format_type}")
    
    if format_type == 'arena':
        inventory_dict = parse_arena_export(lines)
    else:
        inventory_dict = parse_simple_inventory(lines)
    
    # Import into database
    try:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from mtg_deck_builder.db.mtgjson_models.base import MTGJSONBase
        from mtg_deck_builder.db.inventory import InventoryItem
        
        # Create database engine and session
        engine = create_engine(f"sqlite:///{db_path}")
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Ensure tables exist
        MTGJSONBase.metadata.create_all(engine)
        
        # Delete all existing inventory items
        session.query(InventoryItem).delete()
        
        # Add new inventory items
        total_cards = 0
        for card_name, quantity in inventory_dict['main'].items():
            # Quantity should be no more than 4
            if quantity > 4:
                logger.warning(
                    f"Quantity for {card_name} is {quantity}, which is greater than 4"
                )
            quantity = min(quantity, 4)
            session.add(InventoryItem(card_name=card_name, quantity=quantity))
            total_cards += quantity
        
        # Commit the changes
        session.commit()
        session.close()
        
        logger.info(
            f"Loaded {len(inventory_dict['main'])} inventory items for {total_cards} cards"
        )
        
        print(f"✅ Successfully imported {len(inventory_dict['main'])} unique cards ({total_cards} total)")
        
    except ImportError as e:
        logger.error(f"Failed to import required modules: {e}")
        print(f"❌ Error: Could not import required database modules. Make sure mtg_deck_builder is installed.")
        raise
    except Exception as e:
        logger.error(f"Failed to load inventory: {e}")
        print(f"❌ Error: Failed to load inventory: {e}")
        raise

def main():
    parser = argparse.ArgumentParser(description="Import MTG inventory file into the database.")
    parser.add_argument("inventory_file", help="Path to the inventory file")
    parser.add_argument("--db-path", default=DEFAULT_DB_PATH, 
                       help=f"Path to the MTGJSON database (default: {DEFAULT_DB_PATH})")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Validate inputs
    inventory_path = Path(args.inventory_file)
    if not inventory_path.exists():
        print(f"❌ Error: Inventory file not found: {inventory_path}")
        sys.exit(1)
    
    db_path = Path(args.db_path)
    if not db_path.exists():
        print(f"❌ Error: Database file not found: {db_path}")
        print(f"   Make sure to run update_mtgjson.py first to download the database.")
        sys.exit(1)
    
    try:
        print(f"Starting inventory import from {inventory_path}...")
        load_inventory_items(str(inventory_path), str(db_path))
        print("✅ Inventory import completed successfully!")
        
    except Exception as e:
        logger.error(f"Inventory import failed: {e}")
        print(f"❌ Inventory import failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
