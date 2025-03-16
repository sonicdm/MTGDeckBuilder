# collection.py
from copy import deepcopy
from typing import Dict, Optional, List
from pydantic import BaseModel, Field
from pydantic._internal import _repr

from mtg_deck_builder.models.cards import AtomicCards
from mtg_deck_builder.models.inventory import Inventory, InventoryItem

BASIC_LAND_NAMES = {"Plains", "Island", "Swamp", "Mountain", "Forest"}


class Collection(AtomicCards):
    """
    Subclass of AtomicCards that adds an 'owned_quantities' dict to track how many
    copies of each card the user owns, plus infinite basic lands if not in the inventory.
    This file omits placeholder filter/deck-building logic to keep it minimal and clear.
    """

    owned_quantities: Dict[str, int] = Field(default_factory=dict)
    inventory: Optional[Inventory] = None

    class Config:
        # Pydantic v2 config to allow alias usage (AtomicCards often uses 'data' -> 'cards')
        allow_population_by_field_name = True

    @classmethod
    def build_from_inventory(
            cls,
            cards: AtomicCards,
            inventory: Inventory
    ) -> "Collection":
        """
        Creates a new Collection by merging the base AtomicCards data
        with the user's inventory. Basic lands are infinite.
        """
        # Convert the parent AtomicCards object to a dict with aliases
        parent_data = cards.model_dump(
            by_alias=True,
            exclude_unset=True
        )
        # Parse into a new Collection
        new_obj = cls.model_validate(parent_data)
        # store inventory in new_obj
        new_obj.inventory = inventory
        # Fill owned_quantities from the Inventory
        inv_dict = inventory.to_dict()  # e.g. {"Lightning Bolt": 4, ...}
        for card_name in new_obj.cards.keys():
            if card_name in BASIC_LAND_NAMES:
                new_obj.owned_quantities[card_name] = 999999  # infinite
            else:
                new_obj.owned_quantities[card_name] = inv_dict.get(card_name, 0)

        return new_obj

    def get_owned_quantity(self, card_name: str) -> int:
        """
        Returns how many copies of `card_name` are owned, or 999999 if it's a basic land.
        """
        return self.owned_quantities.get(card_name, 0)

    def filter_cards(
            self,
            name_query: Optional[str] = None,
            text_query: Optional[str] = None,
            type_query: Optional[str] = None,
            color_identity: Optional[List[str]] = None,
            color_mode: str = "exact",
            keyword_query: Optional[str] = None,
            power_value: Optional[float] = None,
            power_op: str = "==",
            toughness_value: Optional[float] = None,
            toughness_op: str = "==",
            mana_value: Optional[float] = None,
            mana_op: str = "==",
            legal_in: Optional[list] = None,
    ) -> "Collection":
        """
        Filter the collection. Call super class method with the same name. return as a Collection object with inventory data.
        :param name_query:
        :param text_query:
        :param type_query:
        :param color_identity:
        :param color_mode:
        :param keyword_query:
        :param power_value:
        :param power_op:
        :param toughness_value:
        :param toughness_op:
        :param mana_value:
        :param mana_op:
        :param legal_in:
        :return: Collection of filtered cards
        """

        new_obj = super().filter_cards(
            name_query=name_query,
            text_query=text_query,
            type_query=type_query,
            color_identity=color_identity,
            color_mode=color_mode,
            keyword_query=keyword_query,
            power_value=power_value,
            power_op=power_op,
            toughness_value=toughness_value,
            toughness_op=toughness_op,
            mana_value=mana_value,
            mana_op=mana_op,
            legal_in=legal_in
        )
        # Recombine with inventory data if self.inventory is not None
        new_obj = Collection.build_from_inventory(new_obj, self.inventory)
        return new_obj

    @property
    def total_owned(self):
        """
        Returns the total number of owned cards in the collection
        Ignoring lands as they are infinite
        :return:
        """
        # card comes from the cards field in AtomicCards
        return sum([qty for card, qty in self.owned_quantities.items() if card not in BASIC_LAND_NAMES])

    @property
    def owned_cards(self):
        """
        Returns a dict of owned cards and their quantity in the collection
        :return:
        """
        return {card: qty for card, qty in self.owned_quantities.items() if card not in BASIC_LAND_NAMES and qty > 0}

    def get_owned_cards_collection(self, min_qty=1):
        """
        Returns a Collection object of owned cards including their inventory data.

        Args:
            min_qty (int): The minimum quantity required to consider a card owned.

        Returns:
            Collection: A new Collection object containing only owned cards.
        """

        # Ensure `self.inventory` is an Inventory object
        if not isinstance(self.inventory, Inventory):
            raise AttributeError("Collection object is missing a valid Inventory instance.")

        # Optimize lookups by converting inventory items list to a filtered list directly
        # filtered_inventory_items = [
        #     item for item in self.inventory.items if item.quantity >= min_qty
        # ]

        # turn this into a for loop for debugging.
        filtered_inventory_items = []
        for item in self.inventory.items.values():
            if item.quantity >= min_qty:
                filtered_inventory_items.append(item)

        # create inventory items from the filtered_inventory_items
        new_inv = Inventory.from_list(filtered_inventory_items)


        # Create a dictionary of owned AtomicCards
        cards = {}
        for item in filtered_inventory_items:
            atomic_card = self.cards.get(item.card_name)
            if atomic_card is not None:
                atomic_card = deepcopy(atomic_card)  # Prevent unintended mutations
                atomic_card.owned = True
                atomic_card.quantity = item.quantity
                cards[atomic_card.name] = atomic_card

        # Create an AtomicCards object with the owned cards
        cards = AtomicCards(data=cards)

        # Build a new Collection object using the new Inventory instance
        new_obj = Collection.build_from_inventory(cards=cards, inventory=new_inv)

        return new_obj

    def __repr__(self):
        # Override the default __repr__ to show the total number of cards owned and total cards in the collection
        total_cards = self.total_cards
        total_owned = self.total_owned
        return f"Collection({total_owned} owned cards, {total_cards} total cards)"
