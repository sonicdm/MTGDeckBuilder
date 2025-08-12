from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException

from backend.security.paths import Scope, safe_path, inventory_root


router = APIRouter(prefix="/api/inventory", tags=["inventory"])


@router.get("")
def list_inventory(subdir: Optional[str] = None) -> List[str]:
    base = inventory_root()
    root = base if not subdir else safe_path(Scope.INVENTORY, subdir)
    return [str(p.relative_to(base)) for p in root.rglob("*.txt")]


@router.get("/file")
def read_inventory(path: str) -> Dict[str, Any]:
    p = safe_path(Scope.INVENTORY, path)
    if p.suffix.lower() not in (".txt",):
        raise HTTPException(status_code=400, detail="Only .txt inventory files are allowed")
    if not p.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return {"path": path, "text": p.read_text(encoding="utf-8")}


@router.post("/file")
def write_inventory(payload: Dict[str, Any]) -> Dict[str, Any]:
    path = payload.get("path")
    text = payload.get("text")
    if not path or not isinstance(text, str):
        raise HTTPException(status_code=400, detail="path and text are required")
    p = safe_path(Scope.INVENTORY, path)
    if p.suffix.lower() not in (".txt",):
        raise HTTPException(status_code=400, detail="Only .txt inventory files are allowed")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return {"ok": True, "path": path}


