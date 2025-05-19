# mtg_deck_builder/deck_config/deck_config.py

"""
Deck configuration models and YAML utilities for Magic: The Gathering deck builder.

Defines Pydantic models for deck configuration, categories, constraints, scoring, and mana base.
Provides YAML import/export utilities for deck configuration files.
"""
import yaml
from pathlib import Path
from typing import List, Dict, Optional
from pydantic import BaseModel, Field, validator


class DeckMeta(BaseModel):
    """
    Metadata for a deck configuration.

    Attributes:
        name (Optional[str]): Name of the deck.
        colors (List[str]): List of color codes for the deck.
        size (int): Deck size (default 60).
        max_card_copies (int): Maximum allowed copies per card.
        legalities (List[str]): List of legal formats.
        color_match_mode (str): Color identity match mode.
        allow_colorless (bool): Whether colorless cards are allowed.
        owned_cards_only (bool): Restrict to owned cards.
        mana_curve (Optional[dict]): Mana curve configuration.
        inventory_file (Optional[str]): Path to inventory file.
    """
    name: Optional[str]
    colors: List[str] = []
    size: int = 60
    max_card_copies: int = 4
    legalities: List[str] = []
    color_match_mode: str = "subset"
    allow_colorless: bool = False
    owned_cards_only: bool = True
    mana_curve: Optional[dict] = None  # min, max, curve_shape, curve_slope
    inventory_file: Optional[str] = None  # path or filename of inventory to use

    def model_dump(self, *args, **kwargs):
        """
        Dump the model as a dictionary, excluding inventory_file.

        Args:
            *args: Positional arguments for model_dump.
            **kwargs: Keyword arguments for model_dump.
        Returns:
            dict: Model dictionary.
        """
        exclude = kwargs.pop('exclude', set())
        exclude = set(exclude) | {'inventory_file'}
        return super().model_dump(*args, exclude=exclude, **kwargs)


class CategoryDefinition(BaseModel):
    """
    Definition for a deck category (e.g., removal, ramp).

    Attributes:
        target (int): Target number of cards in this category.
        preferred_keywords (List[str]): Keywords to prioritize.
        priority_text (List[str]): Text or regex patterns to prioritize.
    """
    target: int = 0
    preferred_keywords: List[str] = []
    priority_text: List[str] = []  # Each entry can be plain text or /regex/


class PriorityCardEntry(BaseModel):
    """
    Entry for a priority card to include in the deck.

    Attributes:
        name (str): Card name.
        min_copies (int): Minimum copies to include.
    """
    name: str
    min_copies: int = 1


class RarityBoostMeta(BaseModel):
    """
    Configuration for boosting rarities in deck selection.

    Attributes:
        common (int): Boost for common cards.
        uncommon (int): Boost for uncommon cards.
        rare (int): Boost for rare cards.
        mythic (int): Boost for mythic cards.
    """
    common: int = 0
    uncommon: int = 0
    rare: int = 0
    mythic: int = 0


class CardConstraintMeta(BaseModel):
    """
    Constraints for card selection in deck building.

    Attributes:
        rarity_boost (Optional[RarityBoostMeta]): Rarity boost configuration.
        exclude_keywords (List[str]): Keywords to exclude.
    """
    rarity_boost: Optional[RarityBoostMeta] = None
    exclude_keywords: List[str] = []


class SpecialLandsMeta(BaseModel):
    """
    Configuration for special lands in the mana base.

    Attributes:
        count (int): Number of special lands to include.
        prefer (List[str]): Preferred special lands.
        avoid (List[str]): Special lands to avoid.
    """
    count: int = 0
    prefer: List[str] = []
    avoid: List[str] = []


class ManaBaseMeta(BaseModel):
    """
    Mana base configuration for the deck.

    Attributes:
        land_count (int): Total number of lands.
        special_lands (Optional[SpecialLandsMeta]): Special lands configuration.
        balance (Optional[dict]): Mana balance configuration.
    """
    land_count: int = 22
    special_lands: Optional[SpecialLandsMeta] = None
    balance: Optional[dict] = None  # adjust_by_mana_symbols: bool


