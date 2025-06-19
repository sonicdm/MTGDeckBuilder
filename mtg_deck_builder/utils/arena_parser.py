from collections import defaultdict
import re
import logging
from typing import List
logger = logging.getLogger(__name__)

def parse_arena_export_line(string: str):
    """
    parse an arena export string into a list of cards
    set code and printing are optional
    """
    logger = logging.getLogger(__name__)
    # logger.debug(f"Parsing arena export line: {string}")
    match = re.match(r'(\d+)\s+(.+?)(?:\s+\(.*\)\s*\d+)?$', string.strip())
    if match:
        # logger.debug(f"Match found: {match.groups()}")
        quantity = int(match.group(1))
        card_name = match.group(2)
        # logger.debug(f"Card name: {card_name} Quantity: {quantity}")
        return quantity, card_name
    # logger.debug(f"No match found for line: {string}")
    return None

def parse_arena_export(text: List[str]):
    """
    parse an arena export text into a list of cards
    """
    logger = logging.getLogger(__name__)
    # logger.debug(f"Parsing arena export for {len(text)} lines")
    inventory_dict = defaultdict(int)
    for line in text:
        parsed = parse_arena_export_line(line)
        if parsed:
            quantity, card_name = parsed
            inventory_dict[card_name] += quantity
    logger.debug(f"Parsed {len(inventory_dict)} cards")
    return inventory_dict