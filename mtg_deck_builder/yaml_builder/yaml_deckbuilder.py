import logging
from pathlib import Path
from typing import Any, Dict, Optional, Union

import yaml

from mtg_deck_builder.db.repository import CardRepository, InventoryRepository
from mtg_deck_builder.models.deck import Deck
from mtg_deck_builder.yaml_builder.helpers import (
    _select_priority_cards,
    _select_special_lands,
    _distribute_basic_lands,
    _fill_categories,
    _fill_with_any,
    _finalize_deck,
)
from mtg_deck_builder.deck_config.deck_config import DeckConfig

logger = logging.getLogger(__name__)

def _run_callback(callbacks, hook_name, **kwargs):
    if callbacks and hook_name in callbacks:
        kwargs["hook_name"] = hook_name
        try:
            callbacks[hook_name](**kwargs)
        except Exception as e:
            logger.warning(f"Callback '{hook_name}' raised an error: {e}")

def build_deck_from_config(
    deck_config: DeckConfig,
    card_repo: CardRepository,
    inventory_repo: Optional[InventoryRepository] = None,
    callbacks: Optional[Dict[str, Any]] = None
) -> Deck:
    logger.debug(f"[DEBUG] Entering build_deck_from_config")

    deck_meta = deck_config.deck
    categories = deck_config.categories or {}
    priority_cards = deck_config.priority_cards or []
    mana_base = deck_config.mana_base or {}
    card_constraints = deck_config.card_constraints or None
    scoring_rules = deck_config.scoring_rules or None
    fallback = deck_config.fallback_strategy or None
    mana_curve = deck_meta.mana_curve or {}
    owned_cards_only = deck_meta.owned_cards_only

    deck_size = deck_meta.size
    max_copies = deck_meta.max_card_copies
    allowed_colors = set(deck_meta.colors)
    legalities = deck_meta.legalities
    color_match_mode = deck_meta.color_match_mode
    mana_min = mana_curve.get("min", None)
    mana_max = mana_curve.get("max", None)
    _run_callback(callbacks, "after_deck_config_load", config=deck_config)
    # Inventory handling
    inventory_items = None
    if owned_cards_only and inventory_repo:
        inventory_items = inventory_repo.get_owned_cards()
        repo = card_repo.get_owned_cards_by_inventory(inventory_items)
        _run_callback(callbacks, "after_inventory_load", inventory_items=inventory_items, repo=repo, config=deck_config) # New callback
    else:
        repo = card_repo

    _run_callback(callbacks, "before_initial_repo_filter", repo=repo, config=deck_config) # New callback (before filtering)
    repo = repo.filter_cards(
        color_identity=list(allowed_colors),
        color_mode=color_match_mode,
        legal_in=legalities[0] if legalities else None
    )
    _run_callback(callbacks, "after_initial_repo_filter", repo=repo, config=deck_config) # New callback (after filtering)

    # Fetch basic lands using the new names_in parameter for precision and robustness.
    # Uses the original card_repo to ensure all basic land types are available.
    basic_land_names = ["Plains", "Island", "Swamp", "Mountain", "Forest"]
    basic_lands_repo = card_repo.filter_cards(names_in=basic_land_names, type_query="Basic Land")
    basic_lands = basic_lands_repo.get_all_cards()

    # Priority cards
    selected_cards = _select_priority_cards(priority_cards, card_repo, allowed_colors, color_match_mode, legalities, max_copies)
    _run_callback(callbacks, "after_priority_cards", selected=selected_cards, config=deck_config, repo=card_repo)

    # Mana base
    land_count = getattr(mana_base, "land_count", 22)
    special_lands_meta = getattr(mana_base, "special_lands", None)
    special_land_limit = getattr(special_lands_meta, "count", 0) if special_lands_meta else 0
    special_land_prefer = getattr(special_lands_meta, "prefer", []) if special_lands_meta else []
    special_land_avoid = getattr(special_lands_meta, "avoid", []) if special_lands_meta else []

    all_lands = [card for card in repo.get_all_cards() if card.matches_type("land")]
    non_basic_lands = [card for card in all_lands if not card.is_basic_land()]
    special_lands = _select_special_lands(
        non_basic_lands, special_land_prefer, special_land_avoid, special_land_limit, allowed_colors
    )
    for land in special_lands:
        land.owned_qty = 1
        selected_cards[land.name] = land

    num_special = len(special_lands)
    num_basic_needed = max(0, land_count - num_special)
    _distribute_basic_lands(selected_cards, basic_lands, allowed_colors, num_basic_needed, legalities, max_copies=max_copies)
    _run_callback(callbacks, "after_land_selection", selected=selected_cards, config=deck_config, repo=card_repo)

    # Fill categories
    _fill_categories(
        categories, repo, selected_cards, mana_min, mana_max, max_copies, deck_size,
        scoring_rules=scoring_rules, card_constraints=card_constraints, inventory_items=inventory_items,
        callbacks=callbacks  # Pass callbacks to _fill_categories
    )
    _run_callback(callbacks, "after_categories", selected=selected_cards, config=deck_config, repo=card_repo)

    # Fallback
    _run_callback(callbacks, "before_fallback_fill", selected_cards=selected_cards, deck_size=deck_size, current_card_count=sum(c.owned_qty for c in selected_cards.values()), config=deck_config) # New callback
    if fallback and getattr(fallback, "fill_with_any", True):
        _fill_with_any(
            repo, selected_cards, deck_size, mana_min, mana_max, max_copies,
            scoring_rules=scoring_rules, card_constraints=card_constraints, inventory_items=inventory_items, callbacks=callbacks # Pass callbacks
        )

    _run_callback(callbacks, "before_finalize", selected=selected_cards, config=deck_config, repo=card_repo)

    deck = _finalize_deck(selected_cards, max_copies, deck_size)
    deck.session = card_repo.session
    deck.config = deck_config
    return deck

def build_deck_from_yaml(
    yaml_data: Union[Dict[str, Any],str],
    card_repo: CardRepository,
    inventory_repo: Optional[InventoryRepository] = None,
    callbacks: Optional[Dict[str, Any]] = None
) -> Deck:
    if isinstance(yaml_data, str):
        yaml_path = Path(yaml_data)
        if not yaml_path.exists():
            raise FileNotFoundError(f"YAML file not found: {yaml_path}")
        with open(yaml_path, 'r') as file:
            yaml_data = yaml.safe_load(file)
    deck_config = DeckConfig.model_validate(yaml_data) if not isinstance(yaml_data, DeckConfig) else yaml_data
    return build_deck_from_config(deck_config, card_repo, inventory_repo, callbacks=callbacks)
