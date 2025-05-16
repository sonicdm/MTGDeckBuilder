from typing import Dict

from mtg_deck_builder.models.collection import Collection


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


def score_creature_or_planeswalker(card, criteria):
    """Score creatures and planeswalkers based on preferred keywords and priority text."""
    score = 0
    text = card.text.lower()

    # Preferred keywords
    for keyword in criteria.get('preferred_keywords', []):
        if keyword.lower() in text:
            score += 10

    # Priority text
    for phrase in criteria.get('priority_text', []):
        if phrase.lower() in text:
            score += 5

    return score


def score_instant_or_sorcery(card, criteria):
    """Score instants and sorceries based on priority text."""
    score = 0
    text = card.text.lower()

    for phrase in criteria.get('priority_text', []):
        if phrase.lower() in text:
            score += 8

    return score


def score_land(card, criteria):
    """Score lands based on mana-fixing attributes and avoidance criteria."""
    score = 0
    text = card.text.lower()

    # Preferred land attributes
    for phrase in criteria.get('mana_base', {}).get('special_lands', {}).get('prefer', []):
        if phrase.lower() in text:
            score += 10

    # Avoidance criteria
    for phrase in criteria.get('mana_base', {}).get('special_lands', {}).get('avoid', []):
        if phrase.lower() in text:
            score -= 10

    return score


def score_creature_or_planeswalker(card, criteria):
    """Score creatures and planeswalkers based on preferred keywords and priority text, while penalizing avoid criteria."""
    score = 0
    text = card.text.lower()

    # Preferred keywords
    for keyword in criteria.get('preferred_keywords', []):
        if keyword.lower() in text:
            score += 10

    # Priority text
    for phrase in criteria.get('priority_text', []):
        if phrase.lower() in text:
            score += 5

    # Avoidance criteria
    for phrase in criteria.get('avoid_cards_with_text', []):
        if phrase.lower() in text:
            score -= 10

    return score


def score_instant_or_sorcery(card, criteria):
    """Score instants and sorceries based on priority text, with penalties for avoid criteria."""
    score = 0
    text = card.text.lower()

    for phrase in criteria.get('priority_text', []):
        if phrase.lower() in text:
            score += 8

    # Avoidance criteria
    for phrase in criteria.get('avoid_cards_with_text', []):
        if phrase.lower() in text:
            score -= 10

    return score


def score_land(card, criteria):
    """Score lands based on mana-fixing attributes and avoidance criteria."""
    score = 0
    text = card.text.lower()

    # Preferred land attributes
    for phrase in criteria.get('mana_base', {}).get('special_lands', {}).get('prefer', []):
        if phrase.lower() in text:
            score += 10

    # Avoidance criteria
    for phrase in criteria.get('mana_base', {}).get('special_lands', {}).get('avoid', []):
        if phrase.lower() in text:
            score -= 10

    return score


def load_yaml_deck_with_defaults(file_path):
    """Loads deck-building criteria from a YAML file and ensures all necessary fields exist."""
    yaml_data = load_yaml_deck(file_path)

    # Ensure key sections exist
    yaml_data.setdefault('deck', {})
    yaml_data.setdefault('categories', {})
    yaml_data.setdefault('mana_base', {})
    yaml_data['mana_base'].setdefault('land_count', 24)
    yaml_data['mana_base'].setdefault('special_lands', {'count': 0, 'prefer': [], 'avoid': []})
    yaml_data['mana_base'].setdefault('balance', {'adjust_by_mana_symbols': False})
    yaml_data.setdefault('card_constraints', {'rarity_boost': {}, 'exclude_keywords': [], 'prefer_cards_with_text': [],
                                              'avoid_cards_with_text': []})

    for category in yaml_data['categories']:
        yaml_data['categories'][category].setdefault('target', 0)
        yaml_data['categories'][category].setdefault('preferred_keywords', [])
        yaml_data['categories'][category].setdefault('priority_text', [])

    return yaml_data