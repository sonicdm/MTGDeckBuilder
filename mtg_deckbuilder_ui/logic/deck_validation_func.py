# mtg_deckbuilder_ui/logic/deck_validation_func.py

"""
deck_validation_func.py

Provides deck validation functionality for the MTG Deckbuilder application.
This module integrates the validation logic from validate_arena_import.py into the UI.
"""

import logging
from typing import Dict, List, Tuple, Optional, Any
from collections import defaultdict
import gradio as gr
import pandas as pd

from mtg_deck_builder.db.mtgjson_models.inventory import load_inventory_items
from mtg_deck_builder.db.mtgjson_models.cards import MTGJSONSummaryCard
from mtg_deck_builder.utils.arena_parser import parse_arena_export
from mtg_deck_builder.db import get_session
from mtg_deck_builder.db.repository import SummaryCardRepository
from mtg_deck_builder.models.deck import Deck
from mtg_deck_builder.utils.arena_deck_creator import FORMAT_RULES
from mtg_deck_builder.models.deck_analyzer import DeckAnalyzer
from mtg_deckbuilder_ui.app_config import app_config

logger = logging.getLogger(__name__)

BASIC_LANDS = {
    'Plains', 'Island', 'Swamp', 'Mountain', 'Forest',
    'Snow-Covered Plains', 'Snow-Covered Island', 'Snow-Covered Swamp',
    'Snow-Covered Mountain', 'Snow-Covered Forest', 'Wastes'
}


def get_owned_qty(card: Optional[MTGJSONSummaryCard], name: str) -> int:
    """Get the owned quantity of a card."""
    if name in BASIC_LANDS:
        return 99999999
    try:
        return int(getattr(card, "owned_qty", 0))
    except Exception:
        return 0


