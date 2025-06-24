#!/usr/bin/env python3
"""
Test script for Arena import functionality.
"""

import logging
from mtg_deck_builder.utils.arena_parser import (
    parse_arena_export,
    validate_arena_import
)
from mtg_deck_builder.utils.arena_deck_creator import (
    create_deck_from_arena_import,
    validate_arena_import_with_database
)

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_arena_import():
    """Test Arena import functionality."""
    
    # Sample Arena export text
    arena_text = """2 Lightning Bolt
4 Llanowar Elves
3 Forest
2 Mountain
1 Island
1 Swamp
1 Plains
2 Giant Growth
1 Fireball
1 Counterspell
1 Dark Ritual
1 Healing Salve"""
    
    print("Testing Arena import functionality...")
    print("=" * 50)
    
    # Test 1: Parse Arena export
    print("\n1. Testing Arena export parsing:")
    arena_lines = arena_text.strip().split('\n')
    parsed_result = parse_arena_export(arena_lines)
    card_quantities = parsed_result['main']
    print(f"Parsed {len(card_quantities)} unique cards:")
    for card_name, quantity in card_quantities.items():
        print(f"  {quantity}x {card_name}")
    
    # Test 2: Validate Arena import (basic)
    print("\n2. Testing basic Arena import validation:")
    is_valid, errors = validate_arena_import(arena_text)
    if is_valid:
        print("✅ Arena import is valid")
    else:
        print("❌ Arena import validation failed:")
        for error in errors:
            print(f"  - {error}")
    
    # Test 3: Validate Arena import (with database)
    print("\n3. Testing Arena import validation with database:")
    is_valid, errors = validate_arena_import_with_database(arena_text)
    if is_valid:
        print("✅ Arena import is valid and all cards found in database")
    else:
        print("❌ Arena import validation failed:")
        for error in errors:
            print(f"  - {error}")
    
    # Test 4: Create deck from Arena import
    print("\n4. Testing deck creation from Arena import:")
    deck = create_deck_from_arena_import(arena_text, "Test Arena Deck")
    if deck:
        print(f"✅ Successfully created deck: {deck.name}")
        print(f"   Total cards: {deck.size()}")
        print(f"   Unique cards: {len(deck.cards)}")
        print("   Cards in deck:")
        for card_name, quantity in deck.inventory.items():
            print(f"     {quantity}x {card_name}")
    else:
        print("❌ Failed to create deck from Arena import")
    
    # Test 5: Test with invalid input
    print("\n5. Testing with invalid input:")
    invalid_text = "This is not a valid Arena export"
    is_valid, errors = validate_arena_import(invalid_text)
    if not is_valid:
        print("✅ Correctly rejected invalid input:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("❌ Should have rejected invalid input")
    
    print("\n" + "=" * 50)
    print("Arena import testing complete!")

if __name__ == "__main__":
    test_arena_import() 