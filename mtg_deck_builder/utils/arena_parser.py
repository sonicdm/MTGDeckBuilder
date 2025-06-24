from collections import defaultdict
import re
import logging
from typing import List, Dict, Optional, Tuple, Sequence

logger = logging.getLogger(__name__)


def parse_arena_export_line(line: str) -> Optional[Tuple[int, str]]:
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


def parse_arena_export(deck_lines: Sequence[str]) -> dict:
    """
    Parse a decklist from MTG Arena export format.
    Returns a dict with 'main', 'sideboard', and 'deck_name' if present.
    
    Args:
        deck_lines: Sequence of lines from the Arena export
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


def validate_arena_import(text: str) -> Tuple[bool, List[str]]:
    """
    Basic validation of Arena export text for format correctness.
    Does not check against database.
    
    Args:
        text: Arena export text
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    lines = text.strip().split('\n')
    
    if not any(line.strip() for line in lines):
        errors.append("Decklist is empty or contains only whitespace.")
    
    for i, line in enumerate(lines, 1):
        line = line.strip()
        if not line:
            continue
        
        # Keywords are allowed
        if line.lower() in ["deck", "commander", "sideboard", "companion"]:
            continue
            
        # Check for quantity and name
        if not re.match(r"^\d+\s+.+", line):
            errors.append(f"Line {i} does not match 'QTY CARD_NAME' format: '{line}'")
            
    return len(errors) == 0, errors


def validate_arena_import_for_format(deck_text: str, format_name: str, format_rules: dict) -> Tuple[bool, List[str]]:
    """
    Validate Arena deck import for a specific format (e.g., commander, standard).
    Returns (is_valid, list_of_errors)
    """
    errors = []
    deck_lines = deck_text.strip().split('\n')
    parsed_result = parse_arena_export(deck_lines)
    card_quantities = parsed_result['main']
    if not card_quantities:
        errors.append("No valid cards found in Arena export.")
        return False, errors

    total_cards = sum(card_quantities.values())
    rules = format_rules.get(format_name.lower())
    if not rules:
        errors.append(f"Unknown format '{format_name}'.")
        return False, errors

    # Deck size
    if "min_size" in rules and total_cards < rules["min_size"]:
        errors.append(f"Deck has {total_cards} cards, format minimum is {rules['min_size']}.")
    if "max_size" in rules and total_cards > rules["max_size"]:
        errors.append(f"Deck has {total_cards} cards, format maximum is {rules['max_size']}.")

    # Card copies
    for name, quantity in card_quantities.items():
        is_basic_land = name in [
            'Plains', 'Island', 'Swamp', 'Mountain', 'Forest',
            'Snow-Covered Plains', 'Snow-Covered Island', 'Snow-Covered Swamp',
            'Snow-Covered Mountain', 'Snow-Covered Forest', 'Wastes'
        ]
        if not is_basic_land and "max_copies" in rules and quantity > rules["max_copies"]:
            errors.append(f"Too many copies of '{name}' ({quantity}), max is {rules['max_copies']}.")

    return (len(errors) == 0), errors