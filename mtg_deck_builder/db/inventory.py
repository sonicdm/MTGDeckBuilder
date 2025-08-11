"""Inventory management for MTG cards."""

import logging
from pathlib import Path

from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship, Session

from mtg_deck_builder.db.mtgjson_models.base import MTGJSONBase
from mtg_deck_builder.utils.arena_parser import parse_arena_export

logger = logging.getLogger(__name__)


class InventoryItem(MTGJSONBase):
    """Represents an inventory item for a Magic card."""

    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True, autoincrement=True)
    card_name = Column(String, ForeignKey('summary_cards.name'), nullable=False)
    quantity = Column(Integer, default=0, nullable=False)
    condition = Column(String, default="NM")  # NM, LP, MP, HP, DMG
    is_foil = Column(String, default="false")  # true, false, both

    # Relationships
    card = relationship(
        "MTGJSONSummaryCard",
        back_populates="inventory_item",
        primaryjoin="foreign(InventoryItem.card_name)==MTGJSONSummaryCard.name"
    )

    def __repr__(self):
        return f"<InventoryItem(card_name={self.card_name!r}, quantity={self.quantity})>"

    def to_dict(self):
        return {
            'id': self.id,
            'card_name': self.card_name,
            'quantity': self.quantity,
            'condition': self.condition,
            'is_foil': self.is_foil
        }


def load_inventory_items(inventory_file: str, session: Session):
    """Take card inventory in Arena format and load it into the database."""
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
    
    # Delete all existing inventory items
    session.query(InventoryItem).delete()
    
    # Add new inventory items
    total_cards = 0
    for card_name, quantity in inventory_dict['main'].items():
        # Quantity should be no more than 4
        if quantity > 4:
            logger.warning(
                f"Quantity for {card_name} is {quantity}, which is greater than 4"
            )
        quantity = min(quantity, 4)
        session.add(InventoryItem(card_name=card_name, quantity=quantity))
        total_cards += quantity
    
    logger.info(
        f"Loaded {len(inventory_dict['main'])} inventory items for {total_cards} cards"
    )
    
    # Commit the changes
    session.commit()





