# mtg_deck_builder/deck_config/deck_config.py

"""
Deck configuration models and YAML utilities for Magic: The Gathering deck builder.

This module defines Pydantic models for deck configuration, categories, constraints, scoring, and mana base.
It also provides YAML import/export utilities for deck configuration files.

Classes:
    DeckMeta: Metadata for a deck configuration.
    CategoryDefinition: Definition for a deck category (e.g., removal, ramp).
    PriorityCardEntry: Entry for a priority card to include in the deck.
    RarityBoostMeta: Configuration for boosting rarities in deck selection.
    CardConstraintMeta: Constraints for card selection in deck building.
    SpecialLandsMeta: Configuration for special lands in the mana base.
    ManaBaseMeta: Mana base configuration for the deck.
    ScoringRulesMeta: Scoring rules for evaluating cards during deck building.
    FallbackStrategyMeta: Fallback strategy for filling the deck if targets are not met.
    DeckConfig: Main configuration class for deck building.

"""
from pathlib import Path
from typing import Any, ClassVar, Dict, List, Literal, Optional, Union

import yaml
from pydantic import BaseModel, Field, field_validator


class PriorityCardEntry(BaseModel):
    """
    Entry for a priority card to include in the deck.

    Attributes:
        name: Card name.
        min_copies: Minimum copies to include.
    """

    name: str
    min_copies: int = 1


class ManaCurveMeta(BaseModel):
    """
    Mana curve configuration for the deck.

    Attributes:
        min: Minimum mana value.
        max: Maximum mana value.
        curve_shape: Shape of the curve (bell, linear, flat).
        curve_slope: Slope of the curve (up, down, flat).
    """

    min: int = 0
    max: int = 0
    curve_shape: str = "bell"  # Options: bell, linear, flat
    curve_slope: str = "down"  # Options: up, down, flat


class InventoryMeta(BaseModel):
    """
    Inventory configuration for the deck.
    """

    inventory_file: str = ""
    owned_cards_only: bool = True