def validate_deck_format(
    arena_text: str,
    format_name: str = "standard",
    inventory_file: Optional[str] = None,
    owned_only: bool = False
) -> Dict[str, Any]:
    """
    Validate an Arena deck import against a specified format.
    
    Args:
        arena_text: Arena deck export text
        format_name: Format to validate against
        inventory_file: Path to inventory file
        owned_only: Whether to only allow owned cards
        
    Returns:
        Dictionary containing validation results
    """
    try:
        if not arena_text or not arena_text.strip():
            return {
                "valid": False,
                "errors": ["No deck text provided"],
                "warnings": [],
                "summary": {},
                "card_status": [],
                "deck_analysis": None
            }

        # Parse Arena text
        arena_lines = arena_text.strip().split('\n')
        parsed = parse_arena_export(arena_lines)
        card_quantities = parsed['main']
        sideboard_quantities = parsed.get('sideboard', {})
        deck_name = parsed.get('deck_name') or "Imported Deck"
        
        if not card_quantities:
            return {
                "valid": False,
                "errors": ["No valid cards found in Arena export"],
                "warnings": [],
                "summary": {},
                "card_status": [],
                "deck_analysis": None
            }

        # Use default inventory file if not specified
        if not inventory_file:
            try:
                inventory_file = str(app_config.get_path("inventory_dir"))
            except (KeyError, Exception):
                # Fallback to default path if config doesn't have inventory_dir
                inventory_file = "inventory_files/card inventory.txt"

        # Validate in database session
        with get_session() as session:
            # Load inventory if specified
            if inventory_file:
                load_inventory_items(inventory_file, session)
            
            repo = SummaryCardRepository(session)
            
            # Look up cards
            found_cards_map = {}
            missing_cards = []
            for name in card_quantities:
                card = repo.find_by_name(name, exact=False)
                if card:
                    found_cards_map[name] = card
                else:
                    missing_cards.append(name)

            # Validate format rules
            errors = []
            warnings = []
            illegal_cards = []
            
            rules = FORMAT_RULES.get(format_name.lower())
            if not rules:
                errors.append(f"Unknown format '{format_name}'")
            else:
                # Deck size validation
                total_cards = sum(card_quantities.values())
                if "min_size" in rules and total_cards < rules["min_size"]:
                    errors.append(f"Deck has {total_cards} cards, format minimum is {rules['min_size']}")
                if "max_size" in rules and total_cards > rules["max_size"]:
                    errors.append(f"Deck has {total_cards} cards, format maximum is {rules['max_size']}")

                # Card validation
                for name, quantity in card_quantities.items():
                    card = found_cards_map.get(name)
                    is_basic_land = name in BASIC_LANDS
                    owned = get_owned_qty(card, name) if card else 0
                    
                    # Copy limit validation
                    if not is_basic_land and quantity > rules['max_copies']:
                        errors.append(f"Too many copies of '{name}' ({quantity}), max is {rules['max_copies']}")

                    # Format legality
                    if card and hasattr(card, 'is_legal_in') and not card.is_legal_in(format_name):
                        errors.append(f"'{name}' is not legal in {format_name}")
                        illegal_cards.append(name)

                    # Ownership validation
                    if owned_only and not is_basic_land and owned < quantity:
                        errors.append(f"Not enough owned copies of '{name}': need {quantity}, have {owned}")

            # Create card status report
            card_status = []
            for name in sorted(card_quantities.keys()):
                quantity = card_quantities[name]
                card = found_cards_map.get(name)
                owned = get_owned_qty(card, name) if card else 0
                is_basic_land = name in BASIC_LANDS
                
                status = "❌ Not Found"
                reason = "Not in database"
                
                if card:
                    if name in illegal_cards:
                        status = "⚠️ Illegal"
                        reason = f"Not legal in {format_name}"
                    elif owned_only and not is_basic_land and owned < quantity:
                        status = "❌ Not enough copies"
                        reason = f"Need {quantity}, have {owned}"
                    else:
                        status = "✅ Found"
                        reason = ""
                
                card_status.append({
                    "name": name,
                    "quantity": quantity,
                    "status": status,
                    "reason": reason,
                    "owned": owned if not is_basic_land else "∞"
                })

            # Create deck analysis if we have valid cards
            deck_analysis = None
            if found_cards_map and not errors:
                # Create deck object for analysis
                deck = Deck(name=deck_name)
                for name, card_obj in found_cards_map.items():
                    if name not in illegal_cards:  # Exclude illegal cards from analysis
                        deck.insert_card(card_obj, card_quantities[name])
                
                if deck.cards:
                    analyzer = DeckAnalyzer(deck)
                    deck_analysis = analyzer.summary_dict()

            # Create summary
            summary = {
                "deck_name": deck_name,
                "total_cards": sum(card_quantities.values()),
                "unique_cards": len(card_quantities),
                "found_cards": len(found_cards_map),
                "missing_cards": len(missing_cards),
                "illegal_cards": len(illegal_cards),
                "sideboard_cards": sum(sideboard_quantities.values()) if sideboard_quantities else 0,
                "format": format_name,
                "is_valid": len(errors) == 0
            }

            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings,
                "summary": summary,
                "card_status": card_status,
                "deck_analysis": deck_analysis
            }

    except Exception as e:
        logger.error(f"Error validating deck: {e}", exc_info=True)
        return {
            "valid": False,
            "errors": [f"Validation error: {str(e)}"],
            "warnings": [],
            "summary": {},
            "card_status": [],
            "deck_analysis": None
        }


