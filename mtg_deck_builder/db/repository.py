"""
Repository classes for Magic: The Gathering deck builder application.

Provides high-level interfaces for querying and managing cards, sets, and inventory
using SQLAlchemy ORM models defined in db.models.

Classes:
    - CardRepository: Query and filter CardDB and related printings.
    - CardSetRepository: Query CardSetDB for set information.
    - InventoryRepository: Query InventoryItemDB for inventory management.
"""

from typing import List, Optional, Dict

from sqlalchemy import func
from sqlalchemy.orm import Session
from datetime import datetime, date
from mtg_deck_builder.db.models import CardDB, CardSetDB, InventoryItemDB


class CardRepository:
    """
    Repository for managing and querying card data from the database.

    Works with CardDB objects, which aggregate all printings of a card.
    Supports filtering, searching, and retrieving printings.
    """

    def __init__(self, session: Optional[Session] = None, cards: Optional[List[CardDB]] = None) -> None:
        """
        Initialize the CardRepository.

        Args:
            session (Optional[Session]): SQLAlchemy session for database queries.
            cards (Optional[List[CardDB]]): Preloaded list of cards to use instead of querying the database.
        """
        self.session = session
        self._cards = cards

    def get_all_cards(self) -> List[CardDB]:
        """
        Retrieve all cards from the database or the preloaded list.

        Returns:
            List[CardDB]: List of all cards.
        """
        if self._cards is not None:
            return self._cards
        if self.session is not None:
            return self.session.query(CardDB).all()
        raise ValueError("No session or preloaded cards provided.")

    def find_by_name(self, name: str) -> Optional[CardDB]:
        """
        Find a card by its name (case-insensitive substring match).

        Args:
            name (str): Name of the card to search for.

        Returns:
            Optional[CardDB]: The card if found, otherwise None.
        """
        if self._cards is not None:
            return next((card for card in self._cards if name.lower() in card.name.lower()), None)
        return self.session.query(CardDB).filter(CardDB.name.ilike(f"%{name}%")).first()

    def find_all_printings(self, name: str) -> List[CardDB]:
        """
        Find all printings of a card by its name (case-insensitive exact match).

        Args:
            name (str): Name of the card to search for.

        Returns:
            List[CardDB]: List of all printings of the card.
        """
        if self._cards is not None:
            return [card for card in self._cards if card.name.lower() == name.lower()]
        return self.session.query(CardDB).filter(CardDB.name.ilike(name)).all()

    def get_newest_printing(self, cards: List[CardDB]) -> Optional[CardDB]:
        """
        Get the newest printing of a card from a list of cards.

        Args:
            cards (List[CardDB]): List of card printings.

        Returns:
            Optional[CardDB]: The newest printing of the card, or None if the list is empty.
        """
        if not cards:
            return None

        def get_release_date(card: CardDB) -> Optional[date]:
            raw_date_val = None
            set_obj = getattr(card, "set", None)

            # Try to get release date from the card's associated set object first
            if set_obj and hasattr(set_obj, "release_date") and set_obj.release_date is not None:
                raw_date_val = set_obj.release_date

            # If not found or None, and session is available, try querying CardSetDB
            if raw_date_val is None and self.session is not None and hasattr(card, "set_code"):
                set_row = self.session.query(CardSetDB).filter_by(set_code=card.set_code).first()
                if set_row and hasattr(set_row, "release_date") and set_row.release_date is not None:
                    raw_date_val = set_row.release_date

            if isinstance(raw_date_val, date):
                return raw_date_val
            elif isinstance(raw_date_val, str):
                try:
                    # Attempt to parse YYYY-MM-DD strings
                    return datetime.strptime(raw_date_val, "%Y-%m-%d").date()
                except ValueError:
                    # If parsing fails, return None
                    # Optionally, log a warning here:
                    # import logging
                    # logging.warning(f"Could not parse date string '{raw_date_val}' for card {getattr(card, 'name', 'Unknown Card')}")
                    return None

            # If raw_date_val was None initially, or not a date/parsable string
            return None

        # Use date.min as a fallback for comparison if a release date is None, ensuring type consistency for max()
        return max(cards, key=lambda c: get_release_date(c) or date.min)

    def get_owned_cards_by_inventory(self, inventory_items: List[InventoryItemDB]) -> 'CardRepository':
        """
        Retrieve owned cards based on inventory items.

        Args:
            inventory_items (List[InventoryItemDB]): List of inventory items.

        Returns:
            CardRepository: A repository containing the owned cards (newest printing per owned card).
        """
        owned_names = [item.card_name for item in inventory_items]
        if not owned_names:
            return CardRepository(cards=[])

        lower_owned_names = [name.lower() for name in owned_names]

        all_printings = self.session.query(CardDB).filter(
            func.lower(CardDB.name).in_(lower_owned_names)
        ).all()

        grouped: Dict[str, List[CardDB]] = {}
        for card in all_printings:
            key = card.name.lower()
            grouped.setdefault(key, []).append(card)

        all_cards = []
        for item in inventory_items:
            name_key = item.card_name.lower()
            printings = grouped.get(name_key, [])
            newest = self.get_newest_printing(printings)
            if newest:
                all_cards.append(newest)

        return CardRepository(cards=all_cards)

    def filter_cards(
            self,
            name_query: Optional[str] = None,
            text_query: Optional[str] = None,
            rarity: Optional[str] = None,
            color_identity: Optional[List[str]] = None,
            color_mode: str = "subset",
            legal_in: Optional[str] = None,
            type_query: Optional[str] = None,
            names_in: Optional[List[str]] = None,  # <-- Re-added
            force_refresh: bool = False,
            min_quantity: int = 0,
    ) -> 'CardRepository':
        """
        Filters the cards based on the provided criteria.

        Args:
            name_query (Optional[str]): Filter by card name (substring match).
            text_query (Optional[str]): Filter by card text (substring match).
            rarity (Optional[str]): Filter by card rarity.
            color_identity (Optional[List[str]]): Filter by card color identity (see CardDB.matches_color_identity).
            color_mode (str): Mode for color identity filtering. One of {"exact", "subset", "any"}.
            legal_in (Optional[str]): Filter by legality in a specific format.
            type_query (Optional[str]): Filter by card type line (substring match).
            names_in (Optional[List[str]]): Filter by a list of exact card names (case-insensitive).
            force_refresh (bool): If True, always query the database for cards.
            min_quantity (int): Minimum quantity of owned copies of a card to include in the result.

        Returns:
            CardRepository: A repository containing the filtered cards.
        """
        cards = self.get_all_cards() if (self._cards is None or force_refresh) else self._cards
        filtered = []
        color_identity_skipped = 0

        # Prepare a lowercased set of names_in for efficient lookup if provided
        lower_names_in = {name.lower() for name in names_in} if names_in else None

        for card in cards:
            # Use getattr to support both CardDB (owned_qty) and InventoryItemDB (quantity)
            qty = getattr(card, "owned_qty", getattr(card, "quantity", 0))
            if min_quantity > qty:
                continue
            if color_identity and not card.matches_color_identity(color_identity, color_mode):
                color_identity_skipped += 1
                continue
            if name_query and name_query.lower() not in (card.name or '').lower():
                continue
            if text_query and text_query.lower() not in (card.text or '').lower():
                continue
            if rarity and (card.rarity or '').lower() != rarity.lower():
                continue
            if legal_in:
                status = (card.legalities or {}).get(legal_in, '')
                if status.lower() != 'legal':
                    continue
            if type_query and (not card.type or type_query.lower() not in card.type.lower()):
                continue
            if lower_names_in and (card.name or '').lower() not in lower_names_in: # <-- Re-added logic
                continue
            filtered.append(card)
        if color_identity and color_identity_skipped > 0:
            # Only log a summary, not per-card
            import logging
            logging.getLogger(__name__).debug(
                f"Skipped {color_identity_skipped} cards due to color identity mismatch (mode={color_mode}, query={color_identity})"
            )
        return CardRepository(session=self.session, cards=filtered)


