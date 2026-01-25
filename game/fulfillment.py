"""
Anachron - Fulfillment Module

Tracks the three anchors of fulfillment invisibly:
- Belonging: Community, acceptance, found family
- Legacy: Lasting impact, teaching, building  
- Freedom: Autonomy, self-determination, independence

These are NEVER shown to the player as numbers. The AI narrator
detects anchor-relevant choices and the game tracks them internally.
The player only experiences the narrative consequences.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum

from config import ANCHORS


class AnchorLevel(Enum):
    """Qualitative levels for each anchor"""
    NONE = "none"           # 0-19: No real progress
    EMERGING = "emerging"   # 20-39: Starting to form
    GROWING = "growing"     # 40-59: Taking shape
    STRONG = "strong"       # 60-79: Significant presence
    ARRIVED = "arrived"     # 80-89: Could stay for this
    MASTERY = "mastery"     # 90-100: Fully realized


@dataclass
class Anchor:
    """Single fulfillment anchor with history"""
    
    name: str
    value: int = 0
    history: List[Tuple[int, str, int]] = field(default_factory=list)
    # History entries: (turn_number, reason, delta)
    
    @property
    def level(self) -> AnchorLevel:
        """Current qualitative level"""
        if self.value >= 90:
            return AnchorLevel.MASTERY
        elif self.value >= 80:
            return AnchorLevel.ARRIVED
        elif self.value >= 60:
            return AnchorLevel.STRONG
        elif self.value >= 40:
            return AnchorLevel.GROWING
        elif self.value >= 20:
            return AnchorLevel.EMERGING
        else:
            return AnchorLevel.NONE
    
    @property
    def has_arrived(self) -> bool:
        """Has player reached 'arrival' on this anchor?"""
        threshold = ANCHORS[self.name.lower()]["arrival_threshold"]
        return self.value >= threshold
    
    @property
    def has_mastery(self) -> bool:
        """Has player achieved mastery?"""
        threshold = ANCHORS[self.name.lower()]["mastery_threshold"]
        return self.value >= threshold
    
    def adjust(self, delta: int, turn: int, reason: str):
        """Adjust anchor value and record history"""
        old_value = self.value
        self.value = max(0, min(100, self.value + delta))
        actual_delta = self.value - old_value
        if actual_delta != 0:
            self.history.append((turn, reason, actual_delta))
    
    def reset_for_new_era(self, retention_rate: float = 0.3):
        """
        When jumping to a new era, anchors partially reset.
        Belonging resets most (you lose your people).
        Legacy partially persists (impact remains).
        Freedom partially persists (skills/mindset remain).
        """
        self.value = int(self.value * retention_rate)
        self.history.append((-1, "era_transition", self.value - int(self.value / retention_rate)))


@dataclass  
class FulfillmentState:
    """
    Tracks all three anchors for a player's journey.
    
    This is the soul of the "finding happiness" mechanic.
    """
    
    belonging: Anchor = field(default_factory=lambda: Anchor("Belonging"))
    legacy: Anchor = field(default_factory=lambda: Anchor("Legacy"))
    freedom: Anchor = field(default_factory=lambda: Anchor("Freedom"))
    
    current_turn: int = 0
    
    # Track last milestone levels to detect crossings (new field, additive)
    _last_belonging_level: str = field(default="none", repr=False)
    _last_legacy_level: str = field(default="none", repr=False)
    _last_freedom_level: str = field(default="none", repr=False)
    
    def get_anchor(self, name: str) -> Anchor:
        """Get anchor by name"""
        return getattr(self, name.lower())
    
    def adjust(self, anchor_name: str, delta: int, reason: str):
        """Adjust a specific anchor"""
        anchor = self.get_anchor(anchor_name)
        anchor.adjust(delta, self.current_turn, reason)
    
    def advance_turn(self):
        """Advance the turn counter"""
        self.current_turn += 1
    
    @property
    def can_stay(self) -> bool:
        """Has player built enough to make staying meaningful?"""
        return any([
            self.belonging.has_arrived,
            self.legacy.has_arrived,
            self.freedom.has_arrived
        ])
    
    @property
    def arrival_anchors(self) -> List[str]:
        """Which anchors have reached 'arrival' level?"""
        arrived = []
        if self.belonging.has_arrived:
            arrived.append("belonging")
        if self.legacy.has_arrived:
            arrived.append("legacy")
        if self.freedom.has_arrived:
            arrived.append("freedom")
        return arrived
    
    @property
    def dominant_anchor(self) -> Optional[str]:
        """Which anchor is strongest?"""
        anchors = [
            ("belonging", self.belonging.value),
            ("legacy", self.legacy.value),
            ("freedom", self.freedom.value)
        ]
        anchors.sort(key=lambda x: x[1], reverse=True)
        if anchors[0][1] > 0:
            return anchors[0][0]
        return None
    
    @property
    def has_full_happiness(self) -> bool:
        """Has player achieved all three anchors at arrival level?"""
        return all([
            self.belonging.has_arrived,
            self.legacy.has_arrived,
            self.freedom.has_arrived
        ])
    
    def transition_to_new_era(self):
        """
        Handle anchor changes when jumping to a new era.
        
        The emotional weight of leaving:
        - Belonging resets significantly (you lose your people)
        - Legacy partially persists (what you built remains)
        - Freedom partially persists (your independence skills remain)
        """
        self.belonging.reset_for_new_era(retention_rate=0.2)  # Lose most belonging
        self.legacy.reset_for_new_era(retention_rate=0.5)     # Keep half of legacy
        self.freedom.reset_for_new_era(retention_rate=0.6)    # Keep most freedom
        
        # Reset milestone tracking for new era
        self._last_belonging_level = self.belonging.level.value
        self._last_legacy_level = self.legacy.level.value
        self._last_freedom_level = self.freedom.level.value
    
    def get_narrative_state(self) -> Dict:
        """
        Get state for AI narrator without exposing numbers.
        Returns qualitative descriptions only.
        """
        return {
            "belonging": {
                "level": self.belonging.level.value,
                "has_arrived": self.belonging.has_arrived,
                "recent_trend": self._get_trend(self.belonging)
            },
            "legacy": {
                "level": self.legacy.level.value,
                "has_arrived": self.legacy.has_arrived,
                "recent_trend": self._get_trend(self.legacy)
            },
            "freedom": {
                "level": self.freedom.level.value,
                "has_arrived": self.freedom.has_arrived,
                "recent_trend": self._get_trend(self.freedom)
            },
            "can_stay": self.can_stay,
            "dominant_anchor": self.dominant_anchor,
            "has_full_happiness": self.has_full_happiness
        }
    
    def _get_trend(self, anchor: Anchor) -> str:
        """Get recent trend for an anchor"""
        recent = [h for h in anchor.history if h[0] >= self.current_turn - 3]
        if not recent:
            return "stable"
        total_delta = sum(h[2] for h in recent)
        if total_delta > 5:
            return "rising"
        elif total_delta < -5:
            return "falling"
        else:
            return "stable"
    
    def get_ending_type(self) -> str:
        """
        Determine ending type based on final anchor state.
        Called when player chooses to stay.
        """
        arrived = self.arrival_anchors
        
        if len(arrived) == 3:
            return "complete"  # Achieved all three - rare, masterful
        elif len(arrived) == 2:
            return "balanced"  # Two anchors - good ending
        elif len(arrived) == 1:
            return arrived[0]  # Single anchor ending
        else:
            return "searching"  # Chose to stay without real fulfillment

    # =========================================================================
    # NEW: PROGRESS TRACKING FOR FRONTEND (additive - does not change existing)
    # =========================================================================
    
    def get_progress_for_frontend(self) -> Dict:
        """
        Get progress state for frontend display.
        
        Returns qualitative levels and trends that can be shown to players
        without exposing raw numbers. This enables progress feedback while
        maintaining narrative immersion.
        
        Returns:
            Dict with structure:
            {
                "belonging": {"level": "emerging", "trend": "rising"},
                "legacy": {"level": "none", "trend": "stable"},
                "freedom": {"level": "growing", "trend": "stable"},
                "dominant": "belonging" | None,
                "journey_phase": "wandering" | "finding_footing" | "building_roots" | "approaching_home" | "home",
                "can_stay": False,
                "arrived_anchors": []
            }
        """
        return {
            "belonging": {
                "level": self.belonging.level.value,
                "trend": self._get_trend(self.belonging)
            },
            "legacy": {
                "level": self.legacy.level.value,
                "trend": self._get_trend(self.legacy)
            },
            "freedom": {
                "level": self.freedom.level.value,
                "trend": self._get_trend(self.freedom)
            },
            "dominant": self.dominant_anchor,
            "journey_phase": self._get_journey_phase(),
            "can_stay": self.can_stay,
            "arrived_anchors": self.arrival_anchors
        }
    
    def _get_journey_phase(self) -> str:
        """
        Determine the narrative phase of the player's journey.
        
        This provides a high-level "how am I doing" indicator without
        exposing the underlying numbers.
        
        Returns one of:
        - "wandering": No real progress yet (all anchors < 20)
        - "finding_footing": Starting to build something (highest anchor 20-39)
        - "building_roots": Making real progress (highest anchor 40-59)
        - "approaching_home": Close to being able to stay (highest anchor 60-79)
        - "home": Can meaningfully stay (any anchor >= 80)
        """
        if self.can_stay:
            return "home"
        
        highest_value = max(
            self.belonging.value,
            self.legacy.value,
            self.freedom.value
        )
        
        if highest_value >= 60:
            return "approaching_home"
        elif highest_value >= 40:
            return "building_roots"
        elif highest_value >= 20:
            return "finding_footing"
        else:
            return "wandering"
    
    def check_milestone_crossed(self) -> Optional[Dict]:
        """
        Check if any anchor just crossed a milestone threshold.
        
        Call this AFTER adjusting anchors to detect level-ups.
        Returns milestone info if one was crossed, None otherwise.
        
        Milestones are crossed when an anchor moves from one level to a higher one.
        We track the last known level and compare to current.
        
        Returns:
            None if no milestone crossed, or Dict:
            {
                "anchor": "belonging" | "legacy" | "freedom",
                "old_level": "none",
                "new_level": "emerging",
                "message": "Narrative hint about the progress"
            }
        """
        milestones_crossed = []
        
        # Check each anchor
        current_belonging = self.belonging.level.value
        if self._level_increased(self._last_belonging_level, current_belonging):
            milestones_crossed.append({
                "anchor": "belonging",
                "old_level": self._last_belonging_level,
                "new_level": current_belonging,
                "message": self._get_milestone_message("belonging", current_belonging)
            })
        self._last_belonging_level = current_belonging
        
        current_legacy = self.legacy.level.value
        if self._level_increased(self._last_legacy_level, current_legacy):
            milestones_crossed.append({
                "anchor": "legacy",
                "old_level": self._last_legacy_level,
                "new_level": current_legacy,
                "message": self._get_milestone_message("legacy", current_legacy)
            })
        self._last_legacy_level = current_legacy
        
        current_freedom = self.freedom.level.value
        if self._level_increased(self._last_freedom_level, current_freedom):
            milestones_crossed.append({
                "anchor": "freedom",
                "old_level": self._last_freedom_level,
                "new_level": current_freedom,
                "message": self._get_milestone_message("freedom", current_freedom)
            })
        self._last_freedom_level = current_freedom
        
        # Return the most significant milestone (highest new level)
        if milestones_crossed:
            level_order = ["none", "emerging", "growing", "strong", "arrived", "mastery"]
            milestones_crossed.sort(
                key=lambda m: level_order.index(m["new_level"]),
                reverse=True
            )
            return milestones_crossed[0]
        
        return None
    
    def _level_increased(self, old_level: str, new_level: str) -> bool:
        """Check if level increased (not just changed)"""
        level_order = ["none", "emerging", "growing", "strong", "arrived", "mastery"]
        try:
            old_idx = level_order.index(old_level)
            new_idx = level_order.index(new_level)
            return new_idx > old_idx
        except ValueError:
            return False
    
    def _get_milestone_message(self, anchor: str, level: str) -> str:
        """
        Get a narrative-appropriate message for reaching a milestone.
        
        These messages hint at progress without being gamey or breaking immersion.
        """
        messages = {
            "belonging": {
                "emerging": "You sense the first threads of connection forming.",
                "growing": "Familiar faces greet you now. This place knows you.",
                "strong": "You matter to people here. They would miss you.",
                "arrived": "This could be home. These could be your people.",
                "mastery": "You belong here, completely and without doubt."
            },
            "legacy": {
                "emerging": "Your actions are beginning to ripple outward.",
                "growing": "What you've started here will outlast this moment.",
                "strong": "Your mark on this place is becoming permanent.",
                "arrived": "You've built something that will endure.",
                "mastery": "Your legacy here is complete and lasting."
            },
            "freedom": {
                "emerging": "You're learning to move through this world unbound.",
                "growing": "The constraints of this era cannot hold you.",
                "strong": "You've carved out true independence here.",
                "arrived": "You are free here, on your own terms.",
                "mastery": "Complete freedom is yours in this time."
            }
        }
        
        return messages.get(anchor, {}).get(level, "Something has shifted.")
    
    def initialize_milestone_tracking(self):
        """
        Initialize milestone tracking with current levels.
        Call this when starting a new game or entering a new era.
        """
        self._last_belonging_level = self.belonging.level.value
        self._last_legacy_level = self.legacy.level.value
        self._last_freedom_level = self.freedom.level.value


# =============================================================================
# AI INTEGRATION HELPERS
# =============================================================================

def get_anchor_detection_prompt() -> str:
    """
    Returns instructions for AI to detect anchor-relevant choices.
    Used in system prompt.
    """
    return """
