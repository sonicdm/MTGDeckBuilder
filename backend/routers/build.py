from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, Optional, List
import logging

from fastapi import APIRouter, Depends, HTTPException
from backend.deps import get_db_url

from mtg_deck_builder.db import get_session
from mtg_deck_builder.db.repository import SummaryCardRepository
from mtg_deck_builder.models.deck_analyzer import DeckAnalyzer
from mtg_deck_builder.models.deck_exporter import DeckExporter
from mtg_deck_builder.yaml_builder.yaml_deckbuilder import build_deck_from_yaml


router = APIRouter(prefix="/api", tags=["build"])


def get_repo(db_url: str) -> SummaryCardRepository:
    with get_session(db_url=db_url) as session:
        return SummaryCardRepository(session)


def analyze_deck(deck) -> Dict[str, Any]:
    analyzer = DeckAnalyzer(deck)
    return analyzer.summary_dict()


class _MemoryLogHandler(logging.Handler):
    def __init__(self, store: List[str], level=logging.INFO) -> None:
        super().__init__(level)
        self.store = store
        self.formatter = logging.Formatter('%(levelname)s %(name)s: %(message)s')
    def emit(self, record: logging.LogRecord) -> None:
        try:
            self.store.append(self.format(record))
        except Exception:
            pass


@router.post("/build")
def build_endpoint(payload: Dict[str, Any], db_url: str = Depends(get_db_url)) -> Dict[str, Any]:
    yaml_text: Optional[str] = payload.get("yaml_text")
    deck_name: Optional[str] = payload.get("deck_name")
    debug: bool = bool(payload.get("debug", False))
    if not yaml_text or len(yaml_text) > 1_000_000:
        raise HTTPException(status_code=400, detail="yaml_text is required and must be <1MB")

    build_log: List[str] = []
    handler: Optional[_MemoryLogHandler] = None
    root_logger = logging.getLogger("mtg_deck_builder")
    prev_level = root_logger.level
    if debug:
        handler = _MemoryLogHandler(build_log, level=logging.DEBUG)
        root_logger.addHandler(handler)
        root_logger.setLevel(logging.DEBUG)

    with get_session(db_url=db_url) as session:
        repo = SummaryCardRepository(session)
        deck = build_deck_from_yaml(yaml_text, repo, verbose=debug)
        if handler is not None:
            root_logger.removeHandler(handler)
            root_logger.setLevel(prev_level)
        if deck is None:
            raise HTTPException(status_code=400, detail="Failed to build deck from YAML")
        if deck_name:
            deck.name = deck_name
        analysis = analyze_deck(deck)
        arena = DeckExporter(deck).mtg_arena_import()
        decklist = []
        # Try to access build context metadata if available
        card_reasons: Dict[str, List[str]] = {}
        build_context_summary: Dict[str, Any] = {}
        try:
            ctx = getattr(deck, '_build_context', None)
            if ctx:
                # Build a compact, serializable summary
                build_context_summary = {
                    "operations": list(getattr(ctx, 'operations', [])),
                    "unmet_conditions": list(getattr(ctx, 'unmet_conditions', [])),
                    "category_summary": {
                        k: {
                            "target": v.target,
                            "added": v.added,
                            "remaining": v.remaining,
                        } for k, v in getattr(ctx, 'category_summary', {}).items()
                    },
                }
                for cc in getattr(ctx, 'cards', []):
                    nm = str(getattr(getattr(cc, 'card', None), 'name', ''))
                    if not nm:
                        continue
                    reasons: List[str] = []
                    r = getattr(cc, 'reason', None)
                    if r:
                        reasons.append(str(r))
                    rs = getattr(cc, 'sources', None)
                    if rs:
                        reasons.extend([str(x) for x in rs])
                    card_reasons[nm] = reasons
        except Exception:
            pass

        total_creature_cards = 0
        total_creature_copies = 0
        for name, card in deck.cards.items():
            # Build a readable type line from MTGJSON data
            try:
                t_list = getattr(card, "types", None)
                if isinstance(t_list, list) and t_list:
                    type_line = " ".join([str(t) for t in t_list])
                else:
                    type_line = str(getattr(card, "type", ""))
            except Exception:
                type_line = str(getattr(card, "type", ""))
            types_list = []
            try:
                tl = getattr(card, "types", None)
                if isinstance(tl, list):
                    types_list = [str(t) for t in tl]
            except Exception:
                types_list = []
            try:
                # Prefer model helper when available
                is_creature = bool(getattr(card, 'is_creature', lambda: False)())
            except Exception:
                is_creature = any(t.lower() == "creature" for t in types_list)
            if is_creature:
                total_creature_cards += 1
                try:
                    total_creature_copies += int(deck.inventory.get(name, 0))
                except Exception:
                    pass
            decklist.append({
                "qty": deck.inventory.get(name, 0),
                "name": name,
                "type": type_line,
                "types": types_list,
                "is_creature": is_creature,
                "mv": getattr(card, "converted_mana_cost", 0),
                "text": getattr(card, "text", ""),
                "mana_cost": getattr(card, "mana_cost", getattr(card, "manaCost", "")),
                "rarity": getattr(card, "rarity", ""),
                "colors": getattr(card, "colors", []),
                "power": getattr(card, "power", None),
                "toughness": getattr(card, "toughness", None),
                "loyalty": getattr(card, "loyalty", None),
                "set_code": getattr(card, "set_code", getattr(card, "setCode", None)),
                "color_identity": getattr(card, "color_identity", getattr(card, "colorIdentity", [])),
                "reasons": card_reasons.get(name, []),
                "score": getattr(card, 'score', None) if hasattr(card, 'score') else None,
            })

        # Enrich debug context with post-build type counts and mismatch note if any
        if debug:
            try:
                creatures_target = None
                creatures_added = None
                if build_context_summary.get("category_summary") and "creatures" in build_context_summary["category_summary"]:
                    cs = build_context_summary["category_summary"]["creatures"]
                    creatures_target = cs.get("target")
                    creatures_added = cs.get("added")
                build_context_summary["post_type_counts"] = {
                    "creature_unique": total_creature_cards,
                    "creature_total": total_creature_copies,
                }
                if creatures_added is not None and creatures_added != total_creature_copies:
                    build_context_summary["notes"] = [
                        f"Category 'creatures' added={creatures_added}, but deck contains {total_creature_copies} creature copies ({total_creature_cards} unique). Later steps may have pruned or replaced cards."
                    ]
            except Exception:
                pass

        return {
            "decklist": decklist,
            "analysis": analysis,
            "arena_import": arena,
            "build_log": build_log,
            "build_context": build_context_summary if debug else {},
        }


