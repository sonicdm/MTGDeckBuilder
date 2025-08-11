import random
from mtg_deck_builder.db import get_session
from mtg_deck_builder.db.repository import SummaryCardRepository
from mtg_deck_builder.db.setup import setup_database
from mtg_deck_builder.db.mtgjson_models.base import MTGJSONBase
from sqlalchemy import text
from mtg_deck_builder.db.mtgjson_models.cards import MTGJSONSummaryCard  # Import MTGJSONCard model

# Force update the database schema to match our models
db_url = "sqlite:///data/mtgjson/AllPrintings.sqlite"
inventory_file = "inventory_files/card inventory.txt"
# setup_database(db_url, base=MTGJSONBase)
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Open a session to the database
with get_session(db_url) as session:
    logger.info("Setting up database")
    setup_database(db_url, base=MTGJSONBase)
    # load_inventory_items(inventory_file, session)
    any_card = session.query(MTGJSONSummaryCard).first()
    if any_card:
        print(f"\nFound a sample card: {any_card}")
    else:
        print("\nNo cards found in the database")
    
    # Try a direct SQL query to verify data exists
    try:
        result = session.execute(text("SELECT name FROM summary_cards WHERE name LIKE '%Aether%' LIMIT 5")).fetchall()
        print("\nDirect SQL query results for 'Aether':")
        for row in result:
            print(f"- {row[0]}")
    except Exception as e:
        print(f"\nError executing direct SQL query: {e}")
    
    # Direct query for 'Aetherling' using the MTGJSONCard model
    print("Direct query for Aetherling")
    aetherling_direct = session.query(MTGJSONSummaryCard).filter(MTGJSONSummaryCard.name == "Aetherling").first()
    if aetherling_direct:
        print(f"\nDirect query found Aetherling: {aetherling_direct}")
    else:
        print("\nDirect query did not find Aetherling")
    
    # Create a repository
    print("Creating repository")
    repo = SummaryCardRepository(session)
    
    # Get the newest printing of Aetherling
    print("Getting Aetherling from repository")
    aetherling = repo.find_by_name("Aetherling")
    if aetherling:
        print(f"\nFound Aetherling: {aetherling.name} from {aetherling.set_code}")
        print(f"Type: {aetherling.type}")
        print(f"Rarity: {aetherling.rarity}")
        print(f"Text: {aetherling.text}")
        print(f"Color Identity: {aetherling.color_identity}")
        print(f"Mana Cost: {aetherling.mana_cost}")
        print(f"Power: {aetherling.power}")
        print(f"Toughness: {aetherling.toughness}")
        print(f"Loyalty: {aetherling.loyalty}")
        print(f"Keywords: {aetherling.keywords}")
        print(f"Legalities: {aetherling.legalities}")
    else:
        print("\nAetherling not found")
    
    # Filter cards by name
    # filtered_repo = repo.filter_cards(name_query="Aether")
    # cards = filtered_repo.get_all_cards()
    # print(f"\nFound {len(cards)} cards matching 'Aether':")
    # for card in cards:
    #     print(f"- {card.name} ({card.set_code})")

    print("Filtering cards by legal in standard, color identity W and U")
    standard_legal = repo.filter_cards(legal_in=["standard"], color_identity=["W", "U"], color_mode="subset", min_quantity=0, basic_type="Planeswalker")
    print(f"\nFound {len(standard_legal.get_all_cards())} cards in standard:")
    colors = set()
    for card in standard_legal.get_all_cards():
        colors.update(card.color_identity_list)
    print(f"Colors: {colors}")

    print(f"10 random cards:")
    cards = standard_legal.get_all_cards()
    for card in random.sample(list(cards), min(10, len(cards))):
        print(f"- name={card.name} type={card.types} subtypes={card.subtypes} supertypes={card.supertypes} colors={card.color_identity_list}")
        for key, value in card.to_dict().items():
            continue
            print(f"-- {key}: {value}")

    chained_repo = repo.filter_cards(legal_in=["standard"])
    print(f"Chained repo: total cards: {len(chained_repo.get_all_cards())}")
    chained_repo = chained_repo.filter_cards(color_identity=["W", "U"], color_mode="subset")
    print(f"Chained repo: total cards: {len(chained_repo.get_all_cards())}")
    chained_repo = chained_repo.filter_cards(min_quantity=1)
    print(f"Chained repo: total cards: {len(chained_repo.get_all_cards())}")
    chained_repo = chained_repo.filter_cards(basic_type="Creature", type_text="Legendary")
    print(f"Chained repo: total cards: {len(chained_repo.get_all_cards())}")
    
    final_cards = chained_repo.get_all_cards()
    for card in final_cards:
        print(f"- name={card.name} type={card.types} subtypes={card.subtypes} supertypes={card.supertypes} colors={card.color_identity_list}")
        for key, value in card.to_dict().items():
            print(f"-- {key}: {value}")
            
    lands = repo.filter_cards(basic_type=["Land"], type_text=["Basic Land"])
    print(f"Lands: {len(lands.get_all_cards())}")
    for card in lands.get_all_cards():
        print(f"- name={card.name} type={card.types} subtypes={card.subtypes} supertypes={card.supertypes} colors={card.color_identity_list}")
        for key, value in card.to_dict().items():
            print(f"-- {key}: {value}")

pass