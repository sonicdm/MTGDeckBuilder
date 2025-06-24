import pytest
import os
import tempfile
import json
from mtg_deck_builder.db.loader import is_reload_needed, update_import_time, load_inventory
from mtg_deck_builder.db.models import ImportLog, InventoryItemDB
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime

def setup_test_db(tmp_path):
    db_path = tmp_path / "test_loader.db"
    db_url = f"sqlite:///{db_path}"
    engine = create_engine(db_url)
    from mtg_deck_builder.db.setup import setup_database
    setup_database(db_url)
    Session = sessionmaker(bind=engine)
    return Session, db_url

def test_is_reload_needed_no_log(tmp_path):
    Session, db_url = setup_test_db(tmp_path)
    session = Session()
    # No ImportLog in DB
    assert is_reload_needed(session, "foo.json", mtime=123) is True
    session.close()

def test_is_reload_needed_with_log(tmp_path):
    Session, db_url = setup_test_db(tmp_path)
    session = Session()
    # Add ImportLog with mtime=100
    log = ImportLog(json_path="foo.json", meta_date=datetime.now(), mtime=100)
    session.add(log)
    session.commit()
    # mtime newer than log
    assert is_reload_needed(session, "foo.json", mtime=200) is True
    # mtime older than log
    assert is_reload_needed(session, "foo.json", mtime=50) is False
    session.close()

def test_update_import_time(tmp_path):
    Session, db_url = setup_test_db(tmp_path)
    session = Session()
    update_import_time(session, "bar.json", meta_date=datetime.now(), mtime=123)
    log = session.query(ImportLog).filter_by(json_path="bar.json").first()
    assert log is not None
    assert log.mtime == 123
    session.close()

def make_inventory_file(tmp_path, lines):
    file = tmp_path / "inv.txt"
    file.write_text("\n".join(lines), encoding="utf-8")
    return str(file)

def test_load_inventory_valid(tmp_path):
    Session, db_url = setup_test_db(tmp_path)
    session = Session()
    path = make_inventory_file(tmp_path, ["2 Lightning Bolt", "1 Plains"])
    load_inventory(session, path)
    items = session.query(InventoryItemDB).all()
    names = {i.card_name for i in items}
    assert "Lightning Bolt" in names
    assert "Plains" in names
    session.close()

def test_load_inventory_missing_file(tmp_path, capsys):
    Session, db_url = setup_test_db(tmp_path)
    session = Session()
    missing_path = tmp_path / "does_not_exist.txt"
    load_inventory(session, str(missing_path))
    out = capsys.readouterr().out
    assert "Inventory file not found" in out
    session.close()

def test_load_inventory_invalid_lines(tmp_path):
    Session, db_url = setup_test_db(tmp_path)
    session = Session()
    path = make_inventory_file(tmp_path, ["foo bar", "3 Lightning Bolt"])
    load_inventory(session, path)
    items = session.query(InventoryItemDB).all()
    assert any(i.card_name == "Lightning Bolt" for i in items)
    assert not any(i.card_name == "foo bar" for i in items)
    session.close()

