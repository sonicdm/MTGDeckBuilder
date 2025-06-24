"""
Arena deck creation utilities.

This module provides functions for creating Deck objects from Arena import text.
Separated from arena_parser.py to avoid circular imports.
"""

import logging
from typing import Dict, Optional, List, Tuple, Any
from mtg_deck_builder.db import get_session
from mtg_deck_builder.db.repository import SummaryCardRepository
from mtg_deck_builder.models.deck import Deck
from mtg_deck_builder.utils.arena_parser import parse_arena_export

logger = logging.getLogger(__name__)

# Format rules (can be expanded)
FORMAT_RULES = {
    "standard": {"min_size": 60, "max_size": 250, "max_copies": 4, "banned": set()},
    "alchemy": {"min_size": 60, "max_size": 250, "max_copies": 4, "banned": set()},
    "historic": {"min_size": 60, "max_size": 250, "max_copies": 4, "banned": set()},
    "brawl": {"min_size": 100, "max_size": 100, "max_copies": 1, "banned": set()},  # Historic Brawl
    "standardbrawl": {"min_size": 60, "max_size": 60, "max_copies": 1, "banned": set()},  # Standard Brawl
    "pauper": {"min_size": 60, "max_size": 250, "max_copies": 4, "banned": set()},
    "commander": {"min_size": 100, "max_size": 100, "max_copies": 1, "banned": set()},
    "pioneer": {"min_size": 60, "max_copies": 4, "banned": set()},
    "modern": {"min_size": 60, "max_copies": 4, "banned": set()},
    "legacy": {"min_size": 60, "max_copies": 4, "banned": set()},
    "vintage": {"min_size": 60, "max_copies": 4, "banned": set()},
    # Add more formats as needed
}

def create_deck_from_arena_import(
    arena_text: str, 
    deck_name: str = "Imported Deck",
    session = None,
    format: Optional[str] = None
) -> Optional[Deck]:
    """
    Create a Deck object from MTG Arena export text.
    
    Args:
        arena_text: Arena export text
        deck_name: Name for the deck
        session: Database session (optional)
        format: Format to validate legality (e.g., "standard", "alchemy")
        
    Returns:
        Deck object if successful, None otherwise
    """
    try:
        arena_lines = arena_text.strip().split('\n')
        parsed_result = parse_arena_export(arena_lines)
        card_quantities = parsed_result['main']
        if not card_quantities:
            logger.error("No cards found in Arena export")
            return None
        if session is None:
            with get_session() as session:
                return _create_deck_with_session(card_quantities, deck_name, session, format)
        else:
            return _create_deck_with_session(card_quantities, deck_name, session, format)
    except Exception as e:
        logger.error(f"Error creating deck from Arena import: {e}", exc_info=True)
        return None

def _create_deck_with_session(
    card_quantities: Dict[str, int],
    deck_name: str,
    session,
    format: Optional[str] = None
) -> Optional[Deck]:
    try:
        repo = SummaryCardRepository(session)
        deck_cards = {}
        missing_cards = []
        found_cards = 0
        illegal_cards = []
        
        for card_name, quantity in card_quantities.items():
            card = repo.find_by_name(card_name)
            # If not found, try searching for it as part of a DFC
            if not card:
                card = repo.find_by_name(card_name, exact=False)

            if card:
                # Check legality if format specified
                if format and hasattr(card, "is_legal_in") and not card.is_legal_in(format):
                    illegal_cards.append(card_name)
                    logger.warning(f"Card {card_name} is not legal in {format}")
                    continue
                deck_cards[card_name] = card
                found_cards += 1
                logger.debug(f"Found card: {card_name} (quantity: {quantity})")
            else:
                missing_cards.append(card_name)
                logger.warning(f"Card not found in database: {card_name}")
        
        # Create deck even if some cards are missing
        if not deck_cards:
            logger.error("No cards from Arena import found in database")
            return None
            
        deck = Deck(cards=deck_cards, name=deck_name, session=session)
        
        # Set the quantities for found cards
        for card_name, quantity in card_quantities.items():
            if card_name in deck_cards:
                deck.inventory[card_name] = quantity
        
        logger.info(f"Successfully created deck '{deck_name}' with {found_cards} cards")
        if missing_cards:
            logger.warning(f"Missing cards: {', '.join(missing_cards)}")
        if illegal_cards:
            logger.warning(f"Illegal cards for {format}: {', '.join(illegal_cards)}")
            
        return deck
    except Exception as e:
        logger.error(f"Error creating deck with session: {e}", exc_info=True)
        return None

