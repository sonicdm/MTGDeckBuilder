from __future__ import annotations

import os
from enum import Enum
from pathlib import Path
from typing import Dict

from fastapi import HTTPException, status


class Scope(str, Enum):
    DECKS = "DECKS"
    MTGJSON = "MTGJSON"
    INVENTORY = "INVENTORY"
    CONFIGS = "CONFIGS"
    EXPORTS = "EXPORTS"


_roots: Dict[Scope, Path] = {}


def set_roots(
    decks: Path,
    mtgjson: Path,
    inventory: Path,
    configs: Path,
    exports: Path,
) -> None:
    roots = {
        Scope.DECKS: Path(decks).resolve(),
        Scope.MTGJSON: Path(mtgjson).resolve(),
        Scope.INVENTORY: Path(inventory).resolve(),
        Scope.CONFIGS: Path(configs).resolve(),
        Scope.EXPORTS: Path(exports).resolve(),
    }
    for p in roots.values():
        p.mkdir(parents=True, exist_ok=True)
    _roots.clear()
    _roots.update(roots)


def _ensure_scope(scope: Scope) -> Path:
    if scope not in _roots:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Scope {scope} is not configured",
        )
    return _roots[scope]


def _resolve_following_symlinks(path: Path) -> Path:
    try:
        return path.resolve(strict=True)
    except FileNotFoundError:
        parent = path.parent
        resolved_parent = parent.resolve(strict=parent.exists())
        return resolved_parent / path.name


def _is_within(root: Path, target: Path) -> bool:
    try:
        target.relative_to(root)
        return True
    except ValueError:
        return False


def safe_path(scope: Scope, user_supplied: str | os.PathLike[str]) -> Path:
    root = _ensure_scope(scope)
    if not isinstance(user_supplied, (str, os.PathLike)):
        raise HTTPException(status_code=400, detail="Invalid path type")

    supplied = Path(user_supplied)

    if supplied.drive and supplied.anchor and not str(supplied).startswith(str(root)):
        raise HTTPException(status_code=400, detail="Path escapes scope root")

    candidate = (root / supplied).resolve()
    resolved = _resolve_following_symlinks(candidate)

    if not _is_within(root, resolved):
        raise HTTPException(status_code=400, detail="Path escapes scope root")

    parts = resolved.parts
    if any(part in ("..",) for part in parts):
        raise HTTPException(status_code=400, detail="Path traversal is not allowed")

    return resolved


# Convenience accessors
def decks_root() -> Path:
    return _ensure_scope(Scope.DECKS)


def mtgjson_root() -> Path:
    return _ensure_scope(Scope.MTGJSON)


def inventory_root() -> Path:
    return _ensure_scope(Scope.INVENTORY)


def configs_root() -> Path:
    return _ensure_scope(Scope.CONFIGS)


def exports_root() -> Path:
    return _ensure_scope(Scope.EXPORTS)