FULFILLMENT TRACKING (Internal - never mention to player):

Track these three dimensions based on player choices:

BELONGING signals:
- Helping others at personal cost
- Returning to same people instead of moving on
- Sharing resources rather than hoarding
- Defending others at risk to self
- Learning names, honoring customs
- Building trust over time

LEGACY signals:
- Teaching someone a skill
- Building something lasting
- Starting projects with long-term payoff
- Mentoring specific individuals
- Introducing knowledge carefully
- Creating institutions or traditions

FREEDOM signals:
- Refusing imposed roles
- Maintaining self-sufficiency
- Exploring rather than settling
- Walking away from compromising situations
- Keeping options open
- Escaping systems that trap others

After each player choice, assess which anchors were affected and by how much.
Include this ONLY in a hidden tag at the end of your response:

<anchors>belonging[+/-X] legacy[+/-X] freedom[+/-X]</anchors>

X should typically be 0-10 for minor choices, 10-20 for significant ones.
Most choices affect 1-2 anchors. Some affect none. Rarely do all three change.
"""


def parse_anchor_adjustments(response: str) -> Dict[str, int]:
    """
    Parse anchor adjustments from AI response.
    Returns dict of anchor_name -> delta
    """
    import re
    
    adjustments = {"belonging": 0, "legacy": 0, "freedom": 0}
    
    match = re.search(
        r'<anchors>\s*belonging\[([+\-]?\d+)\]\s*legacy\[([+\-]?\d+)\]\s*freedom\[([+\-]?\d+)\]\s*</anchors>',
        response,
        re.IGNORECASE
    )
    
    if match:
        adjustments["belonging"] = int(match.group(1))
        adjustments["legacy"] = int(match.group(2))
        adjustments["freedom"] = int(match.group(3))
    
    return adjustments


def strip_anchor_tags(response: str) -> str:
    """Remove anchor tags from response before showing to player"""
    import re
    return re.sub(r'<anchors>.*?</anchors>', '', response, flags=re.IGNORECASE | re.DOTALL).strip()
