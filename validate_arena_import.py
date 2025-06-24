#!/usr/bin/env python3
"""
Utility script to validate an Arena deck import against a specified format.
Reports illegal, banned, or missing cards and deck size/copy violations.
"""

import argparse
from collections import defaultdict
from typing import Dict
from mtg_deck_builder.db.loader import load_inventory
from mtg_deck_builder.db.mtgjson_models.cards import MTGJSONSummaryCard
from mtg_deck_builder.utils.arena_parser import parse_arena_export
from mtg_deck_builder.db import get_session
from mtg_deck_builder.db.repository import SummaryCardRepository
from mtg_deck_builder.models.deck import Deck
from mtg_deck_builder.utils.arena_deck_creator import FORMAT_RULES
from mtg_deck_builder.models.deck_analyzer import DeckAnalyzer

try:
    import pyperclip
    HAS_CLIPBOARD = True
except ImportError:
    HAS_CLIPBOARD = False

BASIC_LANDS = {
    'Plains', 'Island', 'Swamp', 'Mountain', 'Forest',
    'Snow-Covered Plains', 'Snow-Covered Island', 'Snow-Covered Swamp',
    'Snow-Covered Mountain', 'Snow-Covered Forest', 'Wastes'
}

def get_owned_qty(card, name):
    if name in BASIC_LANDS:
        return 99999999
    try:
        return int(getattr(card, "owned_qty", 0))
    except Exception:
        return 0

def print_deck_statistics(deck) -> None:
    """Print comprehensive deck statistics for a given Deck object."""
    if not deck or not deck.cards:
        print("\nNo cards found in database to analyze.")
        return

    print(f"\n📊 Deck Statistics (based on {deck.size()} found cards):")

    mana_curve = defaultdict(int)
    color_dist = defaultdict(int)
    type_breakdown = defaultdict(int)

    for card_name, quantity in deck.inventory.items():
        card = deck.cards.get(card_name)
        if not card:
            continue

        # Mana Curve (non-lands)
        if hasattr(card, "types") and "Land" not in card.types:
            cmc = getattr(card, "mana_value", 0) or 0
            mana_curve[cmc] += quantity

        # Color Distribution (non-lands)
        if hasattr(card, "colors") and getattr(card, "types") and "Land" not in card.types:
            colors = card.colors or ["Colorless"]
            for color in colors:
                color_dist[color] += quantity

        # Type Breakdown
        if hasattr(card, "types"):
            type_breakdown[card.types[0]] += quantity

    print("\n📈 Mana Curve:")
    for cmc, count in sorted(mana_curve.items()):
        print(f"  {cmc} CMC: {count} cards")

    print("\n🎨 Color Distribution:")
    for color, count in sorted(color_dist.items()):
        print(f"  {color}: {count} cards")

    print("\n🏷️ Type Breakdown:")
    for card_type, count in sorted(type_breakdown.items()):
        print(f"  {card_type}: {count} cards")

def print_pretty_card_list(deck) -> None:
    """Prints a formatted table of cards in the deck."""
    if not deck or not deck.inventory:
        return

    print(f"\n📝 Deck List ({deck.size()} cards):")

    table_data = []
    headers = ["Qty", "Name", "Mana Cost", "Type", "Rarity"]

    sorted_cards = sorted(
        deck.inventory.items(),
        key=lambda item: (
            (getattr(deck.cards.get(item[0]), "types", ["Z"])[0] or "Z"),
            item[0],
        ),
    )

    for card_name, quantity in sorted_cards:
        card = deck.cards.get(card_name)
        if card:
            mana_cost = getattr(card, "mana_cost", "") or ""
            card_type = (getattr(card, "types", ["Unknown"])[0] or "Unknown")
            rarity = (getattr(card, "rarity", "") or "").capitalize()
            table_data.append(
                [
                    f"{quantity}x",
                    card_name,
                    mana_cost,
                    card_type,
                    rarity,
                ]
            )

    if not table_data:
        return

    col_widths = [len(header) for header in headers]
    for row in table_data:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(cell)))

    header_line = " | ".join(f"{h:<{col_widths[i]}}" for i, h in enumerate(headers))
    separator = "-+-".join("-" * width for width in col_widths)
    print(header_line)
    print(separator)

    for row in table_data:
        row_line = " | ".join(
            f"{str(cell):<{col_widths[i]}}" for i, cell in enumerate(row)
        )
        print(row_line)

