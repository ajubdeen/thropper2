"""
Anachron - Configuration Module

All tunable game parameters live here. Adjust these to change game feel
without touching game logic.
"""

# =============================================================================
# ERA REGIONS
# =============================================================================

# Which eras are considered "European/Western" vs global
# European focus includes Western culture (Americas colonized by Europeans)
EUROPEAN_ERA_IDS = [
    "classical_athens",      # Greece
    "viking_age",            # Scandinavia
    "medieval_plague",       # Europe
    "american_revolution",   # Colonial America (Western culture)
    "industrial_britain",    # Britain
    "civil_war",             # America (Western culture)
    "ww2_europe",            # Europe
    "ww2_pacific",           # American Home Front (Western culture)
    "cold_war_germany",      # Cold War East Germany
]

# All other eras are "worldwide/global"
# ancient_egypt, han_dynasty, aztec_empire, mughal_india, indian_partition

# =============================================================================
# TIME MACHINE SETTINGS
# =============================================================================

# Minimum turns before window can open (prevents slot-machine gameplay)
WINDOW_MIN_TURNS = 7

# Window probability by turn (guaranteed by turn 10)
# Turn 7: 30%, Turn 8: 50%, Turn 9: 75%, Turn 10: 100%
WINDOW_PROBABILITIES = {
    7: 0.30,
    8: 0.50,
    9: 0.75,
    10: 1.00,  # Guaranteed
}

# Legacy settings (kept for reference, no longer used)
WINDOW_BASE_PROBABILITY = 0.30  # Starting probability at turn 7
WINDOW_PROBABILITY_INCREMENT = 0.20  # Roughly matches new curve
WINDOW_PROBABILITY_CAP = 1.0  # Guaranteed by turn 10

# Small chance of very long gap (makes some playthroughs feel different)
# DISABLED - we now guarantee window by turn 10
LONG_GAP_PROBABILITY = 0.0  # Was 0.05
LONG_GAP_EXTRA_TURNS = 0  # Was 10

# Window duration in turns (how long player has to decide)
WINDOW_DURATION_TURNS = 3  # Represents about a week in-game

# =============================================================================
# TIME PACING
# =============================================================================

# Normal turns per year (each turn = ~7-8 weeks when window is closed)
TURNS_PER_YEAR = 7

# When window opens, time compresses - turns represent days not weeks
# This creates urgency around the decision
WINDOW_TIME_COMPRESSED = True

# =============================================================================
# STARTING ITEMS (Fixed - these always come with you)
# =============================================================================

STARTING_ITEMS = [
    {
        "id": "ibuprofen",
        "name": "Bottle of Ibuprofen",
        "description": "100 tablets of 200mg ibuprofen",
        "uses": 100,
        "utility": "Reduce fever, ease pain, reduce inflammation",
        "risk": "Can't cure infections, supplies run out, overdose danger",
        "hooks": ["heal", "trade", "gain trust", "save someone important"],
        "from_era": None,  # Modern item
        "era_context": {
            # How remarkable is this item in different periods?
            "ancient": "Miraculous - reliable pain/fever relief without opium. Seems like divine medicine.",
            "medieval": "Very valuable - safer than available alternatives. Clean pills are unusual.",
            "early_modern": "Valuable - still superior to most remedies, but less dramatic.",
            "industrial": "Moderate - aspirin invented 1897, morphine common. Good but not miraculous.",
            "modern": "Unremarkable - it's just over-the-counter medicine.",
        },
    },
    {
        "id": "knife",
        "name": "Swiss Army Knife",
        "description": "Compact folding knife with multiple tools",
        "uses": None,  # Durable
        "utility": "Useful for cutting, minor repairs, and practical tasks",
        "risk": "Theft target in early eras, questions about craftsmanship origin",
        "hooks": ["cut", "repair", "craft", "practical tasks"],
        "from_era": None,
        "era_context": {
            # How remarkable AND what are its limits?
            "ancient": "Novel - good steel is rare, folding mechanism clever. But it's a knife, not a superpower. Cannot cut bronze/iron easily.",
            "medieval": "Moderate - good smiths exist. Compact design is main novelty. It's a useful tool, nothing more.",
            "early_modern": "Low - pocket knives are common. Just a nice portable tool.",
            "industrial": "Minimal - mass-produced pocket knives widely available. Unremarkable.",
            "modern": "None - Swiss Army Knives exist (invented 1891). Just a pocket knife.",
        },
        "physical_limits": [
            "Can cut: leather, cloth, rope, wood, food, soft metals (lead, tin)",
            "Can score but NOT cut through: copper, bronze, iron, steel",
            "Blade dulls with heavy use, especially on hard materials",
            "One knife, one user - limited throughput for any task",
        ],
    },
    {
        "id": "phone_kit",
        "name": "Smartphone + Solar Charger",
        "description": "Modern smartphone with offline Wikipedia and solar charger",
        "uses": None,  # Renewable with solar
        "utility": "Private access to encyclopedic knowledge - the player's secret advantage",
        "risk": "Obviously impossible technology - extremely dangerous to reveal in any pre-2000 era",
        "hooks": ["consult Wikipedia privately", "verify historical facts", "recall medical knowledge", "check names and dates"],
        "features": [
            "Wikipedia offline - encyclopedic knowledge of history, science, medicine, people (PRIMARY USE)",
            "Solar charger - renewable power as long as there's sun",
            "Camera - record images, use as mirror (rare use)",
            "Flashlight - only when no fire/torches available (edge case)",
            "Compass - only when genuinely lost in wilderness (edge case)",
            "Calculator - complex math instantly (rare use)",
            "Maps - though only shows modern geography (limited use)"
        ],
        "from_era": None,
        "era_context": {
            # The smartphone remains alien/impossible until post-2000
            "ancient": "Alien artifact if revealed. But privately: an oracle of infinite knowledge.",
            "medieval": "Witchcraft evidence if seen. But privately: the player knows things no one else could.",
            "early_modern": "Impossible to explain if discovered. But privately: a secret library.",
            "industrial": "Would be confiscated and studied. But privately: encyclopedic advantage.",
            "modern": "Spy equipment if found. But privately: still invaluable for historical knowledge.",
        },
    },
]

