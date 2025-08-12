from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from mtg_deck_builder.db.repository import SummaryCardRepository
from mtg_deck_builder.models.deck import Deck
from mtg_deck_builder.models.deck_exporter import DeckExporter
from mtg_deck_builder.utils.arena_parser import parse_arena_export


@dataclass
class ArenaParseResult:
    main: Dict[str, int]
    sideboard: Optional[Dict[str, int]]
    warnings: List[str]


@dataclass
class ResolutionReport:
    missing: List[str]
    resolved: List[str]


def parse_arena_export_text(text: str) -> ArenaParseResult:
    lines = text.strip().splitlines()
    parsed = parse_arena_export(lines)
    return ArenaParseResult(main=parsed.get("main", {}), sideboard=parsed.get("sideboard"), warnings=[])


def build_deck_from_arena(
    text: str,
    repo: SummaryCardRepository,
    deck_name: str = "Imported Deck",
) -> Tuple[Deck, ResolutionReport]:
    parsed = parse_arena_export_text(text)
    missing: List[str] = []
    resolved: List[str] = []

    deck = Deck(name=deck_name, session=repo.session)
    for name, qty in parsed.main.items():
        card = repo.find_by_name(name, exact=True)
        if not card:
            missing.append(name)
            continue
        deck.insert_card(card, quantity=qty)
        resolved.append(name)

    return deck, ResolutionReport(missing=missing, resolved=resolved)


def deck_to_arena(deck: Deck) -> str:
    return DeckExporter(deck).mtg_arena_import()