def format_validation_results(validation_result: Dict[str, Any]) -> Tuple[str, pd.DataFrame, Dict[str, Any]]:
    """
    Format validation results for UI display.
    
    Args:
        validation_result: Result from validate_deck_format
        
    Returns:
        Tuple of (summary_text, card_status_df, deck_analysis)
    """
    summary = validation_result.get("summary", {})
    card_status = validation_result.get("card_status", [])
    deck_analysis = validation_result.get("deck_analysis")
    errors = validation_result.get("errors", [])
    warnings = validation_result.get("warnings", [])
    
    # Format summary text
    summary_lines = []
    summary_lines.append(f"📋 **Deck Summary**")
    summary_lines.append(f"  • **Name**: {summary.get('deck_name', 'Unknown')}")
    summary_lines.append(f"  • **Total Cards**: {summary.get('total_cards', 0)}")
    summary_lines.append(f"  • **Unique Cards**: {summary.get('unique_cards', 0)}")
    summary_lines.append(f"  • **Found in DB**: {summary.get('found_cards', 0)}")
    summary_lines.append(f"  • **Missing**: {summary.get('missing_cards', 0)}")
    summary_lines.append(f"  • **Illegal**: {summary.get('illegal_cards', 0)}")
    if summary.get('sideboard_cards', 0) > 0:
        summary_lines.append(f"  • **Sideboard**: {summary.get('sideboard_cards', 0)}")
    summary_lines.append(f"  • **Format**: {summary.get('format', 'Unknown')}")
    
    # Format validation status
    summary_lines.append(f"\n⚖️ **Format Validation**")
    if validation_result.get("valid", False):
        summary_lines.append("  ✅ **Deck is VALID**")
    else:
        summary_lines.append("  ❌ **Deck is NOT VALID**")
        for error in errors:
            summary_lines.append(f"    • {error}")
    
    if warnings:
        summary_lines.append(f"\n⚠️ **Warnings**")
        for warning in warnings:
            summary_lines.append(f"  • {warning}")
    
    summary_text = "\n".join(summary_lines)
    
    # Create DataFrame for card status
    if card_status:
        df = pd.DataFrame(card_status)
        df = df[["quantity", "name", "status", "reason", "owned"]]
        df.columns = ["Qty", "Name", "Status", "Reason", "Owned"]
    else:
        df = pd.DataFrame(columns=["Qty", "Name", "Status", "Reason", "Owned"])
    
    return summary_text, df, deck_analysis


def format_deck_analysis(deck_analysis: Optional[Dict[str, Any]]) -> str:
    """
    Format deck analysis for display.
    
    Args:
        deck_analysis: Deck analysis dictionary
        
    Returns:
        Formatted analysis text
    """
    if not deck_analysis:
        return "No deck analysis available."
    
    lines = []
    lines.append("📊 **Advanced Deck Analysis**")
    
    # Basic stats
    lines.append(f"  • **Overall**: {deck_analysis.get('total_cards', 0)} cards, "
                f"{deck_analysis.get('land_count', 0)} lands, "
                f"{deck_analysis.get('spell_count', 0)} spells")
    lines.append(f"  • **Avg. Mana Value**: {deck_analysis.get('avg_mana_value', 'N/A')}")
    lines.append(f"  • **Colors**: {', '.join(deck_analysis.get('color_identity', []))}")
    
    # Mana curve
    if deck_analysis.get("mana_curve"):
        lines.append("\n📈 **Mana Curve**")
        curve = deck_analysis["mana_curve"]
        for cmc, count in sorted(curve.items()):
            lines.append(f"  • {cmc} CMC: {count} cards")
    
    # Type breakdown
    if deck_analysis.get("type_counts"):
        lines.append("\n🏷️ **Type Breakdown**")
        types = deck_analysis["type_counts"]
        for t, count in sorted(types.items()):
            lines.append(f"  • {t}: {count} cards")
    
    # Keywords
    if deck_analysis.get("keyword_summary"):
        lines.append("\n🔑 **Frequent Keywords**")
        keywords = deck_analysis["keyword_summary"]
        top_keywords = sorted(keywords.items(), key=lambda item: (-item[1], item[0]))[:5]
        for k, count in top_keywords:
            lines.append(f"  • {k.capitalize()}: {count} cards")
    
    # Land breakdown
    if deck_analysis.get("land_breakdown"):
        lines.append("\n🌍 **Land Breakdown**")
        lands = deck_analysis["land_breakdown"]
        for land, count in sorted(lands.items()):
            lines.append(f"  • {count}x {land}")
    
    return "\n".join(lines)


