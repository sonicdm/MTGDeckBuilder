from collections import defaultdict, Counter
from typing import List
from mtg_deck_builder.data_loader import load_inventory_from_txt, load_atomic_cards_from_json
from mtg_deck_builder.models.collection import Collection
from mtg_deck_builder.models.cards import AtomicCard


def main():
    """Main function to build and export the Dimir Control deck."""
    print("\n🟦⬛ Starting Dimir Control Deck Builder...\n")

    inventory_path = r"Z:\Scripts\MTGDecks\inventory_files\card_inventory_2025-03-14.txt"
    atomic_path = r"Z:\Scripts\MTGDecks\atomic_json_files\AtomicCards.json"

    print("📥 Loading inventory and card database...")
    inventory = load_inventory_from_txt(inventory_path)
    atomic_cards = load_atomic_cards_from_json(atomic_path)

    collection = Collection.build_from_inventory(atomic_cards, inventory)
    print(f"✅ Loaded {sum(collection.owned_quantities.values())} total owned cards.\n")

    print("🔍 Filtering Standard-legal UB & Colorless cards...")
    color_identity = ["U", "B", ""]
    filtered_cards = collection.filter_cards(color_identity=color_identity, legal_in=["standard"], color_mode="only")

    print(f"✅ Found {len(filtered_cards.cards)} potential deck cards!\n")

    print("⚙️  Building the Dimir Control deck...")
    deck = build_dimir_deck(collection)

    print("\n📝 Final Deck List (MTGA Import Format):")
    print(export_to_mtga_simple_format(deck))


# --------------------------------------------------------------
# 🏗️ DECK BUILDING LOGIC
# --------------------------------------------------------------

def build_dimir_deck(collection: Collection) -> List[AtomicCard]:
    """Builds a Dimir Control deck with proper mana balance and strategic spell selection."""
    deck_size = 60

    # Define target counts
    ratios = {
        "lands": 24,
        "creatures": 16,  # Ensuring at least 16 creatures for board presence
        "removal": 12,
        "card_draw": 6,
        "tempo": 4,
        "value": 2,
    }

    # ✅ Step 1: Filter Standard-legal UB and Colorless cards
    filtered_cards = collection.filter_cards(color_identity=["U", "B", ""], legal_in=["standard"], color_mode="only")
    filtered_cards = filtered_cards.get_owned_cards_collection()

    # ✅ Step 2: Score cards based on Dimir suitability
    print("📊 Scoring cards for suitability in Dimir Control...")
    scored_cards = score_all_cards(list(filtered_cards.cards.values()))

    scored_cards.sort(key=lambda x: x[1], reverse=True)


    # ✅ Step 3: Categorize cards by type
    categorized_cards = categorize_cards(scored_cards)

    print("🛠 Selecting best cards for each category...\n")

    # ✅ Step 4: Select creatures first
    deck = select_cards("creatures", ratios["creatures"], categorized_cards, collection)

    # ✅ Step 5: Add remaining spells
    for category in ["removal", "card_draw", "tempo", "value"]:
        deck += select_cards(category, ratios[category], categorized_cards, collection)

    # ✅ Step 6: Optimize mana base
    deck += optimize_mana_base(deck, collection, ratios["lands"])

    # ✅ Step 7: Ensure exactly 60 cards in the deck
    deck = trim_deck(deck)

    print("\n✅ Deck Successfully Built!\n")
    return deck


from collections import defaultdict


def categorize_cards(scored_cards):
    """
    Categorizes scored cards into appropriate deck categories.

    - Categorizes cards based on their types and effects.
    - Prints category counts for debugging.

    Args:
        scored_cards (List[Tuple[AtomicCard, float]]): A list of cards with their Dimir suitability score.

    Returns:
        Dict[str, List[Tuple[AtomicCard, float]]]: Categorized cards sorted into groups.
    """
    categorized_cards = defaultdict(list)

    print("📂 Categorizing Cards...")

    for card, score in scored_cards:
        card_text = card.text or ""
        card_types = card.types or []

        if "Land" in card_types:
            categorized_cards["lands"].append((card, score))

        elif "Creature" in card_types:
            categorized_cards["creatures"].append((card, score))

        elif any(kw in card_text for kw in ["Destroy", "Exile", "Counter", "Remove"]):
            categorized_cards["removal"].append((card, score))

        elif any(kw in card_text for kw in ["Draw", "Loot", "Scry"]):
            categorized_cards["card_draw"].append((card, score))

        elif any(kw in card_text for kw in ["Bounce", "Discard", "Tax", "Flash"]):
            categorized_cards["tempo"].append((card, score))

        elif any(kw in card_text for kw in ["Recursion", "Value", "Copy"]):
            categorized_cards["value"].append((card, score))

        else:
            categorized_cards["other"].append((card, score))  # Fallback category

    # ✅ Print category summary
    print("\n📊 Categorization Summary:")
    for category, cards in categorized_cards.items():
        print(f"   - {category}: {len(cards)} cards")

    return categorized_cards