class CardSetRepository:
    """
    Repository for managing and querying card set data from the database.

    Works with CardSetDB objects, which represent MTG sets/expansions.
    """

    def __init__(self, session: Session) -> None:
        """
        Initialize the CardSetRepository.

        Args:
            session (Session): SQLAlchemy session for database queries.
        """
        self.session = session

    def get_all_sets(self) -> List[CardSetDB]:
        """
        Retrieve all card sets from the database.

        Returns:
            List[CardSetDB]: List of all card sets.
        """
        return self.session.query(CardSetDB).all()

    def find_by_code(self, set_code: str) -> Optional[CardSetDB]:
        """
        Find a card set by its set code.

        Args:
            set_code (str): The set code to search for.

        Returns:
            Optional[CardSetDB]: The card set if found, otherwise None.
        """
        return self.session.query(CardSetDB).filter_by(set_code=set_code).first()


class InventoryRepository:
    """
    Repository for managing and querying inventory data from the database.

    Works with InventoryItemDB objects, which track owned cards and quantities.
    """

    def __init__(self, session: Session) -> None:
        """
        Initialize the InventoryRepository.

        Args:
            session (Session): SQLAlchemy session for database queries.
        """
        self.session = session

    def get_all_items(self) -> List[InventoryItemDB]:
        """
        Retrieve all inventory items from the database.

        Returns:
            List[InventoryItemDB]: List of all inventory items.
        """
        return self.session.query(InventoryItemDB).all()

    def get_owned_cards(self) -> List[InventoryItemDB]:
        """
        Retrieve all owned cards from the inventory.

        Returns:
            List[InventoryItemDB]: List of owned inventory items (quantity > 0 or is_infinite).
        """
        return self.session.query(InventoryItemDB).filter(
            (InventoryItemDB.quantity > 0) | (InventoryItemDB.is_infinite == True)
        ).all()

    def find_by_card_name(self, card_name: str) -> Optional[InventoryItemDB]:
        """
        Find an inventory item by its card name.

        Args:
            card_name (str): The name of the card to search for.

        Returns:
            Optional[InventoryItemDB]: The inventory item if found, otherwise None.
        """
        return self.session.query(InventoryItemDB).filter_by(card_name=card_name).first()

