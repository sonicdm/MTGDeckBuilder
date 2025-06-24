from typing import Any, Callable, Dict, List, Optional, TypeVar, Protocol, cast, Union
from sqlalchemy import or_, and_, func, Column
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import BinaryExpression
from mtg_deck_builder.db.mtgjson_models.cards import MTGJSONCard, MTGJSONCardLegality
from mtg_deck_builder.db.mtgjson_models.sets import MTGJSONSet
from mtg_deck_builder.db.mtgjson_models.tokens import MTGJSONToken

T = TypeVar('T')

class BaseMTGJSONRepository:
    """
    Base repository for MTGJSON models with common functionality.
    """
    def __init__(self, session: Session):
        self.session = session
        self._status_callback: Optional[Callable[[str], None]] = None

    def set_status_callback(self, callback_func: Callable[[str], None]) -> 'BaseMTGJSONRepository':
        self._status_callback = callback_func
        return self

    def _report_status(self, message: str) -> None:
        if self._status_callback:
            self._status_callback(message)

class MTGJSONCardRepository(BaseMTGJSONRepository):
    """
    Repository for managing and querying MTGJSONCard data, matching CardRepository functionality.
    Supports chaining by returning a new repository with in-memory filtered results.
    """
    def __init__(self, session: Session, cards: Optional[List[MTGJSONCard]] = None):
        super().__init__(session)
        self.cards = cards  # In-memory filtered set

    def get_all_cards(self) -> List[MTGJSONCard]:
        if self.cards is not None:
            return self.cards
        return self.session.query(MTGJSONCard).all()

    def filter_cards(
        self,
        name_query: Optional[str] = None,
        text_query: Optional[str] = None,
        rarity: Optional[str] = None,
        basic_type: Optional[str] = None,
        supertype: Optional[str] = None,
        subtype: Optional[str] = None,
        keyword_multi: Optional[List[str]] = None,
        type_query: Optional[str] = None,
        color_identity: Optional[List[str]] = None,
        color_mode: str = "subset",
        legal_in: Optional[str] = None,
        inventory_names: Optional[List[str]] = None,
        min_quantity: int = 0,
        printing_field_filters: Optional[Dict[str, Any]] = None,
        allow_colorless: bool = False,
        all_printings: bool = True,  # Always use all printings since we don't have cards_db
        **kwargs
    ) -> "MTGJSONCardRepository":
        # Filter and return all printings
        query = self.session.query(MTGJSONCard)
        if name_query:
            query = query.filter(MTGJSONCard.name.ilike(f"%{name_query}%"))
        if text_query:
            query = query.filter(MTGJSONCard.text.ilike(f"%{text_query}%"))
        if rarity:
            query = query.filter(MTGJSONCard.rarity.ilike(rarity))
        if type_query:
            query = query.filter(MTGJSONCard.type.ilike(f"%{type_query}%"))
        if basic_type:
            query = query.filter(MTGJSONCard.type.ilike(f"%{basic_type}%"))
        if supertype:
            query = query.filter(MTGJSONCard.type.ilike(f"%{supertype}%"))
        if subtype:
            query = query.filter(MTGJSONCard.type.ilike(f"%{subtype}%"))
        if keyword_multi:
            for keyword in keyword_multi:
                query = query.filter(MTGJSONCard.text.ilike(f"%{keyword}%"))
        if color_identity:
            if color_mode == "subset":
                for color in ['W', 'U', 'B', 'R', 'G']:
                    if color not in color_identity:
                        query = query.filter(~MTGJSONCard.colorIdentity.like(f"%{color}%"))
                color_conditions = [MTGJSONCard.colorIdentity.like(f"%{color}%") for color in color_identity if color != 'C']
                if color_conditions:
                    query = query.filter(or_(*color_conditions))
            elif color_mode == "exact":
                for color in ['W', 'U', 'B', 'R', 'G']:
                    if color not in color_identity:
                        query = query.filter(~MTGJSONCard.colorIdentity.like(f"%{color}%"))
                for color in color_identity:
                    query = query.filter(MTGJSONCard.colorIdentity.like(f"%{color}%"))
                query = query.filter(func.length(MTGJSONCard.colorIdentity) == len(color_identity))
            elif color_mode == "any":
                color_conditions = [MTGJSONCard.colorIdentity.like(f"%{color}%") for color in color_identity if color != 'C']
                if color_conditions:
                    query = query.filter(or_(*color_conditions))
        if legal_in:
            query = query.join(MTGJSONCardLegality, MTGJSONCard.uuid == MTGJSONCardLegality.uuid)
            query = query.filter(getattr(MTGJSONCardLegality, legal_in) == "Legal")
        if inventory_names:
            query = query.filter(MTGJSONCard.name.in_(inventory_names))
        if printing_field_filters:
            for field, value in printing_field_filters.items():
                query = query.filter(getattr(MTGJSONCard, field) == value)
        filtered = query.all()
        return MTGJSONCardRepository(self.session, cards=filtered)

    def __repr__(self):
        sample = self.cards[0] if self.cards else None
        return f"<MTGJSONCardRepository(cards={len(self.cards) if self.cards is not None else 'all'}, sample={sample!r})>"

    def find_by_name(self, name: str) -> Optional[MTGJSONCard]:
        # Returns the newest printing by releaseDate (if available)
        cards = (
            self.session.query(MTGJSONCard)
            .filter(MTGJSONCard.name == name)
            .all()
        )
        if not cards:
            return None
        # Pick the newest by releaseDate if available
        def get_release(card):
            return getattr(card, 'releaseDate', None) or ''
        newest = max(cards, key=get_release)
        return newest

    def get_all_printings(self, name: str) -> List[MTGJSONCard]:
        return self.session.query(MTGJSONCard).filter_by(name=name).all()

    def get_inventory_cards(self, inventory_names: List[str]) -> List[MTGJSONCard]:
        return self.session.query(MTGJSONCard).filter(MTGJSONCard.name.in_(inventory_names)).all()

    def get_newest_printing(self, name: str) -> Optional[MTGJSONCard]:
        return self.find_by_name(name)

    def get_cards_by_set(self, set_code: str) -> List[MTGJSONCard]:
        return self.session.query(MTGJSONCard).filter(MTGJSONCard.setCode == set_code).all()

    def get_cards_by_rarity(self, rarity: str) -> List[MTGJSONCard]:
        return self.session.query(MTGJSONCard).filter(MTGJSONCard.rarity.ilike(rarity)).all()

    def get_cards_by_type(self, type_query: str) -> List[MTGJSONCard]:
        return self.session.query(MTGJSONCard).filter(MTGJSONCard.type.ilike(f"%{type_query}%")).all()

    def get_cards_by_color_identity(self, color_identity: List[str], color_mode: str = "subset") -> List[MTGJSONCard]:
        return self.filter_cards(color_identity=color_identity, color_mode=color_mode).get_all_cards()

    def get_cards_by_legal_in(self, legal_in: str) -> List[MTGJSONCard]:
        return self.filter_cards(legal_in=legal_in).get_all_cards()

    def get_cards_by_keyword(self, keyword: str) -> List[MTGJSONCard]:
        return self.filter_cards(keyword_multi=[keyword]).get_all_cards()

    def get_cards_by_inventory(self, inventory_names: List[str], min_quantity: int = 1) -> List[MTGJSONCard]:
        # min_quantity is handled in inventory DB, so filter inventory_names before passing
        return self.filter_cards(inventory_names=inventory_names).get_all_cards()

    @staticmethod
    def rebuild_card_db(session):
        # Rebuild the card_db table from all printings
        pass  # This method is no longer needed since we're using MTGJSONCard directly

class MTGJSONSetRepository(BaseMTGJSONRepository):
    """
    Repository for managing and querying MTGJSONSet data.
    """
    def get_all_sets(self) -> List[MTGJSONSet]:
        return self.session.query(MTGJSONSet).all()

    def find_by_code(self, set_code: str) -> Optional[MTGJSONSet]:
        return self.session.query(MTGJSONSet).filter_by(code=set_code).first()

    def filter_sets(self, name_query: Optional[str] = None) -> List[MTGJSONSet]:
        query = self.session.query(MTGJSONSet)
        if name_query:
            query = query.filter(MTGJSONSet.name.ilike(f"%{name_query}%"))
        return query.all() 