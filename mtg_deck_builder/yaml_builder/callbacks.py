"""
Example Callbacks for the YAML builder.
"""
from mtg_deck_builder.deck_config.deck_config import DeckConfig


def log_summary(selected, **kwargs):
    """
    Print a quick summary of card counts.
    """
    print(f"[CB] Deck so far: {sum(c.owned_qty for c in selected.values())} cards")
    for name, card in sorted(selected.items()):
        print(f" - {name} x{card.owned_qty}")


def assert_no_commons(selected, **kwargs):
    """
    Raise error if any common rarity card exists.
    """
    commons = [name for name, card in selected.items() if card.rarity == "common"]
    if commons:
        raise AssertionError(f"[CB] Common cards found: {commons}")


def ensure_card_present(card_name, min_copies=1):
    """
    Returns a callback that ensures a specific card is present at least `min_copies` times.
    """
    def _callback(selected, **kwargs):
        if card_name not in selected:
            raise AssertionError(f"[CB] Required card missing: {card_name}")
        if selected[card_name].owned_qty < min_copies:
            raise AssertionError(f"[CB] Not enough copies of {card_name} (have {selected[card_name].owned_qty}, need {min_copies})")
    return _callback


def limit_card_copies(max_allowed=4):
    """
    Enforces a global limit on card copies.
    """
    def _callback(selected, **kwargs):
        over_limit = [(n, c.owned_qty) for n, c in selected.items() if c.owned_qty > max_allowed]
        if over_limit:
            raise AssertionError(f"[CB] Card copy limit exceeded: {over_limit}")
    return _callback


def log_special_lands(selected=None, **kwargs):
    """
    Logs which lands were chosen as special lands.
    """
    if selected:
        print(f"[CB] Special lands: {[c.name for c in selected]}")


def log_deck_config_details(**kwargs):
    """
    Logs some details from the DeckConfig object if available.
    """
    config = kwargs.get('config')
    if isinstance(config, DeckConfig):
        print(f"[CB] Deck Name from Config: {config.deck.name}")
        print(f"[CB] Owned Cards Only from Config: {config.deck.owned_cards_only}")
        if config.scoring_rules and config.scoring_rules.min_score_to_flag:
            print(f"[CB] Min Score to Flag from Config: {config.scoring_rules.min_score_to_flag}")
        # Example of accessing a category's target
        if config.categories and "creatures" in config.categories:
            print(f"[CB] Creatures category target: {config.categories['creatures'].target}")
        if config.deck.inventory_file:
            print(f"[CB] Inventory File from Config: {config.deck.inventory_file}")
    else:
        print("[CB] DeckConfig not found or not of expected type in kwargs for log_deck_config_details.")


def log_inventory_load(**kwargs):
    """
    Logs details after inventory is loaded and repo potentially filtered.
    """
    inventory_items = kwargs.get('inventory_items')
    repo = kwargs.get('repo')
    config = kwargs.get('config')
    if config and config.deck.owned_cards_only:
        print(f"[CB] after_inventory_load: Running with owned_cards_only = True.")
        if inventory_items is not None:
            print(f"[CB] {len(inventory_items)} distinct items loaded from inventory.")
        else:
            print("[CB] No inventory items loaded (or inventory_repo not provided).")
        # Potentially log repo size or a few card names if needed
    else:
        print("[CB] after_inventory_load: Running with owned_cards_only = False (or no inventory repo).")


def log_repo_filter_state(**kwargs):
    """
    Logs the state of the card repository at different filter stages.
    """
    repo = kwargs.get('repo')
    config = kwargs.get('config')
    print(f"[CB] {hook_name}: Repo contains {len(repo.get_all_cards())} cards after this stage.")
    if config:
        print(f"    Applied with config: {config.deck.name}, Colors: {config.deck.colors}, Legalities: {config.deck.legalities}")


def log_before_category_fill(**kwargs):
    """
    Logs details before a specific category is filled.
    """
    category_name = kwargs.get('category_name')
    category_config = kwargs.get('category_config')
    # repo = kwargs.get('repo') # repo is available if needed
    # selected_cards_so_far = kwargs.get('selected_cards_so_far') # available if needed
    print(f"[CB] before_category_fill:{category_name}: Target is {category_config.target}.")
    print(f"    Preferred Keywords: {category_config.preferred_keywords}")
    print(f"    Priority Text: {category_config.priority_text}")


def log_before_fallback_fill(**kwargs):
    """
    Logs deck state before fallback fill strategy is applied.
    """
    selected_cards = kwargs.get('selected_cards')
    deck_size = kwargs.get('deck_size')
    current_card_count = kwargs.get('current_card_count')
    config = kwargs.get('config') # DeckConfig
    print(f"[CB] before_fallback_fill: Current deck has {current_card_count}/{deck_size} cards.")
    if config and config.fallback_strategy:
        print(f"    Fallback strategy: fill_with_any={config.fallback_strategy.fill_with_any}, fill_priority={config.fallback_strategy.fill_priority}")

def log_after_deck_config_load(**kwargs):
    """
    Logs details after the deck configuration is loaded.
    """
    config = kwargs.get('config')
    if isinstance(config, DeckConfig):
        print(f"[CB] Deck Name from Config: {config.deck.name}")
        print(f"[CB] Owned Cards Only from Config: {config.deck.owned_cards_only}")
        if config.scoring_rules and config.scoring_rules.min_score_to_flag:
            print(f"[CB] Min Score to Flag from Config: {config.scoring_rules.min_score_to_flag}")
        # Example of accessing a category's target
        if config.categories and "creatures" in config.categories:
            print(f"[CB] Creatures category target: {config.categories['creatures'].target}")
        if config.deck.inventory_file:
            print(f"[CB] Inventory File from Config: {config.deck.inventory_file}")
    else:
        print("[CB] DeckConfig not found or not of expected type in kwargs for log_deck_config_load.")