def print_advanced_statistics(summary: dict) -> None:
    """Prints a formatted summary of deck statistics."""
    print("\n📊 Advanced Deck Analysis:")

    print(
        f"  - Overall: {summary.get('total_cards')} cards, {summary.get('land_count')} lands, {summary.get('spell_count')} spells"
    )
    print(f"  - Avg. Mana Value: {summary.get('avg_mana_value')}")
    print(f"  - Colors: {', '.join(summary.get('color_identity', []))}")

    if summary.get("mana_curve"):
        print("\n📈 Mana Curve:")
        curve = summary["mana_curve"]
        for cmc, count in sorted(curve.items()):
            print(f"  {cmc} CMC: {count} cards")

    if summary.get("type_counts"):
        print("\n🏷️ Type Breakdown:")
        types = summary["type_counts"]
        for t, count in sorted(types.items()):
            print(f"  {t}: {count} cards")

    if summary.get("keyword_summary"):
        print("\n🔑 Frequent Keywords:")
        keywords = summary["keyword_summary"]
        top_keywords = sorted(keywords.items(), key=lambda item: (-item[1], item[0]))[:5]
        for k, count in top_keywords:
            print(f"  {k.capitalize()}: {count} cards")

    if summary.get("land_breakdown"):
        print("\n🌍 Land Breakdown:")
        lands = summary["land_breakdown"]
        for land, count in sorted(lands.items()):
            print(f"  {count}x {land}")

