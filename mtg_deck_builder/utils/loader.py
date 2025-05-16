from concurrent.futures import ThreadPoolExecutor, as_completed
from uuid import UUID

from tqdm import tqdm

from mtg_deck_builder.db.models import CardDB, CardSetDB
from mtg_deck_builder.models import CardDatabase, CardSet
from mtg_deck_builder.utils.conversion import carddb_to_pydantic


def build_card_database(session) -> CardDatabase:
    cards = session.query(CardDB).all()
    sets = session.query(CardSetDB).all()

    # Build sets with progress bar
    pydantic_sets = {}
    for s in tqdm(sets, desc="Building sets"):
        pydantic_sets[s.set_code] = CardSet(
            set_name=s.set_name,
            set_code=s.set_code,
            release_date=s.release_date.isoformat() if s.release_date else None,
            block=s.block,
            cards={}
        )

    # Build cards in parallel with progress bar
    pydantic_cards = {}
    with ThreadPoolExecutor() as executor:
        futures = {executor.submit(carddb_to_pydantic, c): c for c in cards}
        for future in tqdm(as_completed(futures), total=len(cards), desc="Building cards"):
            card = future.result()
            if card:
                pydantic_cards[card.uid] = card
    # attach cards to their respective sets
    # for card in pydantic_cards.values():
        #progress bar
    for card in tqdm(pydantic_cards.values(), desc="Attaching cards to sets"):
        if card.set_code in pydantic_sets:
            pydantic_sets[card.set_code].cards[card.uid] = card

    return CardDatabase(cards=pydantic_cards, sets=pydantic_sets)
