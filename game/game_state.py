"""
Anachron - Game State Module

Central game state that coordinates all systems:
- Time machine
- Fulfillment anchors
- Inventory
- Era and narrative state

Includes full serialization support for save/load functionality.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

from config import MODES, TURNS_PER_YEAR
from time_machine import TimeMachine, DeviceState
from fulfillment import FulfillmentState, Anchor
from items import Inventory, Item


class GameMode(Enum):
    KID = "kid"
    MATURE = "mature"


class RegionPreference(Enum):
    EUROPEAN = "european"      # European/Western eras only
    WORLDWIDE = "worldwide"    # All eras


class GamePhase(Enum):
    """Current phase of the game"""
    SETUP = "setup"             # Initial setup
    ARRIVAL = "arrival"         # Just arrived in new era
    LIVING = "living"           # Normal gameplay in era
    WINDOW_OPEN = "window_open" # Time machine window is active
    STAYING = "staying"         # Chose to stay, playing out ending
    TRAVELING = "traveling"     # Using window to leave
    ENDED = "ended"             # Game complete


@dataclass
class EraState:
    """State for the current era"""
    
    era_id: str
    era_name: str
    era_year: int
    era_location: str
    
    turns_in_era: int = 0
    character_name: Optional[str] = None
    
    # Relationships built (for narrative continuity)
    relationships: List[Dict] = field(default_factory=list)
    
    # Key events that have happened
    events: List[str] = field(default_factory=list)
    
    # Player's current situation summary
    situation: str = ""
    
    def advance_turn(self):
        self.turns_in_era += 1
    
    @property
    def time_in_era_description(self) -> str:
        """Human-readable time spent in era"""
        turns = self.turns_in_era
        
        # 7 turns = 1 year, so each turn is ~7-8 weeks
        if turns == 0:
            return "just arrived"
        elif turns == 1:
            return "a few weeks"
        elif turns == 2:
            return "a couple months"
        elif turns <= 4:
            return "several months"
        elif turns <= 6:
            return "most of a year"
        elif turns <= 7:
            return "about a year"
        elif turns <= 14:
            return f"about {turns // 7} years"
        else:
            years = turns // 7
            return f"over {years} years"
    
    def to_dict(self) -> Dict:
        """Serialize era state"""
        return {
            "era_id": self.era_id,
            "era_name": self.era_name,
            "era_year": self.era_year,
            "era_location": self.era_location,
            "turns_in_era": self.turns_in_era,
            "character_name": self.character_name,
            "relationships": self.relationships,
            "events": self.events,
            "situation": self.situation
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "EraState":
        """Deserialize era state"""
        era = cls(
            era_id=data["era_id"],
            era_name=data["era_name"],
            era_year=data["era_year"],
            era_location=data["era_location"]
        )
        era.turns_in_era = data.get("turns_in_era", 0)
        era.character_name = data.get("character_name")
        era.relationships = data.get("relationships", [])
        era.events = data.get("events", [])
        era.situation = data.get("situation", "")
        return era


@dataclass
class GameState:
    """
    Complete game state.
    
    This is the single source of truth for the entire game.
    """
    
    # Core systems
    time_machine: TimeMachine = field(default_factory=TimeMachine)
    fulfillment: FulfillmentState = field(default_factory=FulfillmentState)
    inventory: Inventory = field(default_factory=Inventory)
    
    # Current era
    current_era: Optional[EraState] = None
    
    # Game settings
    mode: GameMode = GameMode.KID
    region_preference: RegionPreference = RegionPreference.WORLDWIDE
    player_name: str = ""
    
    # Phase tracking
    phase: GamePhase = GamePhase.SETUP
    
    # History across eras
    era_history: List[Dict] = field(default_factory=list)
    
    # Timestamps
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    
    # Ending info
    ending_type: Optional[str] = None
    final_era: Optional[str] = None
    
    # Session persistence - stores the last narrative and choices for resume
    last_narrative: str = ""
    last_choices: List[Dict] = field(default_factory=list)
    
    # AI conversation history for current era (needed for narrative continuity)
    conversation_history: List[Dict] = field(default_factory=list)
    
    # Unified event log for ending generation (persists across eras)
    game_events: List[Dict] = field(default_factory=list)
    
    def start_game(self, player_name: str, mode: GameMode, region: RegionPreference = RegionPreference.WORLDWIDE):
        """Initialize a new game"""
        self.player_name = player_name
        self.mode = mode
        self.region_preference = region
        self.started_at = datetime.now()
        self.phase = GamePhase.SETUP
        self.inventory = Inventory.create_starting()
    
    def enter_era(self, era: Dict):
        """Enter a new era"""
        # Save previous era to history if exists
        if self.current_era:
            self._save_era_to_history()
        
        # Create new era state
        self.current_era = EraState(
            era_id=era["id"],
            era_name=era["name"],
            era_year=era["year"],
            era_location=era["location"]
        )
        
        # Handle fulfillment transition if not first era
        if self.era_history:
            self.fulfillment.transition_to_new_era()
        
        # IMPORTANT: Close the window and reset turns when entering new era
        # This ensures window is always closed on arrival
        self.time_machine.window_active = False
        self.time_machine.window_turns_remaining = 0
        self.time_machine.turns_since_last_window = 0
        self.time_machine._accumulated_probability = 0.0
        
        # Track era if not already tracked (travel() may have added it)
        if era["id"] not in self.time_machine.eras_visited:
            self.time_machine.eras_visited.append(era["id"])
        
        # Clear conversation history for new era
        self.conversation_history = []
        
        # Note: game_events is NOT cleared - it persists across eras
        # to capture the full journey for ending generation
        
        self.phase = GamePhase.ARRIVAL
    
    def set_last_turn(self, narrative: str, choices: List[Dict]):
        """Store the last narrative and choices for session resume"""
        self.last_narrative = narrative
        self.last_choices = choices
    
    # =========================================================================
    # GAME EVENTS LOG - for ending generation
    # =========================================================================
    
    def log_event(self, event_type: str, **kwargs):
        """
        Log a game event for later use in ending generation.
        
        Event types:
        - "relationship": NPC interaction {name: str}
        - "defining_moment": Large anchor shift {anchor: str, delta: int, context: str}
        - "wisdom": Player demonstrated historical understanding {id: str, insight: str}
        - "item_use": Player used an item {item_id: str, context: str}
        - "era_arrival": Arrived in new era {era_id: str, era_name: str}
        - "character_named": Player given a name {name: str}
        
        All events automatically include:
        - turn: current total turn count
        - era_id: current era (if any)
        """
        event = {
            "type": event_type,
            "turn": self.total_turns,
            "era_id": self.current_era.era_id if self.current_era else None,
            **kwargs
        }
        self.game_events.append(event)
    
    def get_events_by_type(self, event_type: str) -> List[Dict]:
        """Retrieve all events of a specific type."""
        return [e for e in self.game_events if e["type"] == event_type]
    
    def get_recent_events(self, count: int = 10) -> List[Dict]:
        """Get the most recent events across all types."""
        return self.game_events[-count:] if self.game_events else []
    
    def get_events_for_era(self, era_id: str) -> List[Dict]:
        """Get all events that occurred in a specific era."""
        return [e for e in self.game_events if e.get("era_id") == era_id]
    
    # =========================================================================
    # TURN AND PHASE MANAGEMENT
    # =========================================================================
    
    def advance_turn(self) -> Dict[str, Any]:
        """
        Advance one turn and return events that occurred.
        
        Returns dict with:
        - window_opened: bool - Window just opened THIS turn
        - window_closing: bool - Window is on its last turn
        - window_closed: bool - Window just closed (player let it expire)
        - window_active_after_turn: bool - Window is active after this turn
        """
        events = {
            "window_opened": False,
            "window_closing": False,
            "window_closed": False,
            "window_active_after_turn": False
        }
        
        # Track if window was already open
        was_active = self.time_machine.window_active
        
        # Advance era turn counter
        if self.current_era:
            self.current_era.advance_turn()
        
        self.fulfillment.advance_turn()
        
        # Check time machine - this may open or close the window
        window_opened = self.time_machine.advance_turn()
        
        if window_opened:
            events["window_opened"] = True
            self.phase = GamePhase.WINDOW_OPEN
        elif was_active and not self.time_machine.window_active:
            events["window_closed"] = True
            self.phase = GamePhase.LIVING
        elif self.time_machine.window_active and self.time_machine.window_turns_remaining == 1:
            events["window_closing"] = True
        
        # Set authoritative post-turn window state
        events["window_active_after_turn"] = self.time_machine.window_active
        
        return events
    
    def choose_to_stay(self, is_final: bool = False):
        """Player chooses to stay in current era"""
        if is_final:
            # This is the final staying - end game
            self.phase = GamePhase.STAYING
            self.ending_type = self.fulfillment.get_ending_type()
            self.final_era = self.current_era.era_id if self.current_era else None
        else:
            # Just letting window close
            self.time_machine.choose_to_stay()
            self.phase = GamePhase.LIVING
    
    def choose_to_travel(self):
        """Player chooses to use the window"""
        self.phase = GamePhase.TRAVELING
    
    def complete_travel(self, new_era: Dict):
        """Complete travel to new era"""
        self.time_machine.travel(new_era["id"])
        self.enter_era(new_era)
    
    def end_game(self):
        """Finalize game ending"""
        self._save_era_to_history()
        self.phase = GamePhase.ENDED
        self.ended_at = datetime.now()
    
    def _save_era_to_history(self):
        """Save current era state to history"""
        if not self.current_era:
            return
        
        self.era_history.append({
            "era_id": self.current_era.era_id,
            "era_name": self.current_era.era_name,
            "turns": self.current_era.turns_in_era,
            "character_name": self.current_era.character_name,
            "relationships": self.current_era.relationships.copy(),
            "events": self.current_era.events.copy(),
            "fulfillment_snapshot": {
                "belonging": self.fulfillment.belonging.value,
                "legacy": self.fulfillment.legacy.value,
                "freedom": self.fulfillment.freedom.value
            }
        })
    
    @property
    def can_stay_meaningfully(self) -> bool:
        """Has player built enough to make staying meaningful?"""
        return self.fulfillment.can_stay
    
    @property
    def total_turns(self) -> int:
        """Total turns across all eras"""
        return self.time_machine.total_turns
    
    @property
    def eras_count(self) -> int:
        """Number of eras visited"""
        return len(self.time_machine.eras_visited)
    
    def get_narrative_context(self) -> Dict:
        """
        Get full context for AI narrator.
        This is what the AI uses to generate responses.
        """
        return {
            "mode": self.mode.value,
            "player_name": self.player_name,
            "current_era": {
                "id": self.current_era.era_id,
                "name": self.current_era.era_name,
                "year": self.current_era.era_year,
                "location": self.current_era.era_location,
                "turns": self.current_era.turns_in_era,
                "time_description": self.current_era.time_in_era_description,
                "character_name": self.current_era.character_name,
                "relationships": self.current_era.relationships,
                "recent_events": self.current_era.events[-5:] if self.current_era.events else []
            } if self.current_era else None,
            "items": self.inventory.to_narrative_dict(),
            "fulfillment": self.fulfillment.get_narrative_state(),
            "time_machine": {
                "indicator": self.time_machine.indicator.value,
                "window_active": self.time_machine.window_active,
                "window_turns_remaining": self.time_machine.window_turns_remaining,
                "eras_visited_count": len(self.time_machine.eras_visited),
            },
            "phase": self.phase.value,
            "can_stay_meaningfully": self.can_stay_meaningfully,
            "era_history_summary": [
                {"era": h["era_name"], "turns": h["turns"]} 
                for h in self.era_history
            ]
        }
    
    def to_save_dict(self) -> Dict:
        """Serialize complete game state for saving"""
        return {
            "version": "1.1",  # Bumped version - removed snapshot
            "saved_at": datetime.now().isoformat(),
            
            # Player info
            "player_name": self.player_name,
            "mode": self.mode.value,
            "region_preference": self.region_preference.value,
            "phase": self.phase.value,
            
            # Timestamps
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            
            # Ending info
            "ending_type": self.ending_type,
            "final_era": self.final_era,
            
            # Current era
            "current_era": self.current_era.to_dict() if self.current_era else None,
            
            # Era history
            "era_history": self.era_history,
            
            # Time machine state
            "time_machine": {
                "turns_since_last_window": self.time_machine.turns_since_last_window,
                "window_active": self.time_machine.window_active,
                "window_turns_remaining": self.time_machine.window_turns_remaining,
                "eras_visited": self.time_machine.eras_visited,
                "total_turns": self.time_machine.total_turns,
                "_accumulated_probability": self.time_machine._accumulated_probability,
                "display": {
                    "current_year": self.time_machine.display.current_year,
                    "current_location": self.time_machine.display.current_location,
                    "current_era_name": self.time_machine.display.current_era_name
                }
            },
            
            # Fulfillment state
            "fulfillment": {
                "belonging": {
                    "value": self.fulfillment.belonging.value,
                    "history": self.fulfillment.belonging.history
                },
                "legacy": {
                    "value": self.fulfillment.legacy.value,
                    "history": self.fulfillment.legacy.history
                },
                "freedom": {
                    "value": self.fulfillment.freedom.value,
                    "history": self.fulfillment.freedom.history
                },
                "current_turn": self.fulfillment.current_turn
            },
            
            # Inventory state
            "inventory": {
                "items": [
                    {
                        "id": item.id,
                        "uses": item.uses,
                        "is_depleted": item.is_depleted,
                        "is_revealed": item.is_revealed,
                        "times_used": item.times_used
                    }
                    for item in self.inventory.modern_items
                ]
            },
            
            # Session resume data
            "last_narrative": self.last_narrative,
            "last_choices": self.last_choices,
            "conversation_history": self.conversation_history,
            
            # Event log for ending generation
            "game_events": self.game_events
        }
    
    @classmethod
    def from_save_dict(cls, data: Dict) -> "GameState":
        """Deserialize game state from save data"""
        state = cls()
        
        # Player info
        state.player_name = data.get("player_name", "")
        state.mode = GameMode(data.get("mode", "kid"))
        state.region_preference = RegionPreference(data.get("region_preference", "worldwide"))
        state.phase = GamePhase(data.get("phase", "setup"))
        
        # Timestamps
        if data.get("started_at"):
            state.started_at = datetime.fromisoformat(data["started_at"])
        if data.get("ended_at"):
            state.ended_at = datetime.fromisoformat(data["ended_at"])
        
        # Ending info
        state.ending_type = data.get("ending_type")
        state.final_era = data.get("final_era")
        
        # Current era
        if data.get("current_era"):
            state.current_era = EraState.from_dict(data["current_era"])
        
        # Era history
        state.era_history = data.get("era_history", [])
        
        # Time machine state
        tm_data = data.get("time_machine", {})
        state.time_machine.turns_since_last_window = tm_data.get("turns_since_last_window", 0)
        state.time_machine.window_active = tm_data.get("window_active", False)
        state.time_machine.window_turns_remaining = tm_data.get("window_turns_remaining", 0)
        state.time_machine.eras_visited = tm_data.get("eras_visited", [])
        state.time_machine.total_turns = tm_data.get("total_turns", 0)
        state.time_machine._accumulated_probability = tm_data.get("_accumulated_probability", 0.0)
        
        display_data = tm_data.get("display", {})
        state.time_machine.display.current_year = display_data.get("current_year", 0)
        state.time_machine.display.current_location = display_data.get("current_location", "")
        state.time_machine.display.current_era_name = display_data.get("current_era_name", "")
        
        # Fulfillment state
        ff_data = data.get("fulfillment", {})
        
        belonging_data = ff_data.get("belonging", {})
        state.fulfillment.belonging.value = belonging_data.get("value", 0)
        state.fulfillment.belonging.history = [tuple(h) for h in belonging_data.get("history", [])]
        
        legacy_data = ff_data.get("legacy", {})
        state.fulfillment.legacy.value = legacy_data.get("value", 0)
        state.fulfillment.legacy.history = [tuple(h) for h in legacy_data.get("history", [])]
        
        freedom_data = ff_data.get("freedom", {})
        state.fulfillment.freedom.value = freedom_data.get("value", 0)
        state.fulfillment.freedom.history = [tuple(h) for h in freedom_data.get("history", [])]
        
        state.fulfillment.current_turn = ff_data.get("current_turn", 0)
        
        # Inventory state - restore from starting items and apply saved state
        state.inventory = Inventory.create_starting()
        inv_data = data.get("inventory", {})
        for item_state in inv_data.get("items", []):
            item = state.inventory.get_item(item_state.get("id", ""))
            if item:
                item.uses = item_state.get("uses")
                item.is_depleted = item_state.get("is_depleted", False)
                item.is_revealed = item_state.get("is_revealed", False)
                item.times_used = item_state.get("times_used", 0)
        
        # Session resume data
        state.last_narrative = data.get("last_narrative", "")
        state.last_choices = data.get("last_choices", [])
        state.conversation_history = data.get("conversation_history", [])
        
        # Event log
        state.game_events = data.get("game_events", [])
        
        return state