def select_cards(category, count, categorized_cards, collection):
    """
    Selects the highest-scoring cards in a category while respecting ownership limits.

    Args:
        category (str): The category name (e.g., "creatures", "removal").
        count (int): The target number of cards to select.
        categorized_cards (Dict[str, List[Tuple[AtomicCard, float]]]): Scored cards by category.
        collection (Collection): The user's card collection.

    Returns:
        List[AtomicCard]: Selected cards from this category.
    """
    selected = []
    deck_counter = Counter()  # Track how many times a card has been added

    print(f"🛠 Selecting cards for category: {category} (Target: {count})")

    for card, score in categorized_cards[category]:
        owned_qty = collection.inventory.get_owned_quantity(card.name)
        add_qty = min(owned_qty, 4, count - len(selected))

        if add_qty > 0:
            for _ in range(add_qty):
                selected.append(card)
                deck_counter[card.name] += 1
                print(f"✅ Added {card.name} ({deck_counter[card.name]}/{owned_qty} copies in deck)")

        if len(selected) >= count:
            break

    print(f"✅ Finished selecting for {category}. Total added: {len(selected)}")
    return selected[:count]


def optimize_mana_base(deck, collection, num_lands):
    """Optimizes the mana base by selecting a mix of special and basic lands."""
    print("\n🌍 Optimizing mana base...")

    special_lands = collection.filter_cards_set(type_query="Land", legal_in=["standard"])
    special_lands = [card for card in special_lands if is_good_special_land(card)]
    num_special_lands = num_lands // 3
    selected_special_lands = select_special_lands(special_lands, num_special_lands, collection)
    selected_basic_lands = select_basic_lands(deck, collection, num_lands - len(selected_special_lands))

    return selected_special_lands + selected_basic_lands


def trim_deck(deck):
    """Trims the deck to exactly 60 cards, prioritizing land stability."""
    if len(deck) > 60:
        print(f"\n🚨 Deck has {len(deck)} cards! Trimming down to 60...")

        # Separate cards into categories
        land_cards = [c for c in deck if "Land" in (c.types or [])]
        creature_cards = [c for c in deck if "Creature" in (c.types or [])]
        non_creature_spells = [c for c in deck if "Creature" not in (c.types or []) and "Land" not in (c.types or [])]

        total_extra = len(deck) - 60
        removed_cards = []

        # ✅ Step 1: Prioritize removing **non-creature spells** first
        if len(non_creature_spells) > total_extra:
            removed_cards = sorted(non_creature_spells, key=lambda c: score_dimir_suitability(c))[:total_extra]
        else:
            removed_cards = non_creature_spells
            extra_lands_needed = len(deck) - 60
            if extra_lands_needed > 0:
                removed_cards.extend(land_cards[:extra_lands_needed])

        print("\n🗑️ Removed Cards to Reach 60:")
        for removed in removed_cards:
            print(f"   ❌ {removed.name}")

        # ✅ Step 5: Reconstruct the final deck
        deck = [c for c in deck if c not in removed_cards]

    print(f"\n✅ Final Deck Count: {len(deck)} (Should be 60)")
    return deck


def select_basic_lands(deck, collection, num_basic_lands):
    """
    Selects the correct number of basic lands based on mana distribution in the deck.

    - Ensures basic lands are balanced according to the deck's mana needs.

    Args:
        deck (List[AtomicCard]): Current decklist (to analyze mana symbols).
        collection (Collection): Player's card collection.
        num_basic_lands (int): Number of basic lands to add.

    Returns:
        List[AtomicCard]: Selected basic lands.
    """
    # Count mana symbols in spells (not lands)
    mana_symbols = Counter()
    for card in deck:
        if "Land" not in (card.types or []) and card.manaCost:
            for symbol in card.manaCost:
                if symbol in ["U", "B"]:
                    mana_symbols[symbol] += 1

    # Determine the ratio of blue vs black mana needed
    total_mana_symbols = mana_symbols["U"] + mana_symbols["B"]
    blue_ratio = 0.5 if total_mana_symbols == 0 else mana_symbols["U"] / total_mana_symbols

    # Calculate land split
    num_islands = round(num_basic_lands * blue_ratio)
    num_swamps = num_basic_lands - num_islands

    # Create placeholders for basic lands if not found in the collection
    basic_island = collection.get_card(name_query="Island") or AtomicCard(
        name="Island", type="Basic Land", colorIdentity=["U"], manaValue=0
    )
    basic_swamp = collection.get_card(name_query="Swamp") or AtomicCard(
        name="Swamp", type="Basic Land", colorIdentity=["B"], manaValue=0
    )

    print(f"🌍 Selecting {num_basic_lands} Basic Lands...")
    print(f"   - Islands: {num_islands}  |  Swamps: {num_swamps}")

    selected_basic_lands = ([basic_island] * num_islands) + ([basic_swamp] * num_swamps)

    print(f"✅ Finished selecting basic lands. Total: {len(selected_basic_lands)}\n")
    return selected_basic_lands