class DeckMeta(BaseModel):
    """Metadata for a deck configuration."""

    name: Optional[str] = None
    colors: List[str] = Field(default_factory=list)
    color_match_mode: Literal["exact", "subset", "any"] = "subset"
    size: int = Field(60, ge=1, le=250)
    max_card_copies: int = Field(4, ge=1, le=99)
    allow_colorless: bool = True
    legalities: List[str] = Field(default_factory=list)
    owned_cards_only: bool = True
    commander: Optional[str] = None
    mana_curve: ManaCurveMeta = Field(default_factory=ManaCurveMeta)

    @field_validator("colors", mode="before")
    @classmethod
    def normalize_colors(cls, v: Any) -> List[str]:
        if isinstance(v, list):
            return [str(c).upper() for c in v]
        return v

    def model_dump(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """
        Dump the model as a dictionary, excluding inventory_file.

        Args:
            *args: Positional arguments for model_dump.
            **kwargs: Keyword arguments for model_dump.

        Returns:
            Model dictionary.
        """
        exclude = kwargs.pop("exclude", set())
        exclude = set(exclude) | {"inventory_file"}
        return super().model_dump(*args, exclude=exclude, **kwargs)


class CategoryDefinition(BaseModel):
    """
    Definition for a deck category (e.g., removal, ramp).

    Attributes:
        target: Target number of cards in this category.
        preferred_keywords: Keywords to prioritize.
        priority_text: Text or regex patterns to prioritize.
        preferred_basic_type_priority: List of basic card types to prioritize.
    """

    target: int = 0
    min: int = 0
    preferred_keywords: List[str] = Field(default_factory=list)
    priority_text: List[str] = Field(default_factory=list)
    preferred_basic_type_priority: List[str] = Field(default_factory=list)


class RarityBoostMeta(BaseModel):
    """
    Configuration for boosting rarities in deck selection.

    Attributes:
        common: Boost for common cards.
        uncommon: Boost for uncommon cards.
        rare: Boost for rare cards.
        mythic: Boost for mythic cards.
    """

    common: int = 0
    uncommon: int = 0
    rare: int = 0
    mythic: int = 0


class CardConstraintMeta(BaseModel):
    """
    Constraints for card selection in deck building.

    Attributes:
        rarity_boost: Rarity boost configuration.
        exclude_keywords: Keywords to exclude.
    """

    rarity_boost: RarityBoostMeta = Field(default_factory=RarityBoostMeta)
    exclude_keywords: List[str] = Field(default_factory=list)


class SpecialLandsMeta(BaseModel):
    """
    Configuration for special lands in the mana base.

    Attributes:
        count: Number of special lands to include.
        prefer: Preferred special lands.
        avoid: Special lands to avoid.
    """

    count: int = 0
    prefer: List[str] = Field(default_factory=list)
    avoid: List[str] = Field(default_factory=list)


class ManaBaseMeta(BaseModel):
    """
    Mana base configuration for the deck.

    Attributes:
        land_count: Total number of lands.
        special_lands: Special lands configuration.
        balance: Mana balance configuration.
    """

    land_count: int = 24
    special_lands: SpecialLandsMeta = Field(default_factory=SpecialLandsMeta)
    balance: Dict[str, bool] = Field(
        default_factory=lambda: {"adjust_by_mana_symbols": True}
    )


class ScoringRulesMeta(BaseModel):
    """
    Scoring rules for evaluating cards during deck building.

    Attributes:
        keyword_abilities: Ability keyword to weight mapping.
        keyword_actions: Action keyword to weight mapping.
        ability_words: Ability word to weight mapping.
        text_matches: Text/regex to weight mapping.
        type_bonus: Type bonuses (basic_types, sub_types, super_types).
        rarity_bonus: Rarity to bonus mapping.
        mana_penalty: Mana penalty configuration.
        min_score_to_flag: Minimum score to flag a card.
    """

    keyword_abilities: Dict[str, int] = Field(default_factory=dict)
    keyword_actions: Dict[str, int] = Field(default_factory=dict)
    ability_words: Dict[str, int] = Field(default_factory=dict)
    text_matches: Dict[str, int] = Field(default_factory=dict)
    type_bonus: Dict[str, Dict[str, int]] = Field(default_factory=dict)
    rarity_bonus: Dict[str, int] = Field(default_factory=dict)
    mana_penalty: Dict[str, int] = Field(
        default_factory=lambda: {"threshold": 5, "penalty_per_point": 1}
    )
    min_score_to_flag: int = 0


class FallbackStrategyMeta(BaseModel):
    """
    Fallback strategy for filling the deck if targets are not met.

    Attributes:
        fill_with_any: Fill with any card if needed.
        fill_priority: Priority categories for filling.
        allow_less_than_target: Allow fewer cards than target.
    """

    fill_with_any: bool = False
    fill_priority: List[str] = Field(default_factory=list)
    allow_less_than_target: bool = False


class DeckConfig(BaseModel):
    """Main configuration class for deck building."""

    seed: Optional[str] = None
    deck: DeckMeta
    categories: Dict[str, CategoryDefinition] = Field(default_factory=dict)
    card_constraints: CardConstraintMeta = Field(default_factory=CardConstraintMeta)
    priority_cards: List[PriorityCardEntry] = Field(default_factory=list)
    scoring_rules: ScoringRulesMeta = Field(default_factory=ScoringRulesMeta)
    mana_base: ManaBaseMeta = Field(default_factory=ManaBaseMeta)
    fallback_strategy: FallbackStrategyMeta = Field(
        default_factory=FallbackStrategyMeta
    )

    @classmethod
    def from_yaml(cls, path_or_str: Union[str, Path]) -> "DeckConfig":
        """
        Create a DeckConfig from a YAML file or string.

        Args:
            path_or_str: Path to YAML file or YAML string.

        Returns:
            DeckConfig instance.

        Raises:
            FileNotFoundError: If path_or_str is a file path that doesn't exist.
            yaml.YAMLError: If YAML parsing fails.
        """
        if isinstance(path_or_str, (str, Path)):
            path = Path(path_or_str)
            if path.exists():
                with open(path, "r") as f:
                    data = yaml.safe_load(f)
            else:
                raise FileNotFoundError(f"YAML file not found: {path}")
        else:
            data = yaml.safe_load(path_or_str)
        return cls(**data)

    def to_yaml(self, path: Optional[Union[str, Path]] = None) -> Optional[str]:
        """
        Convert the configuration to YAML.

        Args:
            path: Optional path to write the YAML to.

        Returns:
            YAML string if path is None, None otherwise.
        """
        data = self.model_dump(exclude_none=True)
        yaml_str = yaml.dump(data, default_flow_style=False)
        if path:
            with open(path, "w") as f:
                f.write(yaml_str)
            return None
        return yaml_str

    def to_json(self, path: Optional[Union[str, Path]] = None) -> str:
        """
        Convert the configuration to a JSON string and optionally save to a file.

        Args:
            path: Optional path to save the JSON file.

        Returns:
            JSON string representation of the configuration.
        """
        import json

        data = self.model_dump(exclude_none=True)
        json_str = json.dumps(data, indent=2)
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(json_str)
        return json_str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DeckConfig":
        """Create a DeckConfig from a dictionary.

        Args:
            data: Dictionary containing deck configuration

        Returns:
            DeckConfig object

        Raises:
            ValueError: If data is invalid
        """
        try:
            return cls.model_validate(data)
        except Exception as e:
            raise ValueError(f"Invalid deck configuration: {e}")

    @property
    def name(self) -> str:
        """Get the name of the deck."""
        return self.deck.name or ""

    @property
    def colors(self) -> List[str]:
        """Get the colors of the deck."""
        return self.deck.colors

    @property
    def size(self) -> int:
        """Get the size of the deck."""
        return self.deck.size

    @property
    def max_card_copies(self) -> int:
        """Get the maximum number of copies of a card in the deck."""
        return self.deck.max_card_copies

    @property
    def mana_curve(self) -> Optional[ManaCurveMeta]:
        """Get the mana curve of the deck."""
        return self.deck.mana_curve

    @property
    def legalities(self) -> List[str]:
        """Get the legalities of the deck."""
        return self.deck.legalities

    @property
    def owned_cards_only(self) -> bool:
        """Get whether only owned cards are allowed."""
        return self.deck.owned_cards_only

    @property
    def color_match_mode(self) -> str:
        """Get the color match mode of the deck."""
        return self.deck.color_match_mode

    @property
    def color_identity(self) -> List[str]:
        """Get the color identity of the deck."""
        return self.deck.colors

    @property
    def allow_colorless(self) -> bool:
        """Get whether colorless cards are allowed."""
        return self.deck.allow_colorless

    @property
    def commander(self) -> Optional[str]:
        """Get the commander of the deck."""
        return self.deck.commander
