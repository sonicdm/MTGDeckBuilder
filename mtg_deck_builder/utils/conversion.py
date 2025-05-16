# utils/conversion.py
from mtg_deck_builder.db.models import CardDB
from mtg_deck_builder.models import Card, Legalities
from uuid import UUID

def carddb_to_pydantic(card: CardDB) -> Card:
    return Card(
        uid=card.uid if isinstance(card.uid, UUID) else UUID(card.uid),
        name=card.name,
        type=card.type,
        rarity=card.rarity,
        mana_cost=card.mana_cost,
        power=card.power,
        toughness=card.toughness,
        abilities=card.abilities,
        flavor_text=card.flavor_text,
        text=card.text,
        artist=card.artist,
        number=card.number,
        set_code=card.set_code,
        colors=card.colors,
        legalities=[Legalities(format=l, legality=v) for l,v in card.legalities.items()],
        rulings=card.rulings,
        foreign_data=card.foreign_data,
    )