def validate_and_import_arena(
    arena_text: str,
    format_name: str = "standard",
    inventory_file: Optional[str] = None,
    owned_only: bool = False,
    selected_columns: Optional[List[str]] = None
) -> Tuple[gr.update, gr.update, gr.update, gr.update, gr.update]:
    """
    Validate Arena deck and return formatted results for UI.
    
    Args:
        arena_text: Arena deck export text
        format_name: Format to validate against
        inventory_file: Path to inventory file
        owned_only: Whether to only allow owned cards
        selected_columns: Columns to display in results
        
    Returns:
        Tuple of UI updates (validation_summary, card_status_table, deck_analysis, deck_state, import_status)
    """
    try:
        # Validate the deck
        validation_result = validate_deck_format(
            arena_text, format_name, inventory_file, owned_only
        )
        
        # Format results
        summary_text, card_status_df, deck_analysis = format_validation_results(validation_result)
        
        # Format deck analysis
        analysis_text = format_deck_analysis(deck_analysis)
        
        # Create deck state if valid
        deck_state = None
        import_status = "❌ Import failed - deck is not valid"
        
        if validation_result.get("valid", False) and deck_analysis:
            try:
                # Parse and create deck
                arena_lines = arena_text.strip().split('\n')
                parsed = parse_arena_export(arena_lines)
                card_quantities = parsed['main']
                deck_name = parsed.get('deck_name') or "Imported Arena Deck"
                
                with get_session() as session:
                    if inventory_file:
                        load_inventory_items(inventory_file, session)
                    
                    repo = SummaryCardRepository(session)
                    found_cards_map = {
                        name: repo.find_by_name(name, exact=False) 
                        for name in card_quantities 
                        if repo.find_by_name(name, exact=False)
                    }
                    
                    # Create deck
                    deck = Deck(name=deck_name)
                    for name, card_obj in found_cards_map.items():
                        deck.insert_card(card_obj, card_quantities[name])
                    
                    # Create deck state
                    deck_state = {
                        "name": deck.name,
                        "cards": deck.to_dict(),
                        "config": None
                    }
                    
                    import_status = f"✅ Successfully imported {deck.name} with {len(deck.cards)} cards"
                    
            except Exception as e:
                logger.error(f"Error creating deck state: {e}")
                import_status = f"⚠️ Validation passed but import failed: {str(e)}"
        
        # Filter card status columns if specified
        if selected_columns and not card_status_df.empty:
            available_columns = [col for col in selected_columns if col in card_status_df.columns]
            if available_columns:
                card_status_df = card_status_df[available_columns]
        
        return (
            gr.update(value=summary_text),  # validation_summary
            gr.update(value=card_status_df),  # card_status_table
            gr.update(value=analysis_text),  # deck_analysis
            gr.update(value=deck_state),  # deck_state
            gr.update(value=import_status)  # import_status
        )
        
    except Exception as e:
        logger.error(f"Error in validate_and_import_arena: {e}", exc_info=True)
        error_msg = f"Validation error: {str(e)}"
        return (
            gr.update(value=error_msg),
            gr.update(value=pd.DataFrame()),
            gr.update(value=""),
            gr.update(value=None),
            gr.update(value="❌ Validation failed")
        )


