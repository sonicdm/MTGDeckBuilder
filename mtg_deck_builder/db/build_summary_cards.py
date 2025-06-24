from collections import defaultdict
import json
import logging
from sqlalchemy.orm import sessionmaker, joinedload
from sqlalchemy import create_engine
from mtg_deck_builder.db.mtgjson_models.cards import MTGJSONCard, MTGJSONSet, MTGJSONCardLegality, MTGJSONSummaryCard
from mtg_deck_builder.db.mtgjson_models.base import MTGJSONBase
from mtg_deck_builder.db.setup import setup_database
from tqdm import tqdm
# setup debug logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
DB_URL = "sqlite:///data/mtgjson/AllPrintings.sqlite"
BATCH_SIZE = 10000

def safe_list_field(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return []
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return parsed
        except Exception:
            pass
        # Fallback: treat as CSV
        return [v.strip() for v in value.split(',') if v.strip()]
    return []

def legalities_to_dict(legality_obj):
    if not legality_obj:
        return {}
    return {
        col.name: getattr(legality_obj, col.name)
        for col in MTGJSONCardLegality.__table__.columns
        if col.name != 'uuid' and getattr(legality_obj, col.name) is not None
    }

def build_summary_cards():
    """Build summary cards from the database."""
    setup_database(DB_URL, base=MTGJSONBase)
    engine = create_engine(DB_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Clear the summary table
        session.query(MTGJSONSummaryCard).delete()
        session.commit()

        # Get all unique card names
        logger.info("Getting all unique card names")
        card_names = session.query(MTGJSONCard.name).distinct().all()
        print(f"Found {len(card_names)} unique card names")
        card_names = [name[0] for name in card_names]

        # Query all cards with eager loading for set and legalities
        logger.info("Querying all cards with eager loading for set and legalities")
        cards = session.query(MTGJSONCard).options(
            joinedload(MTGJSONCard.set),
            joinedload(MTGJSONCard.legalities)
        ).all()

        logger.info(f"Found {len(cards)} card printings with set and legalities eagerly loaded")

        # Organize cards by name
        cards_by_name = defaultdict(list)
        for card in cards:
            cards_by_name[card.name].append(card)

        logger.info(f"Organized into {len(cards_by_name)} unique cards")

        # Process cards in batches
        total_cards = len(card_names)
        with tqdm(total=total_cards, desc="Processing cards", unit="card") as pbar:
            for i in range(0, total_cards, BATCH_SIZE):
                batch_names = card_names[i:i + BATCH_SIZE]
                summary_cards = []

                for name in batch_names:
                    card_printings = cards_by_name[name]
                    if not card_printings:
                        continue

                    # Sort by release date to get newest printing
                    newest_printing = max(
                        card_printings,
                        key=lambda c: c.set.releaseDate if c.set and c.set.releaseDate else ''
                    )
                    printing_set_codes = [c.setCode for c in card_printings]

                    try:
                        summary_card = MTGJSONSummaryCard(
                            name=name,
                            set_code=newest_printing.setCode,
                            rarity=newest_printing.rarity,
                            type=newest_printing.type,
                            mana_cost=newest_printing.manaCost,
                            converted_mana_cost=newest_printing.manaValue,
                            power=newest_printing.power,
                            toughness=newest_printing.toughness,
                            loyalty=newest_printing.loyalty,
                            text=newest_printing.text,
                            flavor_text=newest_printing.flavorText,
                            artist=newest_printing.artist,
                            printing_set_codes=printing_set_codes,
                            color_identity=safe_list_field(newest_printing.colorIdentity),
                            colors=safe_list_field(newest_printing.colors),
                            supertypes=safe_list_field(newest_printing.supertypes),
                            subtypes=safe_list_field(newest_printing.subtypes),
                            keywords=safe_list_field(newest_printing.keywords),
                            legalities=legalities_to_dict(newest_printing.legalities),
                            types=safe_list_field(newest_printing.types)
                        )
                    except Exception as e:
                        logger.error(f"Error processing card {name}: {e}")
                        continue
                    summary_cards.append(summary_card)
                    pbar.update(1)

                # Bulk insert the batch
                session.bulk_save_objects(summary_cards)
                session.commit()
                
                # print(f"Processed batch of {len(summary_cards)} cards")

    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

if __name__ == "__main__":
    build_summary_cards() 