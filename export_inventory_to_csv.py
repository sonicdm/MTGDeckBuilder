#!/usr/bin/env python3
"""
Utility script to export inventory to CSV with comprehensive card information.

This script exports all cards in the inventory to a CSV file with detailed information
including color identity, legalities, text, types, and other useful fields.
"""

import csv
import logging
import sys
from typing import Dict, Any
from mtg_deck_builder.db import get_session
from mtg_deck_builder.db.repository import SummaryCardRepository
from mtg_deck_builder.models.card import SummaryCard

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def get_card_data_for_csv(card: SummaryCard) -> Dict[str, Any]:
    """Extract card data for CSV export.
    
    Args:
        card: MTGJSONSummaryCard object
        
    Returns:
        Dictionary with card data for CSV export
    """
    # Get legalities as a formatted string
    legalities_str = ""
    if card.legalities:
        legal_parts = []
        for format_name, legality in card.legalities.items():
            if legality == "Legal":
                legal_parts.append(format_name)
        legalities_str = ", ".join(sorted(legal_parts))
    
    # Get color identity as a string
    color_identity_str = ""
    if card.color_identity_list:
        color_identity_str = ", ".join(card.color_identity_list)
    
    # Get colors as a string
    colors_str = ""
    if card.colors_list:
        colors_str = ", ".join(card.colors_list)
    
    # Get types as a string
    types_str = ""
    if card.types:
        types_str = ", ".join(card.types)
    
    # Get supertypes as a string
    supertypes_str = ""
    if card.supertypes_list:
        supertypes_str = ", ".join(card.supertypes_list)
    
    # Get subtypes as a string
    subtypes_str = ""
    if card.subtypes_list:
        subtypes_str = ", ".join(card.subtypes_list)
    
    # Get keywords as a string
    keywords_str = ""
    if card.keywords_list:
        keywords_str = ", ".join(card.keywords_list)
    
    # Get printing set codes as a string
    set_codes_str = ""
    if card.printing_set_codes:
        set_codes_str = ", ".join(card.printing_set_codes)
    
    return {
        'name': card.name,
        'quantity': card.quantity,
        'rarity': card.rarity or '',
        'type_text': card.type or '',
        'types': card.types or [],
        'mana_cost': card.mana_cost or '',
        'converted_mana_cost': card.converted_mana_cost or 0,
        'power': card.power or '',
        'toughness': card.toughness or '',
        'color_identity': color_identity_str,
        'colors': colors_str,
        'types': types_str,
        'supertypes': supertypes_str,
        'subtypes': subtypes_str,
        'keywords': keywords_str,
        'legalities': legalities_str,
        'is_basic_land': card.is_basic_land(),
        'is_land': card.is_land(),
        'is_creature': card.is_creature(),
    }


def export_inventory_to_csv(output_path: str = "inventory_export.csv", 
                           min_quantity: int = 1,
                           include_zero_quantity: bool = False) -> None:
    """Export inventory to CSV with comprehensive card information.
    
    Args:
        output_path: Path to output CSV file
        min_quantity: Minimum quantity to include (default: 1)
        include_zero_quantity: Whether to include cards with 0 quantity
    """
    logger.info(f"Starting inventory export to {output_path}")
    
    with get_session() as session:
        repo = SummaryCardRepository(session)
        
        # Only export cards actually in inventory
        if not include_zero_quantity:
            repo = repo.filter_by_inventory_quantity(min_quantity)
            filtered_cards = repo.filter_cards(legal_in=["standard"]).get_all_cards()
            logger.info(f"Filtered to {len(filtered_cards)} cards with quantity >= {min_quantity}")
        else:
            filtered_cards = repo.get_all_cards()
            logger.info(f"Including all {len(filtered_cards)} cards (including zero quantity)")
        
        # Define CSV headers
        headers = [
            "name",
            "quantity",
            "rarity",
            "type_text",
            "types",
            "supertypes",
            "subtypes",
            "mana_cost",
            "converted_mana_cost",
            "power",
            "toughness",
            "color_identity",
            "colors",
            "keywords",
            "legalities",
            "is_basic_land",
            "is_land",
            "is_creature",
        ]
        
        # Write to CSV
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=headers)
            writer.writeheader()
            
            for i, card in enumerate(filtered_cards):
                if i % 1000 == 0:
                    logger.info(f"Processed {i}/{len(filtered_cards)} cards...")
                
                card_data = get_card_data_for_csv(card)
                writer.writerow(card_data)
        
        logger.info(f"Successfully exported {len(filtered_cards)} cards to {output_path}")
        
        # Print some statistics
        total_quantity = sum(card.quantity for card in filtered_cards)
        logger.info(f"Total quantity of exported cards: {total_quantity}")
        
        # Count by rarity
        rarity_counts = {}
        for card in filtered_cards:
            rarity = card.rarity or 'Unknown'
            rarity_counts[rarity] = rarity_counts.get(rarity, 0) + card.quantity
        
        logger.info("Quantity by rarity:")
        for rarity, count in sorted(rarity_counts.items()):
            logger.info(f"  {rarity}: {count}")
        
        # Count by color identity
        color_counts = {}
        for card in filtered_cards:
            if card.color_identity_list:
                color_identity = ", ".join(sorted(card.color_identity_list))
            else:
                color_identity = "Colorless"
            color_counts[color_identity] = color_counts.get(color_identity, 0) + card.quantity
        
        logger.info("Quantity by color identity:")
        for color_identity, count in sorted(color_counts.items()):
            logger.info(f"  {color_identity}: {count}")


def main():
    """Main function to handle command line arguments and run the export."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Export inventory to CSV with comprehensive card information"
    )
    parser.add_argument(
        "-o", "--output", 
        default="inventory_export.csv",
        help="Output CSV file path (default: inventory_export.csv)"
    )
    parser.add_argument(
        "-m", "--min-quantity",
        type=int,
        default=1,
        help="Minimum quantity to include (default: 1)"
    )
    parser.add_argument(
        "--include-zero",
        action="store_true",
        help="Include cards with 0 quantity"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        export_inventory_to_csv(
            output_path=args.output,
            min_quantity=args.min_quantity,
            include_zero_quantity=args.include_zero
        )
        logger.info("Export completed successfully!")
        
    except Exception as e:
        logger.error(f"Export failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 