# =============================================================================
# FULFILLMENT ANCHORS (Hidden from player)
# =============================================================================

ANCHORS = {
    "belonging": {
        "name": "Belonging",
        "description": "Community, acceptance, found family",
        "arrival_threshold": 70,
        "mastery_threshold": 90,
    },
    "legacy": {
        "name": "Legacy", 
        "description": "Lasting impact, teaching, building",
        "arrival_threshold": 70,
        "mastery_threshold": 90,
    },
    "freedom": {
        "name": "Freedom",
        "description": "Autonomy, self-determination, independence",
        "arrival_threshold": 70,
        "mastery_threshold": 90,
    }
}

# =============================================================================
# GAME MODES
# =============================================================================

MODES = {
    "kid": {
        "name": "Kid Mode",
        "age_rating": "11+",
        "description": "Educational, age-appropriate content",
        "violence": "consequences, not graphic",
        "death": "framed respectfully",
        "sexual_content": False,
        "profanity": False,
    },
    "mature": {
        "name": "Mature Mode",
        "age_rating": "18+",
        "description": "Unflinching historical realism",
        "violence": "graphic when accurate",
        "death": "visceral, specific",
        "sexual_content": "implied, referenced",
        "profanity": True,
    }
}

# =============================================================================
# DISPLAY SETTINGS
# =============================================================================

TEXT_SPEED = 0.012  # Seconds per character for typewriter effect
SHOW_DEVICE_STATUS = True  # Show time machine indicator in UI

# =============================================================================
# DEBUG SETTINGS (Development Only)
# =============================================================================

import os

# Set DEBUG_ERA to a valid era ID to force that era (e.g., "cold_war_germany")
# Only works when DEBUG_MODE is also True
DEBUG_MODE = os.environ.get("DEBUG_MODE", "").lower() == "true"
DEBUG_ERA = os.environ.get("DEBUG_ERA", "")

# Valid era IDs for validation (prevents arbitrary input)
VALID_ERA_IDS = [
    "ancient_egypt",
    "classical_athens", 
    "han_dynasty",
    "viking_age",
    "medieval_plague",
    "aztec_empire",
    "mughal_india",
    "american_revolution",
    "industrial_britain",
    "civil_war",
    "indian_partition",
    "ww2_europe",
    "ww2_pacific",
    "cold_war_germany",
]

def get_debug_era_id():
    """Returns validated debug era ID or None if not in debug mode"""
    if DEBUG_MODE and DEBUG_ERA and DEBUG_ERA in VALID_ERA_IDS:
        return DEBUG_ERA
    return None
