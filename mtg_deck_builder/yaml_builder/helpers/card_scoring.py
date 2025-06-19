"""Card scoring and evaluation logic.

This module provides functions for scoring cards based on various criteria:
- Keyword abilities and actions
- Text pattern matches
- Type bonuses
- Rarity bonuses
- Mana cost penalties
"""

import logging
import re
from typing import List, Optional, Union, Any
from mtg_deck_builder.models.deck_config import ScoringRulesMeta
from mtg_deck_builder.yaml_builder.deck_build_classes import (
    DeckBuildContext,
    ContextCard,
    LandStub,
)
from mtg_deck_builder.db.mtgjson_models.cards import MTGJSONSummaryCard
from mtg_deck_builder.yaml_builder.types import ScoredCard

logger = logging.getLogger(__name__)


def _match_priority_text(card: Any, patterns: List[str]) -> bool:
    """Check if card text matches any priority patterns.

    Args:
        card: Card object to check
        patterns: List of text patterns to match against

    Returns:
        True if any pattern matches, False otherwise
    """
    if not patterns:
        return False

    # Handle None text safely
    text = getattr(card, "text", "") or ""
    text = text.lower()

    for pattern in patterns:
        if pattern.startswith("/") and pattern.endswith("/"):
            # Handle regex pattern
            try:
                regex = re.compile(pattern[1:-1], re.IGNORECASE)
                if regex.search(text):
                    return True
            except re.error:
                logger.warning(f"Invalid regex pattern: {pattern}")
                continue
        elif pattern.lower() in text:
            return True

    return False


def score_card(
    card: Union[MTGJSONSummaryCard, LandStub, ContextCard],
    scoring_rules: Optional[ScoringRulesMeta],
    context: Optional[DeckBuildContext] = None,
) -> ScoredCard:
    """Score a card based on scoring rules and context."""
    scored_card = ScoredCard(card=card, score=0)
    if not scoring_rules:
        return scored_card

    score = 0

    # Handle ContextCard type
    if isinstance(card, ContextCard):
        card = card.card

    # Handle LandStub type
    if isinstance(card, LandStub):
        # Basic lands get a base score
        if card.name.lower() in ["forest", "mountain", "plains", "island", "swamp"]:
            scored_card.increase_score(
                score=1, source="score_card", reason="Basic land"
            )
        return scored_card

    # Handle MTGJSONSummaryCard type
    if not isinstance(card, MTGJSONSummaryCard):
        return ScoredCard(card=card, score=score)

    # Score based on keyword abilities
    if scoring_rules.keyword_abilities:
        for keyword, weight in scoring_rules.keyword_abilities.items():
            if keyword.lower() in (getattr(card, "keywords", []) or []):
                scored_card.increase_score(
                    score=int(weight),
                    source="score_card",
                    reason=f"Keyword ability: {keyword}",
                )

    # Score based on keyword actions
    if scoring_rules.keyword_actions:
        for keyword, weight in scoring_rules.keyword_actions.items():
            if keyword.lower() in (getattr(card, "keywords", []) or []):
                scored_card.increase_score(
                    score=int(weight),
                    source="score_card",
                    reason=f"Keyword action: {keyword}",
                )

    # Score based on ability words
    if scoring_rules.ability_words:
        for keyword, weight in scoring_rules.ability_words.items():
            if keyword.lower() in (getattr(card, "keywords", []) or []):
                scored_card.increase_score(
                    score=int(weight),
                    source="score_card",
                    reason=f"Ability word: {keyword}",
                )

    # Score based on text matches
    if scoring_rules.text_matches:
        for pattern, weight in scoring_rules.text_matches.items():
            if pattern.startswith("/") and pattern.endswith("/"):
                # Handle regex pattern
                try:
                    if re.search(
                        pattern[1:-1],
                        getattr(card, "oracle_text", "") or "",
                        re.IGNORECASE,
                    ):
                        scored_card.increase_score(
                            score=int(weight),
                            source="score_card",
                            reason=f"Text match: {pattern}",
                        )
                except re.error:
                    continue
            elif pattern.lower() in (getattr(card, "oracle_text", "") or "").lower():
                scored_card.increase_score(
                    score=int(weight),
                    source="score_card",
                    reason=f"Text match: {pattern}",
                )

    # Score based on card types
    if scoring_rules.type_bonus:
        # Basic type bonus
        for type_, weight in scoring_rules.type_bonus.get("basic_types", {}).items():
            if type_.lower() in [t.lower() for t in (getattr(card, "types", []) or [])]:
                scored_card.increase_score(
                    score=int(weight),
                    source="score_card",
                    reason=f"Type bonus: {type_}",
                )
        # Sub type bonus
        for type_, weight in scoring_rules.type_bonus.get("sub_types", {}).items():
            if type_.lower() in [t.lower() for t in (getattr(card, "types", []) or [])]:
                scored_card.increase_score(
                    score=int(weight),
                    source="score_card",
                    reason=f"Type bonus: {type_}",
                )
        # Super type bonus
        for type_, weight in scoring_rules.type_bonus.get("super_types", {}).items():
            if type_.lower() in [t.lower() for t in (getattr(card, "types", []) or [])]:
                scored_card.increase_score(
                    score=int(weight),
                    source="score_card",
                    reason=f"Type bonus: {type_}",
                )

    # Score based on rarity
    if scoring_rules.rarity_bonus and getattr(card, "rarity", None):
        for rarity, weight in scoring_rules.rarity_bonus.items():
            if rarity.lower() == getattr(card, "rarity", "").lower():
                scored_card.increase_score(
                    score=int(weight),
                    source="score_card",
                    reason=f"Rarity bonus: {rarity}",
                )

    # Apply mana cost penalties
    if scoring_rules.mana_penalty and getattr(card, "converted_mana_cost", None):
        threshold = scoring_rules.mana_penalty.get("threshold", 5)
        penalty_per_point = scoring_rules.mana_penalty.get("penalty_per_point", 1)
        cmc = float(getattr(card, "converted_mana_cost", 0) or 0)
        if cmc > threshold:
            scored_card.increase_score(
                score=-int((cmc - threshold) * penalty_per_point),
                source="score_card",
                reason=f"Mana cost penalty: {cmc}",
            )

    return scored_card
