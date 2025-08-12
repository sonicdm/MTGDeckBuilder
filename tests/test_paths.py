from pathlib import Path
import tempfile
import os

from backend.security.paths import set_roots, safe_path, Scope


def test_safe_path_basic_containment(tmp_path: Path):
    decks = tmp_path / "decks"
    mtgjson = tmp_path / "mtgjson"
    inventory = tmp_path / "inventory"
    configs = tmp_path / "configs"
    exports = tmp_path / "exports"
    set_roots(decks, mtgjson, inventory, configs, exports)

    p = safe_path(Scope.DECKS, "test.yaml")
    assert str(p).startswith(str(decks))


def test_safe_path_denies_traversal(tmp_path: Path):
    set_roots(*(tmp_path / d for d in ["decks", "mtgjson", "inventory", "configs", "exports"]))
    try:
        safe_path(Scope.DECKS, "../etc/passwd")
        assert False, "expected exception"
    except Exception:
        assert True


