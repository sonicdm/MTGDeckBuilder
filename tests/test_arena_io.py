from mtg_deck_builder.arena_io import parse_arena_export_text


def test_parse_arena_basic():
    txt = """
Deck
4 Lightning Strike (M20) 152
2 Play with Fire

Sideboard
1 Fade into Antiquity
""".strip()
    res = parse_arena_export_text(txt)
    assert res.main.get("Lightning Strike") == 4
    assert res.main.get("Play with Fire") == 2
    assert res.sideboard is not None

