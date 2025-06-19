"""Card metadata and type definitions.

This module provides utilities for working with card types, subtypes, and supertypes.
It includes functions for loading and validating card type data from MTGJSON.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Set, Optional, Any
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Path to card types data
CARDTYPES_PATH = Path('data/mtgjson/CardTypes.json')

# CardTypes.json models
class TypeEntry(BaseModel):
    subTypes: List[str] = Field(default_factory=list)
    superTypes: List[str] = Field(default_factory=list)

class CardTypesData(BaseModel):
    meta: Dict[str, str] = Field(default_factory=dict)
    data: Dict[str, TypeEntry] = Field(default_factory=dict)

    def get_subtypes(self, card_type: str) -> List[str]:
        """Get subtypes for a given card type."""
        entry = self.data.get(card_type.lower())
        return entry.subTypes if entry else []

    def get_supertypes(self, card_type: str) -> List[str]:
        """Get supertypes for a given card type."""
        entry = self.data.get(card_type.lower())
        return entry.superTypes if entry else []

    def all_types(self) -> List[str]:
        """Get all available card types."""
        return list(self.data.keys())

# Keywords.json models
class KeywordsData(BaseModel):
    meta: Dict[str, str] = Field(default_factory=dict)
    data: Dict[str, List[str]] = Field(default_factory=dict)

    def get_ability_words(self) -> List[str]:
        """Get all ability words."""
        return self.data.get("abilityWords", [])

    def get_keyword_abilities(self) -> List[str]:
        """Get all keyword abilities."""
        return self.data.get("keywordAbilities", [])

    def get_keyword_actions(self) -> List[str]:
        """Get all keyword actions."""
        return self.data.get("keywordActions", [])

    def is_keyword_ability(self, keyword: str) -> bool:
        """Check if a given keyword is a keyword ability."""
        return keyword in self.get_keyword_abilities()

    def is_keyword_action(self, keyword: str) -> bool:
        """Check if a given keyword is a keyword action."""
        return keyword in self.get_keyword_actions()

    def is_ability_word(self, keyword: str) -> bool:
        """Check if a given keyword is an ability word."""
        return keyword in self.get_ability_words()

# Loader utilities
def load_card_types(path: Path) -> CardTypesData:
    """Load card types data from MTGJSON file.
    
    Args:
        path: Path to the card types JSON file
        
    Returns:
        CardTypesData object containing card type definitions
        
    Raises:
        FileNotFoundError: If the card types file doesn't exist
        json.JSONDecodeError: If the file contains invalid JSON
    """
    try:
        with open(path, 'r', encoding='utf-8') as f:
            raw = json.load(f)
        return CardTypesData.model_validate(raw)
    except FileNotFoundError:
        logger.error(f"Card types file not found at {path}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in card types file: {e}")
        raise

def load_keywords(path: Path) -> KeywordsData:
    """Load keywords data from MTGJSON file.
    
    Args:
        path: Path to the keywords JSON file
        
    Returns:
        KeywordsData object containing keyword definitions
        
    Raises:
        FileNotFoundError: If the keywords file doesn't exist
        json.JSONDecodeError: If the file contains invalid JSON
    """
    try:
        with open(path, 'r', encoding='utf-8') as f:
            raw = json.load(f)
        return KeywordsData.model_validate(raw)
    except FileNotFoundError:
        logger.error(f"Keywords file not found at {path}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in keywords file: {e}")
        raise 