def print_card_status_report(
    card_quantities: dict, found_cards_map: Dict[str, MTGJSONSummaryCard], illegal_cards: list
) -> None:
    """Prints a detailed report on the status of each card, including owned quantity."""
    print("\n📋 Card Status Report:")
    headers = ["Qty", "Name", "Status", "Reason", "Owned"]
    table_data = []

    all_card_names = sorted(card_quantities.keys())

    for name in all_card_names:
        quantity = card_quantities[name]
        status = "❌ Not Found"
        reason = "Not in database"
        card = found_cards_map.get(name)
        owned = get_owned_qty(card, name) if card else "-"
        is_basic_land = name in BASIC_LANDS
        if card:
            if name in illegal_cards:
                status = "⚠️ Illegal"
                reason = "Not legal in format"
            elif not is_basic_land and owned != "-" and int(owned) < quantity:
                status = "❌ Not enough copies"
                reason = f"Need {quantity}, have {owned}"
            else:
                status = "✅ Found"
                reason = ""
        table_data.append([f"{quantity}x", name, status, reason, owned])

    col_widths = [len(header) for header in headers]
    for row in table_data:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(cell)))

    header_line = " | ".join(f"{h:<{col_widths[i]}}" for i, h in enumerate(headers))
    separator = "-+-".join("-" * width for width in col_widths)
    print(header_line)
    print(separator)

    for row in table_data:
        row_line = " | ".join(
            f"{str(cell):<{col_widths[i]}}" for i, cell in enumerate(row)
        )
        print(row_line)

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate MTG Arena deck import against a format."
    )
    parser.add_argument(
        "arena_file",
        nargs="?",
        help="Path to Arena deck export file (txt)",
    )
    parser.add_argument(
        "--format",
        "-f",
        default="standard",
        help="Format to validate (e.g. standard, alchemy, commander)",
    )
    parser.add_argument(
        "--clipboard",
        action="store_true",
        help="Read Arena deck from clipboard instead of file",
    )
    parser.add_argument(
        "--owned_only",
        action="store_true",
        help="Only allow cards in the inventory",
    )
    parser.add_argument(
        "--inventory_file",
        default="inventory_files/card inventory.txt",
        help="Path to inventory file",
    )
    args = parser.parse_args()

    # 1. Get Deck Text
    if args.clipboard:
        if not HAS_CLIPBOARD:
            print("pyperclip is not installed. Use 'pip install pyperclip'.")
            return
        arena_text = pyperclip.paste()
        print("Read Arena deck from clipboard.")
    elif args.arena_file:
        with open(args.arena_file, "r", encoding="utf-8") as f:
            arena_text = f.read()
    else:
        parser.print_help()
        return

    print(f"\nValidating Arena deck for format: {args.format}\n{'='*50}")

    # 2. Parse Text
    arena_lines = arena_text.strip().split('\n')
    parsed = parse_arena_export(arena_lines)
    card_quantities = parsed['main']
    sideboard_quantities = parsed.get('sideboard')
    deck_name = parsed.get('deck_name') or "Imported Deck"
    if not card_quantities:
        print("❌ No valid cards found in Arena export.")
        return

    # 3. Look up cards in DB and do all analysis inside the session
    with get_session() as session:
        load_inventory(session, args.inventory_file)
        repo = SummaryCardRepository(session)
        found_cards_map = {name: repo.find_by_name(name, exact=False) for name in card_quantities if repo.find_by_name(name, exact=False)}
        missing_card_names = [name for name in card_quantities if name not in found_cards_map]

        # 4. Validate Format and get illegal cards
        errors = []
        illegal_cards = []
        rules = FORMAT_RULES.get(args.format.lower())
        if not rules:
            errors.append(f"Unknown format '{args.format}'.")
        else:
            # Deck size
            total_cards = sum(card_quantities.values())
            if "min_size" in rules and total_cards < rules["min_size"]:
                errors.append(f"Deck has {total_cards} cards, format minimum is {rules['min_size']}.")
            if "max_size" in rules and total_cards > rules["max_size"]:
                errors.append(f"Deck has {total_cards} cards, format maximum is {rules['max_size']}.")

            # Card copies and legality
            for name, quantity in card_quantities.items():
                card = found_cards_map.get(name)
                is_basic_land = name in BASIC_LANDS
                owned = get_owned_qty(card, name) if card else 0
                
                if not is_basic_land and quantity > rules['max_copies']:
                    errors.append(f"Too many copies of '{name}' ({quantity}), max is {rules['max_copies']}.")

                if card and hasattr(card, 'is_legal_in') and not card.is_legal_in(args.format):
                    errors.append(f"'{name}' is not legal in {args.format}.")
                    illegal_cards.append(name)

                if not is_basic_land and owned < quantity:
                    errors.append(f"Not enough owned copies of '{name}': need {quantity}, have {owned}.")

        # 5. Print Reports
        print(f"📋 Deck Summary:")
        print(f"  Total cards in list: {sum(card_quantities.values())}")
        print(f"  Unique cards in list: {len(card_quantities)}")
        if deck_name:
            print(f"  Deck name: {deck_name}")
        if sideboard_quantities:
            print(f"  Sideboard cards: {sum(sideboard_quantities.values())}")

        print(f"\n⚖️ Format Validation ({args.format}):")
        if not errors:
            print("  ✅ Deck is VALID.")
        else:
            print("  ❌ Deck is NOT VALID:")
            for err in errors:
                print(f"    - {err}")

        print_card_status_report(card_quantities, found_cards_map, illegal_cards)

        # 6. Create Deck Object from found/legal cards and print analysis
        if found_cards_map:
            # Exclude illegal cards from the analysis deck
            analysis_cards = {k: v for k, v in found_cards_map.items() if k not in illegal_cards}
            
            if analysis_cards:
                deck = Deck(name=deck_name)
                for name, card_obj in analysis_cards.items():
                    deck.insert_card(card_obj, card_quantities[name])
                
                analyzer = DeckAnalyzer(deck)
                summary = analyzer.summary_dict()
                print_advanced_statistics(summary)
                print_pretty_card_list(deck)
            else:
                print("\nNo legal cards found to analyze.")

if __name__ == "__main__":
    main()