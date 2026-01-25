"""
Anachron - Event Parsing Module

Extracts structured event data from AI narrative responses.
Uses explicit tags that the AI is instructed to include, avoiding fragile regex heuristics.

Tags parsed:
- <character_name>Name</character_name> - Player's name in current era
- <key_npc>Name</key_npc> - Important NPC mentioned (can appear multiple times)
- <wisdom>wisdom_id</wisdom> - Player demonstrated historical understanding

These tags are stripped from the response before showing to the player,
similar to how anchor tags are handled.
"""

import re
from typing import Dict, List, Optional, Tuple


# =============================================================================
# PROMPT ADDITIONS - Instructions for AI to output event tags
# =============================================================================

def get_event_tracking_prompt() -> str:
    """
    Returns instructions for AI to include event tracking tags.
    Added to system prompt alongside anchor detection.
    """
    return """
EVENT TRACKING (Internal - never mention to player):

Include these tags at the END of your response, BEFORE the <anchors> tag:

1. CHARACTER NAME (arrival only):
   When you give the player a name in a new era, include:
   <character_name>TheName</character_name>
   
2. KEY NPCs (every turn with significant NPC interaction):
   When an NPC becomes important to the story (not just mentioned in passing), include:
   <key_npc>NPCName</key_npc>
   You can include multiple <key_npc> tags if multiple NPCs are significant this turn.
   Only tag NPCs who:
   - Have a name
   - The player directly interacts with
   - Could become recurring characters
   
3. WISDOM MOMENTS (when player demonstrates historical understanding):
   If the player's choice shows they understand this era's specific realities
   (social hierarchy, religious customs, economic systems, survival strategies),
   include:
   <wisdom>brief_description</wisdom>
   Examples: <wisdom>approached_priests_first</wisdom>, <wisdom>understood_caste_rules</wisdom>

Put all event tags on their own line at the end, before <anchors>.
These tags are hidden from the player.
"""


def parse_character_name(response: str) -> Optional[str]:
    """
    Extract the character name given to the player in this era.
    
    Returns the name if found, None otherwise.
    """
    match = re.search(
        r'<character_name>\s*([^<]+?)\s*</character_name>',
        response,
        re.IGNORECASE
    )
    if match:
        return match.group(1).strip()
    return None


def parse_key_npcs(response: str) -> List[str]:
    """
    Extract all key NPCs mentioned in the response.
    
    Returns a list of NPC names (may contain duplicates if mentioned multiple times).
    """
    matches = re.findall(
        r'<key_npc>\s*([^<]+?)\s*</key_npc>',
        response,
        re.IGNORECASE
    )
    return [name.strip() for name in matches if name.strip()]


def parse_wisdom_moment(response: str) -> Optional[str]:
    """
    Extract wisdom moment ID if the player demonstrated historical understanding.
    
    Returns the wisdom ID if found, None otherwise.
    """
    match = re.search(
        r'<wisdom>\s*([^<]+?)\s*</wisdom>',
        response,
        re.IGNORECASE
    )
    if match:
        return match.group(1).strip()
    return None


def strip_event_tags(response: str) -> str:
    """
    Remove all event tags from the response before showing to the player.
    
    Removes: <character_name>, <key_npc>, <wisdom> tags
    Note: Anchor tags are handled separately by strip_anchor_tags()
    """
    # Remove character_name tags
    response = re.sub(
        r'<character_name>\s*[^<]*?\s*</character_name>',
        '',
        response,
        flags=re.IGNORECASE
    )
    
    # Remove key_npc tags
    response = re.sub(
        r'<key_npc>\s*[^<]*?\s*</key_npc>',
        '',
        response,
        flags=re.IGNORECASE
    )
    
    # Remove wisdom tags
    response = re.sub(
        r'<wisdom>\s*[^<]*?\s*</wisdom>',
        '',
        response,
        flags=re.IGNORECASE
    )
    
    # Clean up any extra whitespace left behind
    response = re.sub(r'\n\s*\n\s*\n', '\n\n', response)
    
    return response.strip()


def parse_all_events(response: str) -> Dict:
    """
    Parse all event data from an AI response.
    
    Returns a dict with:
    - character_name: str or None
    - key_npcs: List[str]
    - wisdom_id: str or None
    """
    return {
        "character_name": parse_character_name(response),
        "key_npcs": parse_key_npcs(response),
        "wisdom_id": parse_wisdom_moment(response)
    }


# =============================================================================
# DEFINING MOMENT DETECTION
# =============================================================================

# Threshold for anchor change to be considered a "defining moment"
DEFINING_MOMENT_THRESHOLD = 12


def check_defining_moment(anchor_adjustments: Dict[str, int]) -> Optional[Tuple[str, int]]:
    """
    Check if any anchor change qualifies as a defining moment.
    
    Args:
        anchor_adjustments: Dict of anchor_name -> delta (e.g., {"belonging": 15, "legacy": 5})
    
    Returns:
        Tuple of (anchor_name, delta) for the largest change if it exceeds threshold,
        None otherwise.
    """
    if not anchor_adjustments:
        return None
    
    # Find the anchor with the largest absolute change
    max_anchor = None
    max_delta = 0
    
    for anchor, delta in anchor_adjustments.items():
        if abs(delta) > abs(max_delta):
            max_anchor = anchor
            max_delta = delta
    
    if max_anchor and abs(max_delta) >= DEFINING_MOMENT_THRESHOLD:
        return (max_anchor, max_delta)
    
    return None
