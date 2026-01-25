"""
Anachron - Time Machine Module

Handles all time machine mechanics:
- Device state and indicator
- Display showing date and location
- Window probability and timing
- Era transitions
"""

import random
from dataclasses import dataclass, field
from typing import Optional, List
from enum import Enum

from config import (
    WINDOW_MIN_TURNS, WINDOW_PROBABILITIES, WINDOW_DURATION_TURNS
)


class DeviceState(Enum):
    """Current state of the time machine device"""
    DORMANT = "dormant"           # Not yet ready, indicator dark
    WARMING = "warming"           # Getting close, indicator flickering
    ACTIVE = "active"             # Window is open, can travel
    COOLDOWN = "cooldown"         # Just used, recharging


class IndicatorState(Enum):
    """What the player sees on the device indicator"""
    DARK = "dark"                 # Nothing happening
    FAINT_PULSE = "faint_pulse"   # Something stirring
    STEADY_GLOW = "steady_glow"   # Window approaching
    BRIGHT_PULSE = "bright_pulse" # Window is open


@dataclass
class TimeMachineDisplay:
    """
    The small display on the device showing current date and location.
    Best kept hidden - the display is obviously not from any known era.
    """
    current_year: int = 0
    current_location: str = ""
    current_era_name: str = ""
    
    def update(self, year: int, location: str, era_name: str):
        self.current_year = year
        self.current_location = location
        self.current_era_name = era_name
    
    def get_display_text(self) -> str:
        """What the display shows"""
        if self.current_year < 0:
            year_str = f"{abs(self.current_year)} BCE"
        else:
            year_str = f"{self.current_year} CE"
        return f"{year_str} | {self.current_location}"


@dataclass
class TimeMachine:
    """
    The player's time travel device.
    
    Small enough to wear on the wrist like a watch, but best kept hidden.
    Has a display showing current date/location, and an indicator for window status.
    The destination controls are broken - that's how this whole journey started.
    """
    
    # Internal state
    turns_since_last_window: int = 0
    window_active: bool = False
    window_turns_remaining: int = 0
    
    # The display
    display: TimeMachineDisplay = field(default_factory=TimeMachineDisplay)
    
    # Journey history
    eras_visited: List[str] = field(default_factory=list)
    total_turns: int = 0
    
    # Probability accumulator (for indicator display)
    _accumulated_probability: float = 0.0
    
    @property
    def indicator(self) -> IndicatorState:
        """What the player sees when they check the device indicator"""
        if self.window_active:
            return IndicatorState.BRIGHT_PULSE
        
        turns_until_eligible = WINDOW_MIN_TURNS - self.turns_since_last_window
        
        if turns_until_eligible > 3:
            return IndicatorState.DARK
        elif turns_until_eligible > 1:
            return IndicatorState.FAINT_PULSE
        else:
            # Eligible or nearly eligible - show based on probability
            if self._accumulated_probability > 0.5:
                return IndicatorState.STEADY_GLOW
            elif self._accumulated_probability > 0.2:
                return IndicatorState.FAINT_PULSE
            else:
                return IndicatorState.DARK
    
    @property
    def device_state(self) -> DeviceState:
        """Current operational state"""
        if self.window_active:
            return DeviceState.ACTIVE
        elif self.turns_since_last_window < 2:
            return DeviceState.COOLDOWN
        elif self.turns_since_last_window >= WINDOW_MIN_TURNS - 2:
            return DeviceState.WARMING
        else:
            return DeviceState.DORMANT
    
    def update_display(self, year: int, location: str, era_name: str):
        """Update the display with current era info"""
        self.display.update(year, location, era_name)
    
    def advance_turn(self) -> bool:
        """
        Advance one turn and check for window.
        Returns True if a window just opened.
        """
        self.total_turns += 1
        self.turns_since_last_window += 1
        
        # Handle active window countdown
        if self.window_active:
            self.window_turns_remaining -= 1
            if self.window_turns_remaining <= 0:
                self._close_window()
            return False
        
        # Check if eligible for window (must be at least turn 7)
        if self.turns_since_last_window < WINDOW_MIN_TURNS:
            return False
        
        # Get probability from table (guaranteed by turn 10)
        # Turn 7: 30%, Turn 8: 50%, Turn 9: 75%, Turn 10+: 100%
        current_turn = self.turns_since_last_window
        if current_turn >= 10:
            current_probability = 1.0  # Guaranteed
        else:
            current_probability = WINDOW_PROBABILITIES.get(current_turn, 1.0)
        
        self._accumulated_probability = current_probability
        
        # Roll for window
        if random.random() < current_probability:
            self._open_window()
            return True
        
        return False
    
    def _open_window(self):
        """Open a travel window"""
        self.window_active = True
        self.window_turns_remaining = WINDOW_DURATION_TURNS
    
    def _close_window(self):
        """Close the travel window (player chose to stay)"""
        self.window_active = False
        self.window_turns_remaining = 0
        self.turns_since_last_window = 0
        self._accumulated_probability = 0.0
    
    def travel(self, new_era_id: str) -> bool:
        """
        Use the window to travel to a new era.
        Returns True if successful.
        """
        if not self.window_active:
            return False
        
        self.eras_visited.append(new_era_id)
        self.window_active = False
        self.window_turns_remaining = 0
        self.turns_since_last_window = 0
        self._accumulated_probability = 0.0
        
        return True
    
    def choose_to_stay(self):
        """Player chooses to let the window close"""
        self._close_window()
    
    def get_indicator_description(self) -> str:
        """Human-readable indicator status"""
        descriptions = {
            IndicatorState.DARK: "The indicator is dark and cold. Silent.",
            IndicatorState.FAINT_PULSE: "A faint pulse stirs in the indicator. Barely perceptible.",
            IndicatorState.STEADY_GLOW: "The indicator glows steadily. Something is building.",
            IndicatorState.BRIGHT_PULSE: "The indicator pulses urgently. The window is open.",
        }
        return descriptions[self.indicator]
    
    def get_window_status(self) -> Optional[str]:
        """Status message if window is active"""
        if not self.window_active:
            return None
        
        if self.window_turns_remaining == WINDOW_DURATION_TURNS:
            return "The window has opened. You have time to decide."
        elif self.window_turns_remaining == 1:
            return "The window is closing. This is your last chance."
        else:
            return f"The window remains open. {self.window_turns_remaining} moments remain."


def select_random_era(available_eras: list, exclude_ids: list = None) -> dict:
    """
    Select a random era, excluding already-visited ones.
    Uses system entropy for better randomness.
    
    Args:
        available_eras: List of era dictionaries
        exclude_ids: Era IDs to exclude (already visited)
    
    Returns:
        Selected era dictionary
    """
    import os
    import time
    
    # Seed with system entropy + time for true randomness each call
    random.seed(int.from_bytes(os.urandom(8), 'big') ^ int(time.time_ns()))
    
    exclude_ids = exclude_ids or []
    eligible = [e for e in available_eras if e["id"] not in exclude_ids]
    
    if not eligible:
        # All eras visited - allow revisits
        eligible = available_eras
    
    # Shuffle then pick first - extra randomization
    random.shuffle(eligible)
    return eligible[0]
