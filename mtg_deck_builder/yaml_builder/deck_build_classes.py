# mtg_deck_builder/yaml_builder/deck_build_classes.py
"""Classes for deck building process."""

from typing import List, Dict, Optional, Any, Union, Set, Tuple
from datetime import datetime
import logging
from collections import defaultdict
import re
from mtg_deck_builder.models.deck_config import (
    DeckConfig,
    CategoryDefinition,
    ScoringRulesMeta,
    ManaBaseMeta,
    FallbackStrategyMeta,
    CardConstraintMeta,
    PriorityCardEntry,
    DeckMeta,
    ManaCurveMeta,
)
from mtg_deck_builder.db.repository import SummaryCardRepository
from mtg_deck_builder.db.mtgjson_models.cards import MTGJSONSummaryCard
from mtg_deck_builder.models.deck import Deck
from dataclasses import dataclass, field

from mtg_deck_builder.yaml_builder.types import DeckBuildCategorySummary

logger = logging.getLogger(__name__)

@dataclass
class LandStub:
    """Stub for basic land cards that don't exist in the database."""
    
    name: str
    color: str
    type: str = "Basic Land"
    color_identity: List[str] = field(default_factory=list)
    converted_mana_cost: int = 0
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
        
        # Set all foil variants to False
        for attr in ['is_foil_etched', 'is_foil_alt', 'is_foil_showcase', 'is_foil_borderless', 
                    'is_foil_double_sided', 'is_foil_oversized', 'is_foil_textured', 'is_foil_holo']:
            setattr(self, attr, False)
            
    @property
    def basic_type(self) -> str:
        """Get the basic type of the land."""
        return "Land"
        
    def matches_type(self, type_string: str) -> bool:
        """Check if the land matches a type string."""
        return type_string.lower() in self.type.lower()
        
    def is_basic_land(self) -> bool:
        """Check if this is a basic land."""
        return True
    def is_land(self) -> bool:
        """Check if this is a land."""
        return True
    
    @property
    def types(self) -> List[str]:
        """Get the types of the land."""
        return ["Land"]

@dataclass
class ContextCard:
    """Wrapper for cards in the deck building process."""
    
    card: Union[MTGJSONSummaryCard, LandStub]
    reason: str
    source: str
    quantity: int = 1
    score: Optional[int] = None
    replaced_at: Optional[str] = None
    replaced_by: Optional[str] = None
    sources: Set[str] = field(default_factory=set)
    
    @property
    def name(self) -> str:
        """Get the name of the card."""
        return str(getattr(self.card, 'name', ''))
        
    def mark_replaced(self, new_card_name: str) -> None:
        """Mark this card as replaced by another card."""
        self.replaced_at = datetime.now().isoformat()
        self.replaced_by = new_card_name
        
    def add_reason(self, reason: str) -> None:
        """Add a reason for this card's inclusion."""
        self.reason = f"{self.reason}; {reason}"

    def set_quantity(self, new_quantity: int) -> None:
        """Set the quantity of this card.
        
        Args:
            new_quantity: New quantity to set
        """
        if new_quantity < 0:
            raise ValueError("Quantity cannot be negative")
        self.quantity = new_quantity
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "name": self.name,
            "reason": self.reason,
            "source": self.source,
            "quantity": self.quantity,
            "score": self.score,
            "replaced_at": self.replaced_at,
            "replaced_by": self.replaced_by,
            "sources": list(self.sources)
        }