def validate_arena_import_with_database(
    arena_text: str,
    format: Optional[str] = None
) -> Tuple[bool, List[str]]:
    """
    Validate Arena import text and check if cards exist in database and are legal in the specified format.
    
    Args:
        arena_text: Arena export text to validate
        format: Format to validate legality (e.g., "standard", "alchemy")
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    from mtg_deck_builder.utils.arena_parser import validate_arena_import
    is_valid, errors = validate_arena_import(arena_text)
    if not is_valid:
        return False, errors
    arena_lines = arena_text.strip().split('\n')
    parsed_result = parse_arena_export(arena_lines)
    card_quantities = parsed_result['main']
    try:
        with get_session() as session:
            repo = SummaryCardRepository(session)
            missing_cards = []
            illegal_cards = []
            banned_cards = []
            format_rules = FORMAT_RULES.get(format.lower(), FORMAT_RULES["standard"]) if format else None
            for card_name in card_quantities.keys():
                card = repo.find_by_name(card_name)
                if not card:
                    missing_cards.append(card_name)
                else:
                    # Check legality
                    if format and hasattr(card, "is_legal_in") and not card.is_legal_in(format):
                        illegal_cards.append(card_name)
                    # Check banlist
                    if format_rules and card_name in format_rules["banned"]:
                        banned_cards.append(card_name)
            if missing_cards:
                errors.append(f"Cards not found in database: {', '.join(missing_cards)}")
            if illegal_cards:
                errors.append(f"Illegal in {format}: {', '.join(illegal_cards)}")
            if banned_cards:
                errors.append(f"Banned in {format}: {', '.join(banned_cards)}")
            # Deck size and max copies (excluding lands)
            if format_rules:
                total_cards = sum(card_quantities.values())
                # Deck size validation
                if "min_size" in format_rules and total_cards < format_rules["min_size"]:
                    errors.append(f"Deck too small: {total_cards} cards (minimum {format_rules['min_size']})")
                if "max_size" in format_rules and total_cards > format_rules["max_size"]:
                    errors.append(f"Deck too large: {total_cards} cards (maximum {format_rules['max_size']})")
                
                # Max copies validation
                for card_name, quantity in card_quantities.items():
                    # Skip basic land quantity checks
                    if card_name in ['Plains', 'Island', 'Swamp', 'Mountain', 'Forest', 'Snow-Covered Plains', 'Snow-Covered Island', 'Snow-Covered Swamp', 'Snow-Covered Mountain', 'Snow-Covered Forest']:
                        continue
                    
                    if quantity > format_rules["max_copies"]:
                        errors.append(f"Too many copies of {card_name}: {quantity} (maximum {format_rules['max_copies']})")
    except Exception as e:
        logger.error(f"Database validation failed: {str(e)}", exc_info=True)
        errors.append(f"Database validation failed: {str(e)}")
    return len(errors) == 0, errors 

def validate_arena_deck(
    deck_text: str,
    format: Optional[str] = None,
    session=None
) -> Dict[str, Any]:
    """
    Validate an Arena deck export and provide detailed analysis.
    
    Args:
        deck_text: Arena deck export text
        format: Format to validate against (e.g., 'standard', 'commander')
        session: Database session (optional)
        
    Returns:
        Dictionary with validation results and deck analysis
    """
    try:
        # Parse the deck
        deck_lines = deck_text.strip().split('\n')
        parsed_result = parse_arena_export(deck_lines)
        card_quantities = parsed_result['main']
        if not card_quantities:
            return {
                "success": False,
                "error": "Failed to parse Arena deck export"
            }
        
        # Create deck object
        deck_name = "Arena Import"
        deck = _create_deck_with_session(card_quantities, deck_name, session, format)
        
        if not deck:
            return {
                "success": False,
                "error": "Failed to create deck object"
            }
        
        # Get basic statistics
        total_cards = sum(card_quantities.values())
        unique_cards = len(card_quantities)
        avg_copies = total_cards / unique_cards if unique_cards > 0 else 0
        
        # Count found vs missing cards
        found_cards = len(deck.cards)
        missing_cards = [name for name in card_quantities.keys() if name not in deck.cards]
        
        # Validate format if specified
        format_errors = []
        if format:
            format_errors = validate_deck_format(deck, format)
        
        # Analyze deck composition
        deck_analysis = {}
        if deck.cards:  # Only analyze if we have cards
            deck_analysis = analyze_deck_composition(deck)
        
        return {
            "success": True,
            "deck": deck,
            "statistics": {
                "total_cards": total_cards,
                "unique_cards": unique_cards,
                "avg_copies": avg_copies,
                "found_cards": found_cards,
                "missing_cards": len(missing_cards)
            },
            "missing_cards": missing_cards,
            "format_errors": format_errors,
            "deck_analysis": deck_analysis,
            "is_valid": len(format_errors) == 0 if format else None
        }
        
    except Exception as e:
        logger.error(f"Error validating Arena deck: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        } 

def validate_deck_format(deck: Deck, format: str) -> List[str]:
    """
    Validate a deck against a specific format's rules.
    
    Args:
        deck: Deck object to validate
        format: Format to validate against
        
    Returns:
        List of validation errors
    """
    errors = []
    
    total_cards = sum(deck.inventory.values())
    
    if format.lower() == "commander":
        if total_cards != 100:
            errors.append(f"Commander deck must have exactly 100 cards, got {total_cards}")
        
        for card_name, quantity in deck.inventory.items():
            card = deck.cards.get(card_name)
            is_basic = False
            if card and hasattr(card, 'supertypes') and 'Basic' in (card.supertypes or []):
                is_basic = True

            if not is_basic and quantity > 1:
                errors.append(f"Too many copies of {card_name}: {quantity} (maximum 1 in Commander)")
                
    elif format.lower() in ["standard", "alchemy", "pioneer", "modern", "legacy", "historic"]:
        if total_cards < 60:
            errors.append(f"{format.title()} deck must have at least 60 cards, got {total_cards}")
        
        for card_name, quantity in deck.inventory.items():
            card = deck.cards.get(card_name)
            is_basic = False
            if card and hasattr(card, 'supertypes') and 'Basic' in (card.supertypes or []):
                is_basic = True

            if not is_basic and quantity > 4:
                errors.append(f"Too many copies of {card_name}: {quantity} (maximum 4)")
    
    return errors

def analyze_deck_composition(deck: Deck) -> Dict[str, Any]:
    """
    Analyze the composition of a deck.
    
    Args:
        deck: Deck object to analyze
        
    Returns:
        Dictionary with deck analysis data
    """
    if not deck or not deck.inventory:
        return {}

    analysis = {
        "mana_curve": {},
        "color_distribution": {},
        "type_distribution": {},
        "rarity_distribution": {},
        "land_analysis": {}
    }
    
    total_cards = sum(deck.inventory.values())

    # Mana curve analysis
    for card_name, quantity in deck.inventory.items():
        card = deck.cards.get(card_name)
        if card and hasattr(card, 'mana_value'):
            cmc = card.mana_value or 0
            if hasattr(card, 'types') and 'Land' not in (card.types or []):
                 analysis["mana_curve"][cmc] = analysis["mana_curve"].get(cmc, 0) + quantity
    
    # Color distribution
    for card_name, quantity in deck.inventory.items():
        card = deck.cards.get(card_name)
        if card and hasattr(card, 'colors'):
            colors = card.colors or []
            if hasattr(card, 'types') and 'Land' in (card.types or []):
                continue
            if not colors:  # Colorless
                analysis["color_distribution"]["Colorless"] = analysis["color_distribution"].get("Colorless", 0) + quantity
            else:
                for color in colors:
                    color_name = {"W": "White", "U": "Blue", "B": "Black", "R": "Red", "G": "Green"}.get(color, color)
                    analysis["color_distribution"][color_name] = analysis["color_distribution"].get(color_name, 0) + quantity
    
    # Type distribution
    for card_name, quantity in deck.inventory.items():
        card = deck.cards.get(card_name)
        if card and hasattr(card, 'types'):
            types = card.types or []
            # Use main type (e.g. Creature, Sorcery)
            main_type = types[0] if types else "Unknown"
            analysis["type_distribution"][main_type] = analysis["type_distribution"].get(main_type, 0) + quantity
    
    # Rarity distribution
    for card_name, quantity in deck.inventory.items():
        card = deck.cards.get(card_name)
        if card and hasattr(card, 'rarity'):
            rarity = card.rarity or "Unknown"
            analysis["rarity_distribution"][rarity.capitalize()] = analysis["rarity_distribution"].get(rarity.capitalize(), 0) + quantity
    
    # Land analysis
    land_count = 0
    basic_lands = {}
    non_basic_lands = {}
    
    for card_name, quantity in deck.inventory.items():
        card = deck.cards.get(card_name)
        if card and hasattr(card, 'types') and "Land" in (card.types or []):
            land_count += quantity
            is_basic = False
            if hasattr(card, 'supertypes') and 'Basic' in (card.supertypes or []):
                is_basic = True
            
            if is_basic:
                basic_lands[card_name] = basic_lands.get(card_name, 0) + quantity
            else:
                non_basic_lands[card_name] = non_basic_lands.get(card_name, 0) + quantity
    
    analysis["land_analysis"] = {
        "total_lands": land_count,
        "basic_lands": basic_lands,
        "non_basic_lands": non_basic_lands,
        "land_percentage": (land_count / total_cards) * 100 if total_cards > 0 else 0
    }
    
    return analysis 