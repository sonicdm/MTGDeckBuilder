"""
Repository classes for Magic: The Gathering deck builder application.

Provides high-level interfaces for:
- querying and managing cards, sets, and inventory
- using SQLAlchemy ORM models defined in db.mtgjson_models

Classes:
    - CardRepository: Query and filter MTGJSONCard and related data.
    - CardSetRepository: Query MTGJSONSet for set information.
    - SummaryCardRepository: Query MTGJSONSummaryCard for card summaries.
"""

from typing import Any, Callable, Dict, List, Optional, TypeVar, Protocol, Union
from sqlalchemy import and_, or_, func, text, inspect
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from abc import ABC, abstractmethod
import logging
import json
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.sql.schema import Column as SAColumn

from mtg_deck_builder.db.mtgjson_models.cards import (
    MTGJSONCard, MTGJSONSummaryCard
)
from mtg_deck_builder.db.mtgjson_models.sets import MTGJSONSet
from mtg_deck_builder.db.inventory import InventoryItem

logger = logging.getLogger(__name__)

T = TypeVar('T')


class RepositoryError(Exception):
    """Base exception for repository errors."""
    pass


class CardNotFoundError(RepositoryError):
    """Raised when a card cannot be found."""
    pass


class DatabaseError(RepositoryError):
    """Raised when a database operation fails."""
    pass


class RepositoryProtocol(Protocol):
    """Protocol defining the interface for all repositories."""

    @abstractmethod
    def get_all(self) -> List[Any]:
        """Get all items from the repository."""
        pass

    @abstractmethod
    def find_by_id(self, id: Any) -> Optional[Any]:
        """Find an item by its ID."""
        pass


class BaseRepository(ABC):
    """Base class for all repositories with common functionality."""

    def __init__(self, session: Session) -> None:
        """Initialize the repository with a database session.

        Args:
            session: SQLAlchemy database session.
        """
        self.session = session
        self._status_callback: Optional[Callable[[str], None]] = None

    def set_status_callback(self,
                            callback_func: Callable[[str],
                                                    None]) -> 'BaseRepository':
        """Set a status callback function for long operations.

        Args:
            callback_func: Function that takes a message string.

        Returns:
            Self for method chaining.
        """
        self._status_callback = callback_func
        return self

    def _report_status(self, message: str) -> None:
        """Report status through the callback if set.

        Args:
            message: Status message to report.
        """
        if self._status_callback:
            self._status_callback(message)

    def _handle_db_error(self, operation: str) -> None:
        """Handle database errors with proper logging.

        Args:
            operation: Description of the operation that failed.

        Raises:
            DatabaseError: If a database operation fails.
        """
        logger.error(f"Database error during {operation}")
        raise