@dataclass
class DeckBuildContext:
    """Context for building a deck."""
    config: DeckConfig
    deck: Deck
    name: str = field(init=False)
    summary_repo: SummaryCardRepository
    cards: List[ContextCard] = field(default_factory=list)
    used_cards: Set[str] = field(default_factory=set)
    unmet_conditions: List[str] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)
    scored_cards: List[tuple[float, MTGJSONSummaryCard]] = field(default_factory=list)
    operations: List[str] = field(default_factory=list)
    # empty_slots: int = 0
    land_count: int = 0
    land_cards: List[ContextCard] = field(default_factory=list)
    category_summary: Dict[str, DeckBuildCategorySummary] = field(default_factory=dict)
    
    def __post_init__(self):
        self.name = self.config.deck.name or "Unnamed Deck"
        
    def add_card(
        self,
        card: Union[MTGJSONSummaryCard, LandStub],
        reason: str,
        source: str,
        quantity: int = 1,
        score: Optional[float] = None,
    ) -> bool:
        """Add a card to the deck.
        
        Args:
            card: Card to add
            reason: Reason for adding
            source: Source of the card
            quantity: Number of copies
            
        Returns:
            True if card was added, False otherwise
        """
        # Check if card is already in deck
        card_name = str(getattr(card, 'name', ''))
        if not card_name:
            return False
            
        # Check singleton rule (except for basic lands)
        is_basic_land = getattr(card, 'is_basic_land', lambda: False)()
        if not is_basic_land and card_name in self.used_cards:
            return False
            
        # For basic lands, allow multiple copies even in singleton formats
        if is_basic_land:
            existing_card = None
            for context_card in self.cards:
                if context_card.name == card_name:
                    existing_card = context_card
                    break
            
            if existing_card:
                # Increment quantity of existing basic land
                existing_card.quantity += quantity
                self.deck.insert_card(card, quantity)
                self.log(f"Incremented {card_name} quantity to {existing_card.quantity} ({reason})")
                return True
            
        # Create context card
        context_card = ContextCard(
            card=card,
            reason=reason,
            source=source,
            quantity=quantity,
            score=score if score is not None else None,
        )
        
        # Add to deck
        self.deck.insert_card(card, quantity)
        
        # Add to context
        self.cards.append(context_card)
        if not is_basic_land:
            self.used_cards.add(card_name)
        
        # Log operation
        self.log(f"Added {quantity}x {card_name} ({reason})")
        
        return True
    @property
    def empty_slots(self) -> int:
        """Get the number of empty slots in the deck."""
        return self.config.deck.size - self.get_total_cards()
    
    def get_total_cards(self) -> int:
        """Get total number of cards in the deck (including quantities)."""
        return sum(card.quantity for card in self.cards)
        
    def get_card_quantity(self, card_name: str) -> int:
        """Get the quantity of a specific card in the deck."""
        for card in self.cards:
            if card.name == card_name:
                return card.quantity
        return 0
        
    def log(self, msg: str) -> None:
        """Record an operation or decision in the build log."""
        timestamp = datetime.now().isoformat()
        self.operations.append(f"{timestamp}: {msg}")
        
    def record_unmet_condition(self, condition: str) -> None:
        """Record a failed constraint or unmet rule."""
        self.unmet_conditions.append(condition)
        self.log(f"Unmet condition: {condition}")
        
    def get_card_names(self) -> List[str]:
        """Get list of card names in the deck."""
        return [c.name for c in self.cards]
        
    def get_active_cards(self) -> List[ContextCard]:
        """Get list of cards that haven't been replaced."""
        return [c for c in self.cards if not c.replaced_at]
        
    def get_replaced_cards(self) -> List[ContextCard]:
        """Get list of cards that were replaced."""
        return [c for c in self.cards if c.replaced_at]
        
    def get_cards_by_source(self, source: str) -> List[ContextCard]:
        """Get all cards added by a specific source."""
        return [c for c in self.cards if c.source == source]
        
    def get_cards_by_reason(self, reason_pattern: str) -> List[ContextCard]:
        """Get all cards matching a reason pattern."""
        return [c for c in self.cards if reason_pattern in c.reason]
        
    def export_summary(self) -> Dict[str, Any]:
        """Get serializable summary of the deck build process."""
        return {
            "name": self.name,
            "cards": [c.to_dict() for c in self.cards],
            "replaced_cards": [c.to_dict() for c in self.get_replaced_cards()],
            "stats": {
                "start_time": datetime.now(),
                "cards_added": self.get_total_cards(),
                "cards_replaced": len(self.get_replaced_cards()),
                "unmet_conditions": len(self.unmet_conditions),
                "category_fills": {},
                "source_counts": {},
                "replacement_reasons": {}
            },
            "unmet_conditions": self.unmet_conditions,
            "logs": self.operations,
            "meta": {
                "scoring_rules": self.config.scoring_rules or {},
                "categories": self.config.categories or {},
                "card_constraints": self.config.card_constraints or {},
                "mana_base": self.config.mana_base or {},
                "mana_curve": self.config.deck.mana_curve or {},
                "fallback_strategy": self.config.fallback_strategy or ""
            },
            "total_cards": self.get_total_cards()
        }
        
    def clear(self) -> None:
        """Reset the build context."""
        self.cards.clear()
        self.operations.clear()
        self.unmet_conditions.clear()
        self.deck = Deck(name=self.name)
        self.scored_cards.clear()
        self.used_cards.clear()
        self.land_count = 0
        self.land_cards.clear()
        
    def get_color_counts(self) -> Dict[str, int]:
        """Get counts of each color in the deck, counting each unique card once."""
        color_counts = {}
        for card in self.cards:
            if not card.card:
                continue
            for color in card.card.color_identity:
                color_counts[color] = color_counts.get(color, 0) + 1
        return color_counts
        
    def log_card_counts(self, label: str) -> None:
        """Log total cards, unique cards, and color counts with a label."""
        total = self.get_total_cards()
        unique = len(self.cards)
        color_counts = self.get_color_counts()
        self.log(f"[{label}] Total cards: {total}, Unique: {unique}, Color counts: {color_counts}")
    
    def add_land_card(self, card: Union[MTGJSONSummaryCard, LandStub], reason: str, source: str, quantity: int = 1) -> bool:
        """Add a land card to the deck."""
        # Check if card is already in deck
        card_name = str(getattr(card, 'name', ''))
        if not card_name:
            return False
            
        # For basic lands, allow multiple copies even in singleton formats
        is_basic_land = getattr(card, 'is_basic_land', lambda: False)()
        if is_basic_land:
            # Basic lands can have multiple copies
            existing_card = None
            for context_card in self.cards:
                if context_card.name == card_name:
                    existing_card = context_card
                    break
            
            if existing_card:
                # Increment quantity of existing basic land
                existing_card.quantity += quantity
                self.deck.insert_card(card, quantity)
                self.land_count += quantity
                self.log(f"Incremented {card_name} quantity to {existing_card.quantity} ({reason})")
                return True
        else:
            # Non-basic lands follow singleton rule
            if card_name in self.used_cards:
                return False
            
        # Create context card
        context_card = ContextCard(
            card=card,
            reason=reason,
            source=source,
            quantity=quantity
        )
        
        # Add to deck
        self.deck.insert_card(card, quantity)
        
        # Add to context
        self.cards.append(context_card)
        if not is_basic_land:
            self.used_cards.add(card_name)
        
        # Update land count
        self.land_count += quantity
        self.land_cards.append(context_card)
        
        # Log operation
        self.log(f"Added {quantity}x {card_name} as land ({reason})")
        
        return True
        
    def get_land_count(self) -> int:
        """Get the number of land cards in the deck."""
        # Count lands by checking actual card types, not just the tracked count
        land_count = 0
        for card in self.cards:
            # Check if it's a land by using the appropriate method/attribute
            try:
                if hasattr(card.card, 'matches_type') and card.card.is_land():
                    land_count += card.quantity
                elif hasattr(card.card, 'types') and 'Land' in (card.card.types or []):
                    land_count += card.quantity
            except (AttributeError, TypeError):
                # Skip cards that don't have the expected attributes
                continue
        return land_count
    
    def get_land_cards(self) -> List[ContextCard]:
        """Get the land cards in the deck."""
        return self.land_cards

