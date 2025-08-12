"""Shared types for the YAML deck builder."""
from typing import Dict, List, Optional, Any, Callable, Union, TYPE_CHECKING, Set
from dataclasses import dataclass, field
from mtg_deck_builder.db.mtgjson_models.cards import MTGJSONSummaryCard
from mtg_deck_builder.models.deck_config import DeckConfig

if TYPE_CHECKING:
    from mtg_deck_builder.models.deck import Deck

@dataclass
class LandStub:
    """A stub for a basic land card."""
    name: str
    color: str
    type: str = "Basic Land"
    color_identity: List[str] = field(default_factory=list)
    mana_cost: str = ""
    oracle_text: str = ""
    keywords: List[str] = field(default_factory=list)
    rarity: str = "common"
    set_code: str = "core"
    collector_number: str = "1"
    is_foil: bool = False
    
    def __post_init__(self):
        if not self.color_identity:
            self.color_identity = [self.color]
    
    @property
    def basic_type(self) -> str:
        """Get the basic type of the land."""
        return "Land"
    
    @property
    def colors(self) -> List[str]:
        """Get the colors of the land."""
        return [self.color]
    
    def matches_type(self, type_string: str) -> bool:
        """Check if the land matches a type string."""
        return type_string.lower() in self.type.lower()
    
    def is_basic_land(self) -> bool:
        """Check if this is a basic land."""
        return True
    

@dataclass
class ContextCard:
    """A card in the deck build context."""
    card: MTGJSONSummaryCard
    quantity: int = 1
    score: Optional[float] = None
    reasons: List[str] = field(default_factory=list)
    sources: List[str] = field(default_factory=list)
    
    def add_reason(self, reason: str) -> None:
        """Add a reason for including this card."""
        self.reasons.append(reason)
    
    def add_source(self, source: str) -> None:
        """Add a source for this card."""
        self.sources.append(source)
    
    def set_quantity(self, quantity: int) -> None:
        """Set the quantity of this card."""
        self.quantity = quantity

@dataclass
class DeckBuildContext:
    """Context for building a deck."""
    config: DeckConfig
    deck: 'Deck'
    cards: List[ContextCard] = field(default_factory=list)
    used_cards: Set[str] = field(default_factory=set)
    unmet_conditions: List[str] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)
    category_summary: Dict[str, "DeckBuildCategorySummary"] = field(default_factory=dict)
    
    def add_card(self, card: MTGJSONSummaryCard, reason: str, source: str, quantity: int = 1) -> bool:
        """Add a card to the deck."""
        card_name = str(getattr(card, 'name', ''))
        if not card_name or card_name in self.used_cards:
            return False
        context_card = ContextCard(card=card, quantity=quantity)
        context_card.add_reason(reason)
        context_card.add_source(source)
        self.cards.append(context_card)
        self.used_cards.add(card_name)
        return True
    
    def record_unmet_condition(self, condition: str) -> None:
        """Record an unmet condition."""
        self.unmet_conditions.append(condition)
    
    def get_total_cards(self) -> int:
        """Get the total number of cards in the deck."""
        return sum(card.quantity for card in self.cards)
    
    def get_card_names(self) -> Set[str]:
        """Get the names of all cards in the deck."""
        return self.used_cards
    
    def get_card_quantity(self, name: str) -> int:
        """Get the quantity of a card in the deck."""
        for card in self.cards:
            if str(getattr(card.card, 'name', '')) == name:
                return card.quantity
        return 0
    
    def get_active_cards(self) -> List[ContextCard]:
        """Get all active cards in the deck."""
        return self.cards

CallbackDict = Dict[str, Callable[..., Any]] 


@dataclass
class ScoredCard:
    """A card with a score."""
    card: MTGJSONSummaryCard
    score: float
    reasons: List[str] = field(default_factory=list)
    sources: List[str] = field(default_factory=list)
    
    def add_reason(self, reason: str, score: float) -> None:
        """Add a reason for including this card."""
        self.reasons.append(f"{reason} ({score:.1f})")
    
    def add_source(self, source: str) -> None:
        """Add a source for this card."""
        self.sources.append(source)
    
    def increase_score(self, score: float, source: str, reason: str) -> None:
        self.score += score
        self.add_source(source)
        self.add_reason(reason, score)
        
    def __lt__(self, other: 'ScoredCard') -> bool:
        """Compare two scored cards."""
        return self.score < other.score
    
    def __gt__(self, other: 'ScoredCard') -> bool:
        """Compare two scored cards."""
        return self.score > other.score
    
    def __eq__(self, other: 'ScoredCard') -> bool:
        """Compare two scored cards."""
        return self.score == other.score
    
    def __ne__(self, other: 'ScoredCard') -> bool:
        """Compare two scored cards."""
        return self.score != other.score
    
    def __le__(self, other: 'ScoredCard') -> bool:
        """Compare two scored cards."""
        return self.score <= other.score
    
    def __ge__(self, other: 'ScoredCard') -> bool:
        """Compare two scored cards."""
        return self.score >= other.score
    
    def __repr__(self) -> str:
        """Return a string representation of the scored card."""
        return f"ScoredCard(card={self.card.name}, score={self.score}, reasons={self.reasons}, sources={self.sources})"
    
    def __str__(self) -> str:
        """Return a string representation of the scored card."""
        return f"ScoredCard(card={self.card.name}, score={self.score}, reasons={self.reasons}, sources={self.sources})"
    
@dataclass
class DeckBuildCategorySummary:
    """A summary of a deck build category."""
    target: int = 0
    added: int = 0
    remaining: int = 0
    scored_cards: List[ScoredCard] = field(default_factory=list)
    
    
    @property
    def scored_cards_count(self) -> int:
        """Get the number of scored cards."""
        return len(self.scored_cards)
    
    @property
    def average_score(self) -> float:
        """Get the average score of the scored cards."""
        if not self.scored_cards:
            return 0.0
        return sum(card.score for card in self.scored_cards) / len(self.scored_cards)
    
    @property
    def max_score(self) -> float:
        """Get the maximum score of the scored cards."""
        if not self.scored_cards:
            return 0.0
        return max(card.score for card in self.scored_cards)
    
    @property
    def min_score(self) -> float:
        """Get the minimum score of the scored cards."""
        if not self.scored_cards:
            return 0.0
        return min(card.score for card in self.scored_cards)
    
    def __repr__(self) -> str:
        """Return a string representation of the deck build category summary."""
        return f"DeckBuildCategorySummary(target={self.target}, added={self.added}, remaining={self.remaining}, scored_cards_count={len(self.scored_cards)}, average_score={self.average_score}, max_score={self.max_score}, min_score={self.min_score})"
    
    def __str__(self) -> str:
        """Return a string representation of the deck build category summary."""
        return f"DeckBuildCategorySummary(target={self.target}, added={self.added}, remaining={self.remaining}, scored_cards_count={len(self.scored_cards)}, average_score={self.average_score}, max_score={self.max_score}, min_score={self.min_score})"