class SummaryCardRepository(BaseRepository):
    """
    Repository for managing and querying summary card data from the database.

    Works with MTGJSONSummaryCard objects, which represent cards across all their printings.
    Provides efficient access to card data without needing to query individual printings.
    """

    def __init__(self, session: Session, cards: Optional[List[MTGJSONSummaryCard]] = None) -> None:
        """Initialize the summary card repository.

        Args:
            session: SQLAlchemy database session.
            cards: Optional list of cards for in-memory operations.
        """
        super().__init__(session)
        self.cards = cards  # Canonical in-memory set

    def get_all_cards(self) -> List[MTGJSONSummaryCard]:
        """Get all cards from the repository.

        If self.cards is set (in-memory cache), returns those.
        Otherwise queries the database with pagination for efficiency.

        Returns:
            List of MTGJSONSummaryCard objects.

        Raises:
            DatabaseError: If database query fails.
        """
        if self.cards is not None:
            logger.debug(
                f"Returning {len(self.cards)} cards from in-memory cache")
            return self.cards

        try:
            # Check if the table exists
            inspector = inspect(self.session.get_bind())
            tables = inspector.get_table_names()
            if 'summary_cards' not in tables:
                logger.error("summary_cards table does not exist!")
                raise DatabaseError("Summary card table not found")

            # Get column information
            columns = inspector.get_columns('summary_cards')
            logger.debug(f"Found {len(columns)} columns in summary_cards table")

            # Check if the table has data
            result = self.session.execute(text("SELECT COUNT(*) FROM summary_cards")).scalar()
            logger.debug(f"Total rows in summary_cards: {result}")
            if result == 0:
                logger.error("summary_cards table is empty! Please run build_summary_cards.py to populate it.")
                raise DatabaseError("Summary card table is empty")

            # Query all cards from the database
            query = self.session.query(MTGJSONSummaryCard)

            # Process in chunks to avoid memory issues
            BATCH_SIZE = 1000
            all_cards = []

            total_count = query.count()
            logger.debug(f"Total cards in database: {total_count}")

            for offset in range(0, total_count, BATCH_SIZE):
                batch = query.offset(offset).limit(BATCH_SIZE).all()
                all_cards.extend(batch)
                self._report_status(
                    f"Loaded batch of {len(batch)} cards (offset {offset})")

            logger.debug(f"Returning {len(all_cards)} total cards")
            return all_cards

        except SQLAlchemyError:
            self._handle_db_error("get_all_cards")
            raise

    def filter_cards(
        self,
        name_query: Optional[str] = None,
        text_query: Optional[str] = None,
        rarity: Optional[str] = None,
        basic_type: Optional[str] = None,
        type_text: Optional[Union[str, List[str]]] = None,  # Keep for backward compatibility
        supertype: Optional[str] = None,
        subtype: Optional[str] = None,
        keyword_multi: Optional[List[str]] = None,
        type_query: Optional[Union[str, List[str]]] = None,
        colors: Optional[List[str]] = None,
        color_identity: Optional[List[str]] = None,
        color_mode: str = "subset",
        legal_in: Optional[List[str]] = None,
        add_where: Optional[str] = None,
        exclude_type: Optional[List[str]] = None,
        names_in: Optional[List[str]] = None,
        min_quantity: int = 0,
        allow_colorless: bool = False,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> 'SummaryCardRepository':
        """Filter cards based on various criteria.
        
        Args:
            name_query: Name to search for
            text_query: Text to search for
            rarity: Rarity to filter by
            basic_type: Basic type to filter by
            type_text: Type text to search for (deprecated, use type_query)
            supertype: Supertype to filter by
            subtype: Subtype to filter by
            keyword_multi: Keywords to filter by
            type_query: Type text to search for (string or list)
            colors: Colors to filter by
            color_identity: Color identity to filter by
            color_mode: How to match colors ('exact', 'subset', 'any')
            legal_in: Format to check legality in
            add_where: Additional WHERE clause
            exclude_type: Types to exclude
            names_in: List of names to include
            min_quantity: Minimum quantity required
            allow_colorless: Whether to include colorless cards
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            New SummaryCardRepository instance with filtered cards
        """
        # Map type_text to type_query for backward compatibility
        if type_text and not type_query:
            type_query = type_text
            
        # Use in-memory filtering if we have cached cards
        if self.cards is not None:
            logger.debug("Using in-memory filtering with %d summary cards", len(self.cards))
            filtered = self._filter_in_memory(
                self.cards,
                name_query=name_query,
                text_query=text_query,
                rarity=rarity,
                basic_type=basic_type,
                supertype=supertype,
                subtype=subtype,
                keyword_multi=keyword_multi,
                type_query=type_query,
                color_identity=color_identity,
                color_mode=color_mode,
                legal_in=legal_in,
                add_where=add_where,
                exclude_type=exclude_type,
                names_in=names_in,
                limit=limit,
                offset=offset,
                allow_colorless=allow_colorless,
                min_quantity=min_quantity
            )
            
        # Otherwise use SQL query
        else:
            filtered = self._filter_with_sql(
                name_query=name_query,
                text_query=text_query,
                rarity=rarity,
                basic_type=basic_type,
                type_query=type_query,
                supertype=supertype,
                subtype=subtype,
                keyword_multi=keyword_multi,
                color_identity=color_identity,
                color_mode=color_mode,
                legal_in=legal_in,
                add_where=add_where,
                exclude_type=exclude_type,
                names_in=names_in,
                min_quantity=min_quantity,
                allow_colorless=allow_colorless,
                limit=limit,
                offset=offset
            )
        return SummaryCardRepository(self.session, filtered)

    def _filter_in_memory(
        self,
        cards: List[MTGJSONSummaryCard],
        name_query: Optional[str] = None,
        text_query: Optional[str] = None,
        rarity: Optional[str] = None,
        basic_type: Optional[str] = None,
        supertype: Optional[str] = None,
        subtype: Optional[str] = None,
        keyword_multi: Optional[List[str]] = None,
        type_query: Optional[Union[str, List[str]]] = None,
        color_identity: Optional[List[str]] = None,
        color_mode: str = "subset",
        add_where: Optional[str] = None,
        exclude_type: Optional[List[str]] = None,
        names_in: Optional[List[str]] = None,
        legal_in: Optional[List[str]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        allow_colorless: bool = False,
        min_quantity: int = 0
    ) -> List[MTGJSONSummaryCard]:
        """Filter cards in memory based on various criteria.

        Args:
            cards: List of cards to filter
            name_query: Name to search for
            text_query: Text to search for
            rarity: Rarity to filter by
            basic_type: Basic type to filter by
            supertype: Supertype to filter by
            subtype: Subtype to filter by
            keyword_multi: Keywords to filter by
            type_query: Type text to search for (string or list)
            colors: Colors to filter by
            color_mode: How to match colors ('exact', 'subset', 'any')
            add_where: Additional WHERE clause (ignored in memory)
            exclude_type: Types to exclude
            names_in: List of names to include
            limit: Maximum number of results
            offset: Number of results to skip
            allow_colorless: Whether to include colorless cards

        Returns:
            Filtered list of cards
        """
        logger = logging.getLogger(__name__)
        logger.debug(f"Starting in-memory filtering with {len(cards)} cards")
        filtered = cards
        if min_quantity > 0:
            filtered = [c for c in filtered if getattr(c, 'quantity', 0) >= min_quantity]
            logger.debug(f"Count after min_quantity: {len(filtered)}")
        # Filter by type_query
        if type_query:
            logger.debug(f"In-memory: Filtering by type_query: {type_query}")
            if filtered:
                sample = filtered[0].types
                logger.debug(f"Sample types value: {sample}")

            if isinstance(type_query, list):
                filtered = [card for card in filtered if any(card.matches_type(t) for t in type_query)]
                logger.debug(f"Count after type_query list: {len(filtered)}")
            else:
                filtered = [c for c in filtered if c.matches_type(type_query)]
                logger.debug(f"Count after type_query single: {len(filtered)}")

            if not filtered:
                all_types = set()   
                for card in cards:
                    all_types.update(card.types_list)
                logger.debug(f"All types in memory: {sorted(all_types)}")
                land_cards = [c for c in cards if 'Land' in c.types_list]
                logger.debug(f"Found {len(land_cards)} land cards in memory")
                if land_cards:
                    logger.debug(f"Sample land card types: {land_cards[0].types_list}")

        # Filter by name
        if name_query:
            filtered = [c for c in filtered if name_query.lower() in c.name.lower()]
            logger.debug(f"Count after name_query: {len(filtered)}")

        # Filter by text
        if text_query:
            filtered = [c for c in filtered if text_query.lower() in c.text.lower()]
            logger.debug(f"Count after text_query: {len(filtered)}")

        # Filter by rarity
        if rarity:
            filtered = [c for c in filtered if str(c.rarity) == rarity]
            logger.debug(f"Count after rarity: {len(filtered)}")

        # Filter by basic type
        if basic_type:
            filtered = [c for c in filtered if any(c.matches_type(t) for t in basic_type)]
            logger.debug(f"Count after basic_type: {len(filtered)}")

        # Filter by supertype
        if supertype:
            filtered = [c for c in filtered if any(c.matches_supertype(t) for t in supertype)]
            logger.debug(f"Count after supertype: {len(filtered)}")

        # Filter by subtype
        if subtype:
            filtered = [c for c in filtered if any(c.matches_subtype(t) for t in subtype)]
            logger.debug(f"Count after subtype: {len(filtered)}")

        # Filter by keywords. keyword_multi is a list of keywords to filter by. card.types is a list of keywords.
        # We need to check if any of the keywords in keyword_multi are in card.types.
        if keyword_multi:
            keyword_multi = [k.lower() for k in keyword_multi]
            filtered = [c for c in filtered if c.has_keywords(keyword_multi)]
            logger.debug(f"Count after keywords: {len(filtered)}")

        # Filter by color identity
        if color_identity:
            filtered = [
                c for c in filtered
                if c.matches_color_identity(
                    color_identity=color_identity,
                    mode=color_mode,
                    allow_colorless=allow_colorless
                )
            ]
            logger.debug(f"Count after color_identity: {len(filtered)}")

        # Filter by exclude type
        if exclude_type:
            filtered = [
                c for c in filtered
                if not any(t.lower() in c.type.lower() for t in exclude_type)
            ]
            logger.debug(f"Count after exclude_type: {len(filtered)}")

        # Filter by names
        if names_in:
            filtered = [c for c in filtered if c.name in names_in]
            logger.debug(f"Count after names_in: {len(filtered)}")

        # Filter by legalities
        if legal_in:
            filtered = [
                c for c in filtered
                if c.is_legal_in(legal_in)
            ]
            logger.debug(f"Count after legalities: {len(filtered)}")

        # Apply offset and limit
        if offset:
            filtered = filtered[offset:]
            logger.debug(f"Count after offset: {len(filtered)}")
        if limit:
            filtered = filtered[:limit]
            logger.debug(f"Count after limit: {len(filtered)}")

        return filtered

    def _filter_with_sql(
        self,
        name_query=None,
        text_query=None,
        rarity=None,
        basic_type=None,
        type_query=None,
        supertype=None,
        subtype=None,
        keyword_multi=None,
        color_identity=None,
        color_mode="subset",
        legal_in=None,
        add_where=None,
        exclude_type=None,
        names_in=None,
        min_quantity=0,
        allow_colorless=False,
        limit=None,
        offset=None,
    ) -> List[MTGJSONSummaryCard]:
        """Filter cards using SQL queries."""
        logger = logging.getLogger(__name__)
        
        # Initialize base query with eager loading of inventory_item
        from sqlalchemy.orm import joinedload
        base_query = self.session.query(MTGJSONSummaryCard).options(
            joinedload(MTGJSONSummaryCard.inventory_item)
        )
        logger.debug("Starting SQLAlchemy query for summary cards with eager loading")

        # Handle min_quantity filter by joining with inventory table
        if min_quantity > 0:
            from mtg_deck_builder.db.inventory import InventoryItem
            base_query = base_query.join(InventoryItem, InventoryItem.card_name == MTGJSONSummaryCard.name)
            base_query = base_query.filter(InventoryItem.quantity >= min_quantity)
            logger.debug(f"SQL: Joined with inventory and filtered for quantity >= {min_quantity}")

        # Log initial query state
        initial_count = base_query.count()
        logger.debug(f"Initial query count before filters: {initial_count}")

        # Check legalities format
        if legal_in:
            if isinstance(legal_in, str):
                legal_in = [legal_in]
            
            sample_legalities = self.session.query(MTGJSONSummaryCard.legalities).limit(1).scalar()
            logger.debug(f"Sample legalities format: {sample_legalities}")

            # Try a simpler approach first - just check if the field exists
            base_query = base_query.filter(MTGJSONSummaryCard.legalities.isnot(None))
            logger.debug(f"Count after legalities not null: {base_query.count()}")
            
            # Use LIKE to find legal cards with case-insensitive matching
            conditions = []
            for fmt in legal_in:
                # Look for the format being legal - match the actual format in the database
                # Use LOWER() for case-insensitive matching
                condition = func.lower(MTGJSONSummaryCard.legalities).ilike(f'%{fmt.lower()}%: %legal%')
                conditions.append(condition)
            
            if conditions:
                base_query = base_query.filter(or_(*conditions))
                logger.debug(f"Count after legalities filter: {base_query.count()}")

        if name_query:
            logger.debug(f"SQL: Filtering by name_query: {name_query}")
            base_query = base_query.filter(MTGJSONSummaryCard.name.ilike(f"%{name_query}%"))
            logger.debug(f"Count after name_query: {base_query.count()}")
        if text_query:
            logger.debug(f"SQL: Filtering by text_query: {text_query}")
            base_query = base_query.filter(MTGJSONSummaryCard.text.ilike(f"%{text_query}%"))
            logger.debug(f"Count after text_query: {base_query.count()}")
        if rarity:
            logger.debug(f"SQL: Filtering by rarity: {rarity}")
            base_query = base_query.filter(MTGJSONSummaryCard.rarity == rarity)
            logger.debug(f"Count after rarity: {base_query.count()}")
        if type_query:
            logger.debug(f"SQL: Filtering by type_query: {type_query}")
            # Debug the types field
            sample = self.session.query(MTGJSONSummaryCard.types).limit(1).scalar()
            logger.debug(f"Sample types value: {sample}")
            
            if isinstance(type_query, list):
                conditions = []
                for t in type_query:
                    logger.debug(f"Adding condition for type: {t}")
                    conditions.append(MTGJSONSummaryCard.types.contains([t]))
                base_query = base_query.filter(or_(*conditions))
            else:
                logger.debug(f"Adding condition for single type: {type_query}")
                base_query = base_query.filter(MTGJSONSummaryCard.types.contains([type_query]))
            
            # Debug the query
            logger.debug(f"SQL query after type filter: {base_query}")
            count = base_query.count()
            logger.debug(f"Count after type_query: {count}")
            
            # If count is 0, let's check what types we actually have
            if count == 0:
                all_types = self.session.query(MTGJSONSummaryCard.types).distinct().all()
                logger.debug(f"All distinct types in database: {all_types}")
                
                # Try a simpler query to see if we can find any lands
                test_query = self.session.query(MTGJSONSummaryCard).filter(
                    MTGJSONSummaryCard.types.contains(['Land'])
                )
                test_count = test_query.count()
                logger.debug(f"Test query count for 'Land' type: {test_count}")
                if test_count > 0:
                    sample_land = test_query.first()
                    logger.debug(f"Sample land card types: {sample_land.types}")

        if exclude_type:
            logger.debug(f"SQL: Filtering by exclude_type: {exclude_type}")
            if isinstance(exclude_type, list):
                conditions = []
                for t in exclude_type:
                    conditions.append(~MTGJSONSummaryCard.types.contains([t]))
                base_query = base_query.filter(and_(*conditions))
            else:
                base_query = base_query.filter(~MTGJSONSummaryCard.types.contains([exclude_type]))
            logger.debug(f"Count after exclude_type: {base_query.count()}")
        if names_in:
            logger.debug(f"SQL: Filtering by names_in: {names_in}")
            base_query = base_query.filter(MTGJSONSummaryCard.name.in_(names_in))
            logger.debug(f"Count after names_in: {base_query.count()}")
        if add_where:
            logger.debug(f"SQL: Applying additional where clause: {add_where}")
            base_query = base_query.filter(add_where)
            logger.debug(f"Count after add_where: {base_query.count()}")
        if basic_type:
            logger.debug(f"SQL: Filtering by basic_type: {basic_type}")
            if isinstance(basic_type, str):
                basic_type = [basic_type]
            
            # Debug the types field
            sample = self.session.query(MTGJSONSummaryCard.types).limit(1).scalar()
            logger.debug(f"Sample types value: {sample}")
            
            conditions = [MTGJSONSummaryCard.types.contains([bt]) for bt in basic_type]
            base_query = base_query.filter(or_(*conditions))
            logger.debug(f"Count after basic_type: {base_query.count()}")
        if supertype:
            logger.debug(f"SQL: Filtering by supertype: {supertype}")
            if isinstance(supertype, str):
                supertype = [supertype]
            
            conditions = [MTGJSONSummaryCard.supertypes.contains([st]) for st in supertype]
            base_query = base_query.filter(or_(*conditions))
            logger.debug(f"Count after supertype: {base_query.count()}")
        if subtype:
            logger.debug(f"SQL: Filtering by subtype: {subtype}")
            if isinstance(subtype, str):
                subtype = [subtype]
            
            conditions = [MTGJSONSummaryCard.subtypes.contains([st]) for st in subtype]
            base_query = base_query.filter(or_(*conditions))
            logger.debug(f"Count after subtype: {base_query.count()}")

        # # Colors filter
        # if color_identity:
        #     all_colors = ["B", "G", "R", "U", "W"]
        #     off_colors = [c for c in all_colors if c not in color_identity]
        #     logger.debug(f"SQL: Filtering by colors: {color_identity} with mode {color_mode}")
        #     if color_mode == "exact":
        #         # Exact match: card must have exactly the same colors (order-insensitive)
        #         base_query = base_query.filter(MTGJSONSummaryCard.colors == sorted(color_identity))
        #     elif color_mode == "subset":
        #         # Subset: card's colors must be a subset of the requested colors, and not contain off-colors
        #         for color in color_identity:
        #             base_query = base_query.filter(MTGJSONSummaryCard.colors.contains([color]))
        #         for color in off_colors:
        #             base_query = base_query.filter(~MTGJSONSummaryCard.colors.contains([color]))
        #         if allow_colorless:
        #             # Allow colorless cards (no colors)
        #             base_query = base_query.filter(
        #                 or_(
        #                     MTGJSONSummaryCard.colors == [],
        #                     *[MTGJSONSummaryCard.colors.contains([color]) for color in color_identity]
        #                 )
        #             )
        #     elif color_mode == "any":
        #         # Any: card must have at least one of the requested colors
        #         conditions = [MTGJSONSummaryCard.colors.contains([color]) for color in color_identity]
        #         base_query = base_query.filter(or_(*conditions))
        #     logger.debug(f"Count after colors: {base_query.count()}")

        # Keyword filter
        if keyword_multi:
            logger.debug(f"SQL: Filtering by keyword_multi: {keyword_multi}")
            # Debug the keywords field
            sample = self.session.query(MTGJSONSummaryCard.keywords).limit(1).scalar()
            logger.debug(f"Sample keywords value: {sample}")
            
            conditions = [MTGJSONSummaryCard.keywords.contains([kw]) for kw in keyword_multi]
            base_query = base_query.filter(or_(*conditions))
            logger.debug(f"Count after keyword_multi: {base_query.count()}")

        if limit is not None:
            logger.debug(f"SQL: Applying limit: {limit}")
            base_query = base_query.limit(limit)
        if offset is not None:
            logger.debug(f"SQL: Applying offset: {offset}")
            base_query = base_query.offset(offset)

        logger.debug("Executing SQLAlchemy query for summary cards")
        cards = base_query.all()
        logger.debug(f"SQLAlchemy query returned {len(cards)} cards")

        # Post-query color_identity filtering (if needed)
        if color_identity is not None:
            logger.debug(f"Post-query: Applying color_identity filter in-memory: {color_identity} with mode {color_mode}")
            before = len(cards)
            if color_mode == "exact":
                cards = [
                    c for c in cards
                    if (
                        (allow_colorless and not getattr(c, 'color_identity_list', []) and not color_identity)
                        or (set(getattr(c, 'color_identity_list', [])) == set(color_identity) and (allow_colorless or getattr(c, 'color_identity_list', [])))
                    )
                ]
            elif color_mode == "subset":
                cards = [
                    c for c in cards
                    if (
                        (allow_colorless and not getattr(c, 'color_identity_list', []))
                        or (set(getattr(c, 'color_identity_list', [])).issubset(set(color_identity)) and (allow_colorless or getattr(c, 'color_identity_list', [])))
                    )
                ]
            elif color_mode == "any":
                cards = [
                    c for c in cards
                    if (
                        (allow_colorless and not getattr(c, 'color_identity_list', []))
                        or (set(getattr(c, 'color_identity_list', [])) & set(color_identity) and (allow_colorless or getattr(c, 'color_identity_list', [])))
                    )
                ]
            else:
                if not allow_colorless:
                    cards = [c for c in cards if getattr(c, 'color_identity_list', [])]
            logger.debug(f"Cards after post-query color_identity: {len(cards)} (before: {before})")
        else:
            if not allow_colorless:
                logger.debug("Post-query: Filtering out colorless cards (color_identity_list must be truthy)")
                before = len(cards)
                cards = [c for c in cards if getattr(c, 'color_identity_list', [])]
                logger.debug(f"Cards after post-query colorless filter: {len(cards)} (before: {before})")

        # Inventory quantity filtering (in-memory only)
        # Note: min_quantity is now handled in SQL with inventory join above
        # if min_quantity > 0:
        #     before = len(cards)
        #     cards = [c for c in cards if getattr(c, 'owned_qty', 0) >= min_quantity]
        #     logger.debug(f"Cards after min_quantity filter: {len(cards)} (before: {before})")

        logger.debug(f"Returning {len(cards)} cards after all filters (SQL)")
        return cards

    def find_by_name(self, name: str, exact: bool = True) -> Optional[MTGJSONSummaryCard]:
        """Find a summary card by name.

        Args:
            name: Card name to find
            exact: Whether to require exact match

        Returns:
            MTGJSONSummaryCard if found, None otherwise
        """
        try:
            if self.cards is not None:
                if exact:
                    return next((c for c in self.cards if str(c.name) == name), None)
                return next((c for c in self.cards if name.lower() in str(c.name).lower()), None)

            if exact:
                return self.session.query(MTGJSONSummaryCard).filter(
                    MTGJSONSummaryCard.name == name
                ).first()
            return self.session.query(MTGJSONSummaryCard).filter(
                MTGJSONSummaryCard.name.ilike(f"%{name}%")
            ).first()
        except SQLAlchemyError:
            self._handle_db_error("find_by_name")
            raise

    def get_printings(self, name: str) -> List[str]:
        """Get all set codes where a card has been printed."""
        try:
            card = self.find_by_name(name)
            v = getattr(card, 'printing_set_codes', None)
            if card and v is not None and not isinstance(v, (InstrumentedAttribute, SAColumn)):
                if isinstance(v, list):
                    return v
                if isinstance(v, str):
                    try:
                        return json.loads(v)
                    except Exception:
                        return [x.strip() for x in v.split(',') if x.strip()]
                if isinstance(v, dict):
                    return list(v.values())
            return []
        except SQLAlchemyError:
            self._handle_db_error("get_printings")
            raise

    def get_legalities(self, name: str) -> Dict[str, str]:
        """Get legality information for a card."""
        try:
            card = self.find_by_name(name)
            v = getattr(card, 'legalities', None)
            if card and v is not None and not isinstance(v, (InstrumentedAttribute, SAColumn)):
                if isinstance(v, dict):
                    return v
                if isinstance(v, str):
                    try:
                        return json.loads(v)
                    except Exception:
                        return {}
            return {}
        except SQLAlchemyError:
            self._handle_db_error("get_legalities")
            raise
        
    def __repr__(self) -> str:
        return f"<SummaryCardRepository(cards={len(self.cards) if self.cards else 'database'})>"

    def filter_by_inventory_quantity(self, min_quantity: int = 1) -> 'SummaryCardRepository':
        """
        Return a new SummaryCardRepository with only cards that have inventory_item.quantity >= min_quantity.
        """
        if self.cards is not None:
            filtered = [c for c in self.cards if c.inventory_item is not None and c.inventory_item.quantity >= min_quantity]
            return SummaryCardRepository(self.session, filtered)
        else:
            # Query the database and join inventory
            from mtg_deck_builder.db.inventory import InventoryItem
            query = self.session.query(MTGJSONSummaryCard).join(InventoryItem, InventoryItem.card_name == MTGJSONSummaryCard.name)
            query = query.filter(InventoryItem.quantity >= min_quantity)
            cards = query.all()
            return SummaryCardRepository(self.session, cards)