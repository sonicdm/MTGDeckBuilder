from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException

from backend.security.paths import Scope, safe_path, decks_root


router = APIRouter(prefix="/api/decks", tags=["decks"])


@router.get("")
def list_decks(subdir: Optional[str] = None) -> Dict[str, List[str]]:
    base = decks_root()
    root = base if not subdir else safe_path(Scope.DECKS, subdir)
    yaml_files = [str(p.relative_to(base)) for p in root.rglob("*.y*ml")]
    json_files = [str(p.relative_to(base)) for p in root.rglob("*.json")]
    return {"yaml": yaml_files, "json": json_files}


@router.get("/file")
def read_deck(path: str) -> Dict[str, Any]:
    p = safe_path(Scope.DECKS, path)
    if p.suffix.lower() not in (".yaml", ".yml", ".json"):
        raise HTTPException(status_code=400, detail="Only YAML/JSON files are allowed")
    if not p.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return {"path": path, "text": p.read_text(encoding="utf-8")}


@router.post("/file")
def write_deck(payload: Dict[str, Any]) -> Dict[str, Any]:
    path = payload.get("path")
    text = payload.get("text")
    if not path or not isinstance(text, str):
        raise HTTPException(status_code=400, detail="path and text are required")
    p = safe_path(Scope.DECKS, path)
    if p.suffix.lower() not in (".yaml", ".yml", ".json"):
        raise HTTPException(status_code=400, detail="Only YAML/JSON files are allowed")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return {"ok": True, "path": path}