def select_special_lands(special_lands, num_special_lands, collection):
    """
    Selects the best special lands for a Dimir deck.

    - Prioritizes lands that provide U or B mana.
    - Ensures ownership limits are respected.
    - Stops selecting once the required number is reached.

    Args:
        special_lands (List[AtomicCard]): List of potential special lands.
        num_special_lands (int): Number of special lands to add.
        collection (Collection): Player's card collection.

    Returns:
        List[AtomicCard]: Selected special lands.
    """
    selected_special_lands = []

    # Sort special lands by best Dimir fit (U/B mana sources first)
    special_lands.sort(key=lambda land: ("{U}" in land.text or "{B}" in land.text, land.manaValue), reverse=True)

    print(f"\n🌍 Selecting {num_special_lands} Special Lands...")

    for land in special_lands:
        owned_qty = collection.inventory.get_owned_quantity(land.name)
        add_qty = min(owned_qty, 4, num_special_lands - len(selected_special_lands))

        if add_qty > 0:
            selected_special_lands.extend([land] * add_qty)
            print(f"✅ Added {add_qty}x {land.name} (Owned: {owned_qty})")

        if len(selected_special_lands) >= num_special_lands:
            break

    print(f"✅ Finished selecting special lands. Total: {len(selected_special_lands)}\n")
    return selected_special_lands


def is_good_special_land(card: AtomicCard) -> bool:
    """
    Determines if a given land is a strong choice for a Dimir deck.

    Criteria:
    - Must be Standard-legal.
    - Must NOT be a basic land.
    - Must provide Dimir colors (U or B) OR offer useful control effects.
    - Preferably has a mana ability or an effect like draw, discard, scry, or mill.

    Args:
        card (AtomicCard): The land card to evaluate.

    Returns:
        bool: True if the land is a good special land, False otherwise.
    """
    # ✅ **Step 1: Ensure land is Standard-legal**
    if not card.is_legal_in("standard"):
        return False  # ❌ Immediately reject non-Standard lands

    # ✅ **Step 2: Ensure it's not a basic land**
    if "Basic" in (card.supertypes or []):
        return False  # ❌ We handle basic lands separately

    # ✅


from tqdm import tqdm  # Progress bar module


def score_all_cards(filtered_cards):
    """
    Scores all filtered cards using the Dimir suitability function.

    - Uses tqdm to display a progress bar.

    Args:
        filtered_cards (List[AtomicCard]): The filtered set of Dimir-relevant cards.

    Returns:
        List[Tuple[AtomicCard, float]]: A list of (card, score) tuples sorted by score.
    """
    print("\n📊 Scoring cards for suitability in Dimir Control...")
    scored_cards = [(card, score_dimir_suitability(card)) for card in
                    tqdm(filtered_cards, desc="Scoring Cards", ncols=80)]
    scored_cards.sort(key=lambda x: x[1], reverse=True)  # Sort by highest score first
    print("✅ Finished scoring all cards!\n")
    return scored_cards


def score_dimir_suitability(card: AtomicCard) -> float:
    """
    Scores a card based on how well it fits in a Dimir deck.

    - Prioritizes UB cards.
    - Includes colorless cards in the normal scoring system.
    - Rewards control elements (counterspells, removal, card draw).
    - Penalizes cards outside Dimir's game plan.

    Args:
        card (AtomicCard): The card to score.

    Returns:
        float: The suitability score (higher = better).
    """
    score = 0

    # ✅ Debug: Print card being scored
    print(f"🔎 Scoring {card.name}...")

    # Prioritize UB cards (strongest synergy)
    if card.matches_color_identity(["U", "B"], mode="exact"):
        score += 5  # Strong Dimir identity
        print(f"   🟦⬛ {card.name} is a pure Dimir card! (+5)")

    # Include colorless (artifacts, utility) but score lower
    elif card.matches_color_identity([""], mode="exact"):
        score += 2  # Usable but less synergistic
        print(f"   ⚪ {card.name} is colorless but useful. (+2)")

    # Reward strong Dimir mechanics
    dimir_keywords = ["counter target", "destroy", "exile", "draw", "discard"]
    for kw in dimir_keywords:
        if kw in (card.text or "").lower():
            score += 3
            print(f"   ✨ {card.name} has '{kw}' effect! (+3)")

    # Adjust artifact scoring—only keep strong ones
    if "Artifact" in (card.types or []):
        if "mana" in (card.text or "").lower() or "draw" in (card.text or "").lower():
            score += 4  # Utility artifacts (e.g., ramp, card draw)
            print(f"   🛠 {card.name} is a useful artifact! (+4)")
        else:
            score -= 2  # Penalize generic artifacts
            print(f"   ❌ {card.name} is a generic artifact. (-2)")

    # Penalize off-color cards (shouldn't happen, but just in case)
    if not card.matches_color_identity(["U", "B", ""], mode="contains"):
        score -= 3
        print(f"   🚨 {card.name} is off-color! (-3)")

    return score


def export_to_mtga_simple_format(deck: List[AtomicCard]) -> str:
    """Exports a decklist for MTG Arena import format."""
    card_counts = Counter(deck)
    return "\n".join(["Deck"] + [f"{qty} {card.name}" for card, qty in card_counts.items()])


if __name__ == "__main__":
    main()
