import yaml
from typing import Dict, List

from mtg_deck_builder.data_loader import load_inventory_from_txt, load_atomic_cards_from_json
from mtg_deck_builder.models.inventory import Inventory
from mtg_deck_builder.models.collection import Collection


def load_yaml_deck(file_path: str) -> Dict:
    """Loads deck-building criteria from a YAML file."""
    with open(file_path, 'r') as f:
        return yaml.safe_load(f)


def load_inventory(file_path: str) -> Inventory:
    """Loads an inventory from a text file."""

    return load_inventory_from_txt(file_path)


def weight_cards(card_collection: Collection, deck_criteria: Dict) -> Dict:
    """
    Assigns a weight score to each card based on deck-building criteria.
    """
    card_weights = {}

    for card in card_collection:
        weight = 0

        # Weight for color identity
        if set(card.colorIdentity).issubset(set(deck_criteria['deck']['colors'])):
            weight += 10

        # Weight for legality
        if deck_criteria['deck'].get('legalities', []):
            for legality in deck_criteria['deck']['legalities']:
                if card.is_legal_in(legality):
                    weight += 5

        # Weight for categories
        for category, rules in deck_criteria.get('categories', {}).items():
            if card.matches_keyword(rules.get('preferred_keywords', [])):
                weight += 10
            if card.matches_text(rules.get('priority_text', [])):
                weight += 8

        # Bonus for preferred text
        for phrase in deck_criteria.get('card_constraints', {}).get('prefer_cards_with_text', []):
            if phrase in (card.text or ""):
                weight += 5

        # Penalty for avoid text
        for phrase in deck_criteria.get('card_constraints', {}).get('avoid_cards_with_text', []):
            if phrase in (card.text or ""):
                weight -= 5

        card_weights[card] = weight

    return card_weights


def filter_collection_for_deck(collection: Collection, deck_criteria: Dict) -> Collection:
    """
    Filters the card collection based on the deck-building criteria.
    """
    colors = deck_criteria['deck']['colors']
    legalities = deck_criteria['deck'].get('legalities', [])

    filtered_collection = collection.filter_cards(
        color_identity=colors,
        color_mode="contains",
        legal_in=legalities
    )

    # Further filtering based on category-specific criteria
    for category, rules in deck_criteria.get('categories', {}).items():
        preferred_keywords = rules.get('preferred_keywords', [])
        priority_text = rules.get('priority_text', [])

        filtered_collection = filtered_collection.filter_cards(
            keyword_query=preferred_keywords,
            text_query=priority_text,
        )

    return filtered_collection


def build_deck(collection: Collection, deck_criteria: Dict) -> List:
    """
    Selects the best cards from the filtered collection to build the deck.
    """
    deck = []
    max_copies = deck_criteria['deck'].get('max_card_copies', 4)

    card_weights = weight_cards(collection, deck_criteria)
    sorted_cards = sorted(collection, key=lambda c: card_weights.get(c, 0), reverse=True)

    for category, rules in deck_criteria.get('categories', {}).items():
        target_count = rules.get('target', 0)
        selected_cards = []

        for card in sorted_cards:
            if len(selected_cards) >= target_count:
                break
            if card.owned and card.quantity > 0:
                copies_to_add = min(card.quantity, max_copies, target_count - len(selected_cards))
                selected_cards.extend([card] * copies_to_add)

        deck.extend(selected_cards)

    return deck


# Usage
yaml_criteria = load_yaml_deck('dmir.yaml')
inventory = load_inventory('card_inventory_2025-03-14.txt')
atomic_cards = load_atomic_cards_from_json('cards.json')
collection = Collection.build_from_inventory(atomic_cards, inventory)
filtered_collection = filter_collection_for_deck(collection, yaml_criteria)
deck = build_deck(filtered_collection, yaml_criteria)

# Print deck composition
for card in deck:
    print(f"{card.name} ({card.quantity}x)")
