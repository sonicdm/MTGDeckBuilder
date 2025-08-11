from collections import defaultdict
from pathlib import Path

from mtg_deck_builder.utils.arena_parser import parse_arena_export
from .base import MTGJSONBase
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship, Session
import re
import logging

logger = logging.getLogger(__name__)

class InventoryItem(MTGJSONBase):
    __tablename__ = "inventory_items"

    id = Column(Integer, primary_key=True)
    card_name = Column(String, ForeignKey("cards.name"))
    quantity = Column(Integer)
    card = relationship("MTGJSONCard", back_populates="inventory")
    

def load_inventory_items(inventory_file: str, session: Session):
    """
    take card inventory in Arena format and load it into the database
    """
    logger.info(f"Loading inventory items from {inventory_file}")
    lines = []
    inventory_file_path = Path(inventory_file)
    with inventory_file_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            lines.append(line)
    
    inventory_dict = parse_arena_export(lines)
    
    # delete all existing inventory items
    session.query(InventoryItem).delete()
    # add new inventory items
    total_cards = 0
    for card_name, quantity in inventory_dict['main'].items():
        # quantity should be no more than 4
        if quantity > 4:
            logger.warning(f"Quantity for {card_name} is {quantity}, which is greater than 4")
        quantity = min(quantity, 4)
        session.add(InventoryItem(card_name=card_name, quantity=quantity))
        total_cards += quantity
    logger.info(f"Loaded {len(inventory_dict['main'])} inventory items for {total_cards} cards")
    # commit the changes
    session.commit()





