import random
from typing import List, Dict, Optional, Set, Tuple, Any, Union, TYPE_CHECKING
from pathlib import Path
import pandas as pd
import json
from sqlalchemy.orm import Session
import logging
from mtg_deck_builder.db import get_card_types, get_keywords
from mtg_deck_builder.models.deck_config import DeckConfig, DeckMeta
from mtg_deck_builder.yaml_builder.types import LandStub

from mtg_deck_builder.models.card_meta import load_card_types, load_keywords
if TYPE_CHECKING:
    from mtg_deck_builder.models.card_meta import CardTypesData, KeywordsData
    from mtg_deck_builder.db.repository import CardRepository, SummaryCardRepository
    from mtg_deck_builder.db.mtgjson_models.cards import MTGJSONSummaryCard

logger = logging.getLogger(__name__)

def load_json(path):
    with open(path, 'r') as f:
        return json.load(f)

class Deck:
    """
    Represents a Magic: The Gathering deck, with analysis and utility methods.
    Stores cards as a dictionary and tracks quantities in a separate inventory dictionary.
    Provides methods for deck statistics, color analysis, mana curve, and export.
    """
    session: Optional[Session] = None
    name: str = ""
    _keywords: 'KeywordsData' = get_keywords()
    _card_types: 'CardTypesData' = get_card_types()


    def __init__(self, cards: Optional[Union[Dict[str, 'MTGJSONSummaryCard'], List['MTGJSONSummaryCard']]] = None, 
                 session: Optional[Session] = None, 
                 name: str = "",
                 config: Optional[DeckConfig] = None):
        self.session: Optional[Session] = session
        self.name: str = name
        self.config: Optional[DeckConfig] = config  # Placeholder for DeckConfig, if needed
        self.cards: Dict[str, Union['MTGJSONSummaryCard', 'LandStub']] = {}
        self.inventory: Dict[str, int] = {}
        logger.debug(f"Deck constructor called with cards type: {type(cards)}")
        if isinstance(cards, dict):
            logger.debug(f"Cards dict keys: {list(cards.keys())}")
        elif isinstance(cards, list):
            logger.debug(f"Cards list length: {len(cards)}")
            if cards:
                logger.debug(f"First card type: {type(cards[0])}")
                logger.debug(f"First card: {cards[0]}")
        if cards is None:
            self._cards = {}
            self._inventory = {}
        elif isinstance(cards, dict):
            self._cards = cards
            self._inventory = {name: 1 for name in cards.keys()}
        elif isinstance(cards, list):
            self._cards = {card.name: card for card in cards}
            self._inventory = {card.name: 1 for card in cards}
        else:
            raise ValueError("cards must be a dict or a list of CardDB")
        logger.debug(f"Deck initialized with {len(self._cards)} cards: {list(self._cards.keys())}")

    @property
    def keywords(self) -> 'KeywordsData':
        """Lazily load keywords data."""
        return self._keywords   

    @property
    def card_types(self) -> 'CardTypesData':
        """Lazily load card types data."""
        return self._card_types

    def __repr__(self) -> str:
        """
        Returns an informative string representation of the deck.
        """
        num_unique_cards = len(self._cards)
        total_cards = self.size()
        return f"<Deck(name='{self.name}', unique_cards={num_unique_cards}, total_cards={total_cards})>"

    @classmethod
    def from_repo(cls, repo: 'SummaryCardRepository', name: str, limit: int = 60, random_cards: bool = True) -> 'Deck':
        """
        Create a Deck from a SummaryCardRepository, optionally limiting and shuffling cards.

        Args:
            repo (SummaryCardRepository): Source repository.
            limit (int): Maximum number of cards to include.
            random_cards (bool): Shuffle cards before selection.
        Returns:
            Deck: New Deck instance.
        """
        all_cards = repo.get_all_cards()
        if not all_cards:
            raise ValueError("No cards found in the repository.")
        if random_cards:
            random.shuffle(all_cards)
            
        selected = all_cards[:limit] if limit else all_cards
        cards_dict = {str(card.name): card for card in selected}
        inventory = {str(card.name): 1 for card in selected}
        deck_config = DeckConfig(deck=DeckMeta(name=name, size=limit))
        deck = cls(cards=cards_dict, session=repo.session, config=deck_config, name=name)
        deck._inventory = inventory
        return deck

    def insert_card(self, card: Union['MTGJSONSummaryCard', 'LandStub'], quantity: int = 1) -> None:
        """
        Inserts a card into the deck with the specified quantity.

        Args:
            card: Card to insert
            quantity: Number of copies to add.
        """
        if card.name in self.cards:
            # If card exists, add to its quantity
            self.inventory[str(card.name)] += quantity
        else:
            # If card doesn't exist, add it with its quantity
            self.cards[str(card.name)] = card
            self.inventory[str(card.name)] = quantity

    def get_quantity(self, card_name: str) -> int:
        """
        Get the quantity of a card in the deck.

        Args:
            card_name (str): Name of the card.
        Returns:
            int: Quantity of the card in the deck.
        """
        return self.inventory.get(card_name, 0)

    def sample_hand(self, hand_size: int = 7) -> List['MTGJSONSummaryCard']:
        """
        Draws a random selection of `hand_size` cards from the deck.

        Args:
            hand_size (int): Number of cards to draw.
        Returns:
            List[CardDB]: List of drawn cards.
        """
        deck_list = [card for card in self.cards.values() for _ in range(self.get_quantity(str(card.name)))]
        if hand_size > len(deck_list):
            raise ValueError("Hand size exceeds the number of cards in the deck.")
        return random.sample(deck_list, hand_size)

    def size(self) -> int:
        """
        Returns the total number of cards in the deck, considering quantities.

        Returns:
            int: Total number of cards in the deck.
        """
        return sum(self.inventory.values())

    def cards_by_type(self, type_match: str) -> List['MTGJSONSummaryCard']:
        """
        Return a list of cards that match a specific type (case-insensitive substring match).
        """
        type_match = type_match.lower()
        return [card for card in self.cards.values() if type_match in (getattr(card, "types", "") or "").lower()]

    def search_cards(self, text: str) -> List['MTGJSONSummaryCard']:
        """
        Return all cards containing a text fragment (case-insensitive, in card name or text).
        """
        text = text.lower()
        return [card for card in self.cards.values()
                if text in (getattr(card, "name", "") or "").lower() or text in (getattr(card, "oracle_text", "") or "").lower()]

    def to_dict(self, eager: bool = False) -> Dict[str, Any]:
        """Convert deck to a dictionary representation.
        
        Args:
            eager: Whether to eagerly load relationships
            
        Returns:
            Dictionary containing deck data cards and quantities, config as well
        """
        # Store minimal card data - just name and quantity
        cards_dict = {
            name: {
                'name': card.name,
                'quantity': self.get_quantity(name)
            } for name, card in self.cards.items()
        }

        # Store minimal deck data
        deck_data = {
            'name': self.name,
            'cards': cards_dict,
            'config': self.config.model_dump() if self.config else None,
            'inventory': self.inventory,
            'keywords': self.keywords.model_dump() if self.keywords else None,
            'card_types': self.card_types.model_dump() if self.card_types else None,
            'size': self.size() if self.size() else None
        }
        
        return deck_data

    def to_json(self, path: Optional[Union[str, Path]] = None) -> Optional[str]:
        """Convert deck to JSON format.
        
        Args:
            path: Optional path to write the JSON to.
            
        Returns:
            JSON string if path is None, None otherwise.
        """
        import json
        data = self.to_dict(eager=True)  # Always eager load for full serialization
        json_str = json.dumps(data, indent=2)
        if path:
            with open(path, 'w') as f:
                f.write(json_str)
            return None
        return json_str

    @classmethod
    def from_dict(cls, data: Dict[str, Any], session) -> 'Deck':
        """Create a Deck instance from a dictionary.
        
        Args:
            data (Dict[str, Any]): Dictionary containing deck data
            session: SQLAlchemy session for database operations
            
        Returns:
            Deck: A new Deck instance with the data from the dictionary
        """
        from mtg_deck_builder.db.models import CardDB
        
        # Create deck instance
        deck = cls()
        deck.name = data['name']
        
        # Load cards from database using card_name
        cards_dict = {}
        for card_data in data['cards'].values():
            card = session.query(CardDB).get(card_data['name'])
            if card:
                cards_dict[card.name] = card
        
        deck._cards = cards_dict
        return deck