@dataclass
class BuildContext:
    """Context for deck building process."""
    
    deck_config: DeckConfig
    summary_repo: SummaryCardRepository
    callbacks: Optional[Dict[str, Any]] = None
    deck_build_context: Optional[DeckBuildContext] = None
    
    @property
    def config(self) -> DeckConfig:
        """Get the deck configuration."""
        return self.deck_config
        
    @property
    def deck_meta(self) -> DeckMeta:
        """Get the deck metadata."""
        return self.deck_config.deck
        
    @property
    def categories(self) -> Dict[str, CategoryDefinition]:
        """Get the category definitions."""
        return self.deck_config.categories
        
    @property
    def card_constraints(self) -> Optional[CardConstraintMeta]:
        """Get the card constraints."""
        return self.deck_config.card_constraints
        
    @property
    def priority_cards(self) -> Optional[List[PriorityCardEntry]]:
        """Get the priority cards."""
        return self.deck_config.priority_cards
        
    @property
    def scoring_rules(self) -> Optional[ScoringRulesMeta]:
        """Get the scoring rules."""
        return self.deck_config.scoring_rules
        
    @property
    def mana_base(self) -> Optional[ManaBaseMeta]:
        """Get the mana base configuration."""
        return self.deck_config.mana_base
        
    @property
    def fallback_strategy(self) -> Optional[FallbackStrategyMeta]:
        """Get the fallback strategy."""
        return self.deck_config.fallback_strategy
        
    @property
    def name(self) -> str:
        """Get the deck name."""
        return self.deck_meta.name or "Unnamed Deck"
        
    @property
    def colors(self) -> List[str]:
        """Get the deck colors."""
        return self.deck_meta.colors
        
    @property
    def color_match_mode(self) -> str:
        """Get the color match mode."""
        return self.deck_meta.color_match_mode
        
    @property
    def size(self) -> int:
        """Get the deck size."""
        return self.deck_meta.size
        
    @property
    def max_card_copies(self) -> int:
        """Get the maximum number of copies per card."""
        return self.deck_meta.max_card_copies
        
    @property
    def allow_colorless(self) -> bool:
        """Get whether colorless cards are allowed."""
        return self.deck_meta.allow_colorless
        
    @property
    def legalities(self) -> List[str]:
        """Get the legal formats."""
        return self.deck_meta.legalities
        
    @property
    def owned_cards_only(self) -> bool:
        """Get whether only owned cards are allowed."""
        return self.deck_meta.owned_cards_only
        
    @property
    def mana_curve(self) -> Optional[ManaCurveMeta]:
        """Get the mana curve configuration."""
        return self.deck_meta.mana_curve 