class ScoringRulesMeta(BaseModel):
    """
    Scoring rules for evaluating cards during deck building.

    Attributes:
        priority_text (Dict[str, int]): Text/regex to weight mapping.
        rarity_bonus (Dict[str, int]): Rarity to bonus mapping.
        mana_penalty (Optional[dict]): Mana penalty configuration.
        min_score_to_flag (Optional[int]): Minimum score to flag a card.
    """
    priority_text: Dict[str, int] = Field(default_factory=dict)  # key: plain text or /regex/, value: weight
    rarity_bonus: Dict[str, int] = Field(default_factory=dict)   # e.g. {"common": 0, "uncommon": 0, ...}
    mana_penalty: Optional[dict] = None  # {threshold: int, penalty_per_point: int}
    min_score_to_flag: Optional[int] = None


class FallbackStrategyMeta(BaseModel):
    """
    Fallback strategy for filling the deck if targets are not met.

    Attributes:
        fill_with_any (bool): Fill with any card if needed.
        fill_priority (List[str]): Priority categories for filling.
        allow_less_than_target (bool): Allow fewer cards than target.
    """
    fill_with_any: bool = False
    fill_priority: List[str] = Field(default_factory=list)
    allow_less_than_target: bool = False


class DeckConfig(BaseModel):
    """
    Main configuration class for deck building.

    Attributes:
        deck (DeckMeta): Deck metadata.
        categories (Dict[str, CategoryDefinition]): Category definitions.
        card_constraints (Optional[CardConstraintMeta]): Card constraints.
        priority_cards (Optional[List[PriorityCardEntry]]): Priority cards.
        scoring_rules (Optional[ScoringRulesMeta]): Scoring rules.
        mana_base (Optional[ManaBaseMeta]): Mana base configuration.
        fallback_strategy (Optional[FallbackStrategyMeta]): Fallback strategy.
    """
    deck: DeckMeta
    categories: Dict[str, CategoryDefinition] = Field(default_factory=dict)
    card_constraints: Optional[CardConstraintMeta] = None
    priority_cards: Optional[List[PriorityCardEntry]] = None
    scoring_rules: Optional[ScoringRulesMeta] = None
    mana_base: Optional[ManaBaseMeta] = None
    fallback_strategy: Optional[FallbackStrategyMeta] = None

    @classmethod
    def from_yaml(cls, path_or_str):
        """
        Load a DeckConfig from a YAML file or string.

        Args:
            path_or_str (str or Path): Path to YAML file or YAML string.
        Returns:
            DeckConfig: Loaded configuration.
        """
        if isinstance(path_or_str, (str, Path)) and Path(path_or_str).exists():
            with open(path_or_str, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
        elif isinstance(path_or_str, str):
            data = yaml.safe_load(path_or_str)
        else:
            raise ValueError("Invalid input for from_yaml")
        # Ensure categories is always a dict of CategoryDefinition
        if "categories" in data and isinstance(data["categories"], dict):
            data["categories"] = {k: CategoryDefinition(**v) if not isinstance(v, CategoryDefinition) else v for k, v in data["categories"].items()}
        return cls.model_validate(data)

    def as_dict(self):
        """
        Return the configuration as a dictionary, excluding inventory_file from export.

        Returns:
            dict: Configuration dictionary.
        """
        dct = self.model_dump()
        # Remove inventory_file from deck dict for export
        if "deck" in dct and "inventory_file" in dct["deck"]:
            dct["deck"].pop("inventory_file")
        return dct

    def to_yaml(self, path=None):
        """
        Export the configuration to a YAML string or file.

        Args:
            path (Optional[str or Path]): Path to write YAML file. If None, returns YAML string.
        Returns:
            str: YAML string if path is None.
        """
        data = self.as_dict()
        yaml_str = yaml.dump(data, sort_keys=False, allow_unicode=True)
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(yaml_str)
        return yaml_str

