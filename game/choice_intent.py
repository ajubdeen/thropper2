"""
Anachron - Choice Intent Detection Module

Detects player intent from choice text, eliminating position-based semantics.
This is the single source of truth for what a choice does.
"""

import re
from enum import Enum
from typing import List, Dict, Optional


class ChoiceIntent(Enum):
    """What a choice actually does"""
    LEAVE_ERA = "leave_era"           # Activate time machine, travel to new era
    STAY_FOREVER = "stay_forever"     # End game, stay permanently in this era
    CONTINUE_STORY = "continue"       # Normal story progression


# Pattern lists for intent detection
# These are checked in order - first match wins

LEAVE_PATTERNS = [
    r'activate.*time\s*machine',
    r'activate.*device',
    r'use.*time\s*machine',
    r'leave.*era.*behind',
    r'leave this era',
    r'travel.*new era',
    r'press.*device',
    r'time to leave',
    r'depart.*era',
]

STAY_FOREVER_PATTERNS = [
    r'stay.*forever',
    r'stay here forever',
    r'this is.*home now',
    r'this is my home',
    r'my home now',
    r'remain.*permanently',
    r'never leave',
    r'choose to stay.*forever',
    r'i choose to stay',
]


def detect_choice_intent(choice_text: str, window_open: bool) -> ChoiceIntent:
    """
    Detect intent from the actual choice text.
    
    This is the ONLY place choice semantics are determined.
    Position (A/B/C) is irrelevant - only the text matters.
    
    Args:
        choice_text: The text of the choice
        window_open: Whether the time machine window is currently open
        
    Returns:
        ChoiceIntent indicating what this choice does
    """
    # Window closed = all choices are story choices
    if not window_open:
        return ChoiceIntent.CONTINUE_STORY
    
    if not choice_text:
        return ChoiceIntent.CONTINUE_STORY
    
    text_lower = choice_text.lower()
    
    # Check for LEAVE patterns
    for pattern in LEAVE_PATTERNS:
        if re.search(pattern, text_lower):
            return ChoiceIntent.LEAVE_ERA
    
    # Check for STAY FOREVER patterns
    for pattern in STAY_FOREVER_PATTERNS:
        if re.search(pattern, text_lower):
            return ChoiceIntent.STAY_FOREVER
    
    # Default: continue story
    return ChoiceIntent.CONTINUE_STORY


def filter_choices(
    choices: List[Dict], 
    window_open: bool, 
    can_stay_meaningfully: bool
) -> List[Dict]:
    """
    Filter out choices that shouldn't be available.
    
    Safety layer in case AI generates invalid options.
    Called after parsing AI response, before storing/emitting.
    
    Args:
        choices: List of choice dicts with 'id' and 'text' keys
        window_open: Whether the time machine window is open
        can_stay_meaningfully: Whether player has built enough to stay
        
    Returns:
        Filtered list of valid choices
    """
    if not window_open:
        # Window closed - all choices are valid story choices
        return choices
    
    filtered = []
    
    for choice in choices:
        choice_text = choice.get('text', '')
        intent = detect_choice_intent(choice_text, window_open)
        
        # Remove stay_forever choices if player isn't eligible
        if intent == ChoiceIntent.STAY_FOREVER and not can_stay_meaningfully:
            continue  # Skip this choice
        
        filtered.append(choice)
    
    return filtered


def get_choice_intent_for_submission(
    choice_id: str,
    last_choices: List[Dict],
    window_open: bool
) -> tuple[Optional[ChoiceIntent], Optional[str]]:
    """
    Get the intent for a submitted choice.
    
    Used at choice submission time to route to the correct handler.
    
    Args:
        choice_id: The choice ID (A, B, or C)
        last_choices: The stored choices from last turn
        window_open: Whether window is currently open
        
    Returns:
        Tuple of (ChoiceIntent, choice_text) or (None, None) if invalid
    """
    # Find the choice text
    choice_text = None
    for choice in last_choices:
        if choice.get('id', '').upper() == choice_id.upper():
            choice_text = choice.get('text', '')
            break
    
    if choice_text is None:
        return None, None
    
    intent = detect_choice_intent(choice_text, window_open)
    return intent, choice_text