def validate_generated_deck(
    deck: Deck,
    format_name: str = "standard",
    owned_only: bool = False
) -> Dict[str, Any]:
    """
    Validate a generated deck against a specified format.
    
    Args:
        deck: Deck object to validate
        format_name: Format to validate against
        owned_only: Whether to only allow owned cards
        
    Returns:
        Dictionary containing validation results
    """
    try:
        if not deck or not deck.cards:
            return {
                "valid": False,
                "errors": ["No deck or cards provided"],
                "warnings": [],
                "summary": {},
                "card_status": [],
                "deck_analysis": None
            }

        # Validate in database session
        with get_session() as session:
            repo = SummaryCardRepository(session)
            
            # Get card quantities from deck
            card_quantities = {}
            for card_name, quantity in deck.inventory.items():
                card_quantities[card_name] = quantity
            
            # Look up cards
            found_cards_map = {}
            missing_cards = []
            for name in card_quantities:
                card = repo.find_by_name(name, exact=False)
                if card:
                    found_cards_map[name] = card
                else:
                    missing_cards.append(name)

            # Validate format rules
            errors = []
            warnings = []
            illegal_cards = []
            
            rules = FORMAT_RULES.get(format_name.lower())
            if not rules:
                errors.append(f"Unknown format '{format_name}'")
            else:
                # Deck size validation
                total_cards = sum(card_quantities.values())
                if "min_size" in rules and total_cards < rules["min_size"]:
                    errors.append(f"Deck has {total_cards} cards, format minimum is {rules['min_size']}")
                if "max_size" in rules and total_cards > rules["max_size"]:
                    errors.append(f"Deck has {total_cards} cards, format maximum is {rules['max_size']}")

                # Card validation
                for name, quantity in card_quantities.items():
                    card = found_cards_map.get(name)
                    is_basic_land = name in BASIC_LANDS
                    owned = get_owned_qty(card, name) if card else 0
                    
                    # Copy limit validation
                    if not is_basic_land and quantity > rules['max_copies']:
                        errors.append(f"Too many copies of '{name}' ({quantity}), max is {rules['max_copies']}")

                    # Format legality
                    if card and hasattr(card, 'is_legal_in') and not card.is_legal_in(format_name):
                        errors.append(f"'{name}' is not legal in {format_name}")
                        illegal_cards.append(name)

                    # Ownership validation
                    if owned_only and not is_basic_land and owned < quantity:
                        errors.append(f"Not enough owned copies of '{name}': need {quantity}, have {owned}")

            # Create card status report
            card_status = []
            for name in sorted(card_quantities.keys()):
                quantity = card_quantities[name]
                card = found_cards_map.get(name)
                owned = get_owned_qty(card, name) if card else 0
                is_basic_land = name in BASIC_LANDS
                
                status = "❌ Not Found"
                reason = "Not in database"
                
                if card:
                    if name in illegal_cards:
                        status = "⚠️ Illegal"
                        reason = f"Not legal in {format_name}"
                    elif owned_only and not is_basic_land and owned < quantity:
                        status = "❌ Not enough copies"
                        reason = f"Need {quantity}, have {owned}"
                    else:
                        status = "✅ Found"
                        reason = ""
                
                card_status.append({
                    "name": name,
                    "quantity": quantity,
                    "status": status,
                    "reason": reason,
                    "owned": owned if not is_basic_land else "∞"
                })

            # Create deck analysis
            deck_analysis = None
            if deck.cards:
                analyzer = DeckAnalyzer(deck)
                deck_analysis = analyzer.summary_dict()

            # Create summary
            summary = {
                "deck_name": deck.name or "Generated Deck",
                "total_cards": sum(card_quantities.values()),
                "unique_cards": len(card_quantities),
                "found_cards": len(found_cards_map),
                "missing_cards": len(missing_cards),
                "illegal_cards": len(illegal_cards),
                "sideboard_cards": 0,  # Generated decks don't have sideboards
                "format": format_name,
                "is_valid": len(errors) == 0
            }

            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings,
                "summary": summary,
                "card_status": card_status,
                "deck_analysis": deck_analysis
            }

    except Exception as e:
        logger.error(f"Error validating generated deck: {e}", exc_info=True)
        return {
            "valid": False,
            "errors": [f"Validation error: {str(e)}"],
            "warnings": [],
            "summary": {},
            "card_status": [],
            "deck_analysis": None
        }


def validate_and_analyze_generated_deck(
    deck: Deck,
    format_name: str = "standard",
    owned_only: bool = False
) -> Tuple[gr.update, gr.update, gr.update]:
    """
    Validate a generated deck and return formatted results for UI.
    
    Args:
        deck: Deck object to validate
        format_name: Format to validate against
        owned_only: Whether to only allow owned cards
        
    Returns:
        Tuple of UI updates (validation_summary, card_status_table, deck_analysis)
    """
    try:
        # Validate the deck
        validation_result = validate_generated_deck(deck, format_name, owned_only)
        
        # Format results
        summary_text, card_status_df, deck_analysis = format_validation_results(validation_result)
        
        # Format deck analysis
        analysis_text = format_deck_analysis(deck_analysis)
        
        return (
            gr.update(value=summary_text),  # validation_summary
            gr.update(value=card_status_df),  # card_status_table
            gr.update(value=analysis_text)  # deck_analysis
        )
        
    except Exception as e:
        logger.error(f"Error in validate_and_analyze_generated_deck: {e}", exc_info=True)
        error_msg = f"Validation error: {str(e)}"
        return (
            gr.update(value=error_msg),
            gr.update(value=pd.DataFrame()),
            gr.update(value="")
        ) 