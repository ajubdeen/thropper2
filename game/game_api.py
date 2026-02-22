#!/usr/bin/env python3
"""
Anachron - Game API Module

JSON-based API for the game, designed for web/mobile frontends.
Separates game logic from presentation entirely.

All methods return structured JSON that frontends can render as they wish.

Features:
- User ID support for multi-user deployments
- Save/load game state for session persistence
- Resume functionality with full narrative/choice restoration
- Intent-based choice resolution (not position-based)
"""

import json
import random
import re
import os
from typing import Optional, Generator, Dict, Any, List
from datetime import datetime
from dataclasses import dataclass, asdict

# Try to import anthropic
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

# Local imports
from config import EUROPEAN_ERA_IDS, get_debug_era_id, NARRATIVE_MODEL, PREMIUM_MODEL
from game_state import GameState, GameMode, GamePhase, RegionPreference
from time_machine import select_random_era, IndicatorState
from fulfillment import parse_anchor_adjustments, strip_anchor_tags
from items import parse_item_usage
from event_parsing import (
    parse_character_name, parse_key_npcs, parse_wisdom_moment,
    strip_event_tags, check_defining_moment
)
from eras import ERAS, get_era_by_id, get_wisdom_path_by_id
from prompts import (
    get_system_prompt, get_arrival_prompt, get_turn_prompt,
    get_window_prompt, get_staying_ending_prompt, get_leaving_prompt,
    get_historian_narrative_prompt, get_quit_ending_prompt
)
from scoring import calculate_score, Leaderboard, AoAEntry, AnnalsOfAnachron
from db_storage import DatabaseSaveManager, DatabaseLeaderboardStorage, DatabaseGameHistory
from choice_intent import (
    ChoiceIntent, detect_choice_intent, filter_choices, 
    get_choice_intent_for_submission
)


# =============================================================================
# MESSAGE TYPES
# =============================================================================

class MessageType:
    """Types of messages the API can emit"""
    # Game flow
    GAME_START = "game_start"
    GAME_END = "game_end"
    GAME_SAVED = "game_saved"
    GAME_LOADED = "game_loaded"
    GAME_RESUMED = "game_resumed"
    
    # Screens/phases
    TITLE = "title"
    SETUP_NAME = "setup_name"
    SETUP_REGION = "setup_region"
    INTRO_STORY = "intro_story"
    INTRO_ITEMS = "intro_items"
    INTRO_DEVICE = "intro_device"
    
    # Gameplay
    ERA_ARRIVAL = "era_arrival"
    ERA_SUMMARY = "era_summary"
    NARRATIVE = "narrative"
    NARRATIVE_CHUNK = "narrative_chunk"  # For streaming
    CHOICES = "choices"
    DEVICE_STATUS = "device_status"
    WINDOW_OPEN = "window_open"
    WINDOW_CLOSING = "window_closing"
    WINDOW_CLOSED = "window_closed"
    
    # Endings
    DEPARTURE = "departure"
    STAYING_FOREVER = "staying_forever"
    ENDING_NARRATIVE = "ending_narrative"
    FINAL_SCORE = "final_score"
    
    # System
    WAITING_INPUT = "waiting_input"
    ERROR = "error"
    LOADING = "loading"
    
    # User data
    USER_GAMES = "user_games"
    LEADERBOARD = "leaderboard"
    ANNALS = "annals"
    ANNALS_ENTRY = "annals_entry"
    
    # Progress feedback (new - for player engagement)
    JOURNEY_PROGRESS = "journey_progress"
    PROGRESS_MILESTONE = "progress_milestone"
    HISTORICAL_WISDOM = "historical_wisdom"


def emit(msg_type: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
    """Create a standardized message"""
    return {
        "type": msg_type,
        "data": data or {},
        "timestamp": datetime.now().isoformat()
    }


# =============================================================================
# NARRATIVE ENGINE (JSON-based)
# =============================================================================

class NarrativeEngine:
    """Handles AI-generated narrative with JSON output"""
    
    def __init__(self, game_state: GameState):
        self.game_state = game_state
        self.messages = []
        self.system_prompt = ""
        
        if ANTHROPIC_AVAILABLE:
            self.client = anthropic.Anthropic()
        else:
            self.client = None
    
    def set_era(self, era: dict):
        """Set up system prompt for current era"""
        self.system_prompt = get_system_prompt(self.game_state, era)
        self.messages = []
    
    def restore_conversation(self, messages: List[Dict]):
        """Restore conversation history from saved state"""
        self.messages = messages
    
    def get_conversation_history(self) -> List[Dict]:
        """Get current conversation history for saving"""
        return self.messages.copy()
    
    def generate_streaming(self, user_prompt: str, model: str = None, temperature: float = None) -> Generator[Dict, None, str]:
        """
        Generate narrative response with streaming.
        Yields message dicts, returns full response.

        Args:
            user_prompt: The prompt to send
            model: Override model (defaults to NARRATIVE_MODEL for gameplay)
            temperature: Override temperature (defaults to API default if None)
        """
        self.messages.append({"role": "user", "content": user_prompt})

        if not self.client:
            response = self._demo_response(user_prompt)
            # Simulate streaming for demo mode
            words = response.split(' ')
            for i, word in enumerate(words):
                chunk = word + (' ' if i < len(words) - 1 else '')
                yield emit(MessageType.NARRATIVE_CHUNK, {"text": chunk})
        else:
            response = yield from self._api_call_streaming(model=model or NARRATIVE_MODEL, temperature=temperature)

        self.messages.append({"role": "assistant", "content": response})
        return response

    def generate(self, user_prompt: str, model: str = None) -> str:
        """Generate narrative response (non-streaming).

        Args:
            user_prompt: The prompt to send
            model: Override model (defaults to PREMIUM_MODEL for one-time generations)
        """
        self.messages.append({"role": "user", "content": user_prompt})

        if not self.client:
            response = self._demo_response(user_prompt)
        else:
            response = self._api_call(model=model or PREMIUM_MODEL)

        self.messages.append({"role": "assistant", "content": response})
        return response
    
    def _api_call_streaming(self, model: str = NARRATIVE_MODEL, temperature: float = None) -> Generator[Dict, None, str]:
        """Make streaming API call, yield chunks, return full response"""
        response = ""
        buffer = ""
        in_hidden_tag = False

        # Tags that should be hidden from the player
        hidden_tag_patterns = ['<anchors>', '<character_name>', '<key_npc>', '<wisdom>']

        try:
            stream_kwargs = dict(
                model=model,
                max_tokens=1500,
                system=self.system_prompt,
                messages=self.messages,
            )
            if temperature is not None:
                stream_kwargs["temperature"] = temperature

            with self.client.messages.stream(**stream_kwargs) as api_stream:
                for text in api_stream.text_stream:
                    response += text
                    buffer += text
                    
                    # Check for any hidden tag opening
                    for tag_start in hidden_tag_patterns:
                        if tag_start in buffer and not in_hidden_tag:
                            before_tag = buffer.split(tag_start)[0]
                            if before_tag:
                                yield emit(MessageType.NARRATIVE_CHUNK, {"text": before_tag})
                            buffer = tag_start + buffer.split(tag_start, 1)[1]
                            in_hidden_tag = True
                            break
                    
                    # Check for tag closing
                    if in_hidden_tag:
                        # Check for any closing tag
                        closing_tags = ['</anchors>', '</character_name>', '</key_npc>', '</wisdom>']
                        for close_tag in closing_tags:
                            if close_tag in buffer:
                                after_tag = buffer.split(close_tag, 1)[1] if close_tag in buffer else ''
                                buffer = after_tag
                                in_hidden_tag = False
                                break
                    
                    # Emit non-tag content
                    if not in_hidden_tag and '<' not in buffer:
                        if buffer:
                            yield emit(MessageType.NARRATIVE_CHUNK, {"text": buffer})
                        buffer = ""
                    elif not in_hidden_tag and '<' in buffer and '>' in buffer:
                        # Check if this is a hidden tag
                        is_hidden = any(tag in buffer for tag in hidden_tag_patterns)
                        if not is_hidden:
                            yield emit(MessageType.NARRATIVE_CHUNK, {"text": buffer})
                            buffer = ""
            
            # Emit remaining buffer after cleaning all hidden tags
            if buffer and not in_hidden_tag:
                clean_buffer = buffer
                clean_buffer = re.sub(r'<anchors>.*?</anchors>', '', clean_buffer, flags=re.DOTALL)
                clean_buffer = re.sub(r'<character_name>.*?</character_name>', '', clean_buffer, flags=re.DOTALL | re.IGNORECASE)
                clean_buffer = re.sub(r'<key_npc>.*?</key_npc>', '', clean_buffer, flags=re.DOTALL | re.IGNORECASE)
                clean_buffer = re.sub(r'<wisdom>.*?</wisdom>', '', clean_buffer, flags=re.DOTALL | re.IGNORECASE)
                if clean_buffer.strip():
                    yield emit(MessageType.NARRATIVE_CHUNK, {"text": clean_buffer})
                    
        except Exception as e:
            yield emit(MessageType.ERROR, {"message": str(e)})
            response = self._demo_response("")
        
        return response
    
    def _api_call(self, model: str = PREMIUM_MODEL) -> str:
        """Make non-streaming API call"""
        try:
            response = self.client.messages.create(
                model=model,
                max_tokens=1500,
                system=self.system_prompt,
                messages=self.messages
            )
            return response.content[0].text
        except Exception as e:
            return self._demo_response("")
    
    def _demo_response(self, prompt: str) -> str:
        """Demo response when API unavailable"""
        prompt_lower = prompt.lower()

        # Check for ending prompts (stay forever or quit)
        if "stay permanently" in prompt_lower or "chosen to stay" in prompt_lower or "staying ending" in prompt_lower:
            return """The decision settles over you like the first warmth of spring after a long winter. This is where you belong now.

You look around at the familiar streets, the faces you've come to know, the life you've built here piece by piece. The device on your wrist feels lighter somehow, as if it too understands that your journey has found its destination.

Years pass. You build a home, not just of walls and roof, but of memories and relationships. The people here become your people. Your strange knowledge from another time becomes local wisdom, passed down to those who need it.

When you grow old, you sit by the fire and sometimes think of the world you left behind. But there is no regret. You found what you were searching for—not a time, but a place where you truly belonged.

The traveler's journey ends not with a return, but with an arrival."""

        # Check for quit/abandon prompts (historical context prompt)
        if "historical context" in prompt_lower:
            return """Some journeys end before the destination is found. You set down the device, its glow fading to nothing.

The weight of all the eras you've passed through settles on your shoulders. You carry fragments of each—memories of faces, echoes of choices made and unmade.

Perhaps another traveler will find the path you couldn't. Perhaps the device will call to someone else, someone who will find what you were seeking.

Your story here is over, but stories have a way of continuing in unexpected ways."""

        # Arrival prompt
        if "arrival" in prompt_lower or len(self.messages) <= 2:
            return """You stumble forward, catching yourself against rough stone. The air hits you first—woodsmoke, animal dung, something cooking. Your ears ring from the transition.

When your vision clears, you see a narrow street of packed earth. Wooden buildings lean against each other, their upper floors jutting out. People in rough wool and leather stop to stare at your strange clothing.

A woman carrying a basket of bread crosses herself and hurries past. A dog barks. Somewhere nearby, a hammer rings against metal.

You are Thomas the Stranger now—that's what they'll call you. Your device hangs cool against your chest, dormant. Your three items are hidden beneath your coat. You need shelter before dark, and you need to figure out when and where you are.

A tavern sign creaks in the wind ahead. To your left, a church bell tower rises above the rooftops. To your right, a blacksmith's forge glows orange through an open door.

[A] Head to the tavern - travelers gather there, and you need information
[B] Make for the church - sanctuary and perhaps a sympathetic ear
[C] Approach the blacksmith - honest work might earn trust faster than questions

<anchors>belonging[0] legacy[0] freedom[0]</anchors>"""

        # Default: regular gameplay turn
        return """Your choice sets events in motion. The day unfolds with unexpected consequences.

People are beginning to know your face now. Some nod in recognition. Others still eye you with suspicion. This place is becoming familiar, for better or worse.

[A] Press forward with your current path
[B] Seek out someone you've met before
[C] Take time to observe and plan

<anchors>belonging[+3] legacy[+1] freedom[+2]</anchors>"""


# =============================================================================
# GAME SAVE/LOAD MANAGER
# =============================================================================

class GameSaveManager:
    """Manages saving and loading game states"""
    
    def __init__(self, save_dir: str = "saves"):
        self.save_dir = save_dir
        self._ensure_dir()
    
    def _ensure_dir(self):
        """Ensure save directory exists"""
        if not os.path.exists(self.save_dir):
            try:
                os.makedirs(self.save_dir)
            except OSError:
                pass
    
    def _get_save_path(self, user_id: str, game_id: str) -> str:
        """Get path for a save file"""
        return os.path.join(self.save_dir, f"{user_id}_{game_id}.json")
    
    def _get_user_dir(self, user_id: str) -> str:
        """Get directory for user's saves"""
        return os.path.join(self.save_dir, user_id)
    
    def save_game(self, user_id: str, game_id: str, state: GameState) -> bool:
        """
        Save game state to file.
        Returns True if successful.
        """
        try:
            save_data = state.to_save_dict()
            save_data["user_id"] = user_id
            save_data["game_id"] = game_id
            
            filepath = self._get_save_path(user_id, game_id)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Save error: {e}")
            return False
    
    def load_game(self, user_id: str, game_id: str) -> Optional[GameState]:
        """
        Load game state from file.
        Returns GameState or None if not found.
        """
        try:
            filepath = self._get_save_path(user_id, game_id)
            if not os.path.exists(filepath):
                return None
            
            with open(filepath, 'r', encoding='utf-8') as f:
                save_data = json.load(f)
            
            return GameState.from_save_dict(save_data)
        except Exception as e:
            print(f"Load error: {e}")
            return None
    
    def delete_game(self, user_id: str, game_id: str) -> bool:
        """Delete a saved game"""
        try:
            filepath = self._get_save_path(user_id, game_id)
            if os.path.exists(filepath):
                os.remove(filepath)
            return True
        except Exception:
            return False
    
    def list_user_games(self, user_id: str) -> List[Dict]:
        """List all saved games for a user"""
        games = []
        prefix = f"{user_id}_"
        
        try:
            for filename in os.listdir(self.save_dir):
                if filename.startswith(prefix) and filename.endswith('.json'):
                    filepath = os.path.join(self.save_dir, filename)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            save_data = json.load(f)
                        
                        games.append({
                            "game_id": save_data.get("game_id", ""),
                            "player_name": save_data.get("player_name", "Unknown"),
                            "phase": save_data.get("phase", "unknown"),
                            "current_era": save_data.get("current_era", {}).get("era_name", "Unknown") if save_data.get("current_era") else None,
                            "total_turns": save_data.get("time_machine", {}).get("total_turns", 0),
                            "saved_at": save_data.get("saved_at", ""),
                            "started_at": save_data.get("started_at", "")
                        })
                    except Exception:
                        continue
        except Exception:
            pass
        
        # Sort by saved_at, newest first
        games.sort(key=lambda x: x.get("saved_at", ""), reverse=True)
        return games


# =============================================================================
# GAME API CLASS
# =============================================================================

class GameAPI:
    """
    JSON-based game API for web/mobile frontends.
    
    All methods yield or return structured message dicts.
    The frontend renders these however it wants.
    
    Supports:
    - User ID for multi-user deployments
    - Save/load for session persistence
    - Resume with full narrative restoration
    - Intent-based choice resolution
    """
    
    def __init__(self, user_id: str = "default"):
        self.user_id = user_id
        self.state = GameState()
        self.narrator = None
        self.current_era = None
        self._selected_region = RegionPreference.WORLDWIDE

        # History tracking (database-backed)
        self.history = DatabaseGameHistory()
        self.current_game = None

        # Save manager (database-backed)
        self.save_manager = DatabaseSaveManager()

        # Game ID for this session
        self.game_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Lab overrides (set externally by QuickPlaySession)
        self.model_override = None         # str: model ID
        self.temperature_override = None   # float: 0.0-1.5
        self.dice_roll_override = None     # int: 1-20
        
        # Ending narrative for stay-forever endings
        self._ending_narrative = ""
    
    # =========================================================================
    # GAME FLOW
    # =========================================================================
    
    def start_game(self) -> Generator[Dict, None, None]:
        """Initialize a new game, yield setup messages"""
        yield emit(MessageType.TITLE, {
            "title": "ANACHRON",
            "tagline": "How will you fare in another era?"
        })
        
        yield emit(MessageType.SETUP_NAME, {
            "prompt": "Enter your name:",
            "default": "Traveler"
        })
    
    def set_player_name(self, name: str) -> Generator[Dict, None, None]:
        """Set player name and move to region selection"""
        self.state.player_name = name if name.strip() else "Traveler"
        
        yield emit(MessageType.SETUP_REGION, {
            "prompt": "Where in history?",
            "options": [
                {
                    "id": "european",
                    "name": "European Focus",
                    "description": "Ancient Greece, Vikings, Medieval Europe, Colonial America, Industrial Britain, World Wars"
                },
                {
                    "id": "worldwide",
                    "name": "World Explorer", 
                    "description": "All eras: Egypt, China, Aztec Empire, Mughal India, plus European eras"
                }
            ]
        })
    
    def set_region(self, region: str) -> Generator[Dict, None, None]:
        """Set region preference and show intro"""
        self._selected_region = RegionPreference.EUROPEAN if region == "european" else RegionPreference.WORLDWIDE
        
        # Initialize game state
        self.state.start_game(self.state.player_name, GameMode.MATURE, self._selected_region)
        self.narrator = NarrativeEngine(self.state)
        self.current_game = self.history.start_new_game(self.state.player_name, self.user_id)
        
        # Intro story
        yield emit(MessageType.INTRO_STORY, {
            "paragraphs": [
                "Twenty-four. Stanford. Six figures. A life that looks perfect and feels like nothing.",
                "So when the lab needed a volunteer for the time machine's first human trial, you stepped up without thinking. Thirty seconds into the past. What could go wrong?",
                "Everything, it turns out.",
                "The machine is broken. You can't go home. All you have is what was in your pockets:"
            ]
        })
        
        # Show items
        items = []
        for item in self.state.inventory.modern_items:
            items.append({
                "id": item.id,
                "name": item.name,
                "description": item.description,
                "uses": item.uses,
                "utility": item.utility,
                "risk": item.risk
            })
        
        yield emit(MessageType.INTRO_ITEMS, {"items": items})
        
        # Device explanation
        yield emit(MessageType.INTRO_DEVICE, {
            "title": "THE DEVICE",
            "description": "The time machine is small—about the size of a chunky wristwatch. You wear it on your wrist, hidden under your sleeve.",
            "mechanics": [
                "The window to use the machine won't open immediately when you arrive somewhere new",
                "You'll have time to settle in first—typically most of a year",
                "When the window opens, you have a short time to decide",
                "Choose to activate it, or let the window close and stay"
            ],
            "catch": [
                "You can't choose where or when you go—it's random",
                "Your three items always come with you",
                "Your relationships do NOT come with you",
                "Each jump means starting over"
            ],
            "goal": "Find a time and place where you want to stay. Build something worth staying for—people, purpose, freedom. When the window opens and you choose not to leave... that's when you've found happiness."
        })
        
        yield emit(MessageType.WAITING_INPUT, {"action": "continue_to_era"})
    
    def enter_first_era(self) -> Generator[Dict, None, None]:
        """Enter the first random era"""
        yield from self._enter_random_era()
    
    # =========================================================================
    # SAVE/LOAD/RESUME
    # =========================================================================
    
    def save_game(self) -> Generator[Dict, None, None]:
        """Save current game state"""
        # Store conversation history in state
        if self.narrator:
            self.state.conversation_history = self.narrator.get_conversation_history()
        
        success = self.save_manager.save_game(self.user_id, self.game_id, self.state)
        
        yield emit(MessageType.GAME_SAVED, {
            "success": success,
            "game_id": self.game_id,
            "message": "Game saved successfully" if success else "Failed to save game"
        })
    
    def load_game(self, game_id: str) -> Generator[Dict, None, None]:
        """Load a saved game"""
        loaded_state = self.save_manager.load_game(self.user_id, game_id)
        
        if not loaded_state:
            yield emit(MessageType.ERROR, {
                "message": f"Could not load game {game_id}"
            })
            return
        
        self.state = loaded_state
        self.game_id = game_id
        
        # Restore current era reference
        if self.state.current_era:
            self.current_era = get_era_by_id(self.state.current_era.era_id)
        
        # Restore narrator with conversation history
        self.narrator = NarrativeEngine(self.state)
        if self.current_era:
            self.narrator.set_era(self.current_era)
            self.narrator.restore_conversation(self.state.conversation_history)
        
        yield emit(MessageType.GAME_LOADED, {
            "success": True,
            "game_id": game_id,
            "player_name": self.state.player_name,
            "phase": self.state.phase.value,
            "current_era": self.state.current_era.era_name if self.state.current_era else None
        })
    
    def resume_game(self) -> Generator[Dict, None, None]:
        """
        Resume a loaded game, providing full context for the player to pick up.
        Emits the last narrative and choices so the player can continue.
        """
        if self.state.phase == GamePhase.ENDED:
            yield emit(MessageType.ERROR, {
                "message": "This game has already ended"
            })
            return
        
        # Build resume context
        resume_data = {
            "player_name": self.state.player_name,
            "phase": self.state.phase.value,
            "total_turns": self.state.total_turns,
            "eras_visited": len(self.state.time_machine.eras_visited)
        }
        
        # Current era info
        if self.state.current_era and self.current_era:
            year = self.current_era['year']
            year_str = f"{abs(year)} BCE" if year < 0 else f"{year} CE"
            
            resume_data["era"] = {
                "name": self.current_era['name'],
                "year": year,
                "year_display": year_str,
                "location": self.current_era['location'],
                "time_in_era": self.state.current_era.time_in_era_description,
                "turns_in_era": self.state.current_era.turns_in_era + 1,
                "era_number": self.state.eras_count
            }
        
        # Device status
        resume_data["device"] = {
            "status": self.state.time_machine.indicator.value,
            "window_active": self.state.time_machine.window_active,
            "window_turns_remaining": self.state.time_machine.window_turns_remaining
        }
        
        # Can stay meaningfully
        resume_data["can_stay_meaningfully"] = self.state.can_stay_meaningfully
        
        yield emit(MessageType.GAME_RESUMED, resume_data)
        
        # Emit the last narrative if available
        if self.state.last_narrative:
            # Strip anchor tags before sending
            clean_narrative = strip_anchor_tags(self.state.last_narrative)
            yield emit(MessageType.NARRATIVE, {
                "text": clean_narrative,
                "is_resume": True
            })
        
        # Re-filter choices for safety (in case save is from old version)
        if self.state.last_choices:
            window_active = self.state.time_machine.window_active
            filtered_choices = filter_choices(
                self.state.last_choices,
                window_active,
                self.state.can_stay_meaningfully
            )
            self.state.last_choices = filtered_choices
            
            can_stay_forever = self.state.can_stay_meaningfully and window_active
            
            yield emit(MessageType.CHOICES, {
                "choices": filtered_choices,
                "can_quit": not can_stay_forever,
                "window_open": window_active,
                "can_stay_forever": can_stay_forever,
                "is_resume": True
            })
        
        # Emit device status
        yield self._get_device_status()
    
    def list_saved_games(self) -> Generator[Dict, None, None]:
        """List all saved games for current user"""
        games = self.save_manager.list_user_games(self.user_id)
        
        yield emit(MessageType.USER_GAMES, {
            "user_id": self.user_id,
            "games": games
        })
    
    def get_leaderboard(self, global_board: bool = True, limit: int = 10) -> Generator[Dict, None, None]:
        """Get leaderboard data"""
        leaderboard = Leaderboard(storage=DatabaseLeaderboardStorage())
        
        if global_board:
            scores = leaderboard.get_top_scores(limit)
        else:
            scores = leaderboard.get_user_scores(self.user_id, limit)
        
        yield emit(MessageType.LEADERBOARD, {
            "global": global_board,
            "user_id": self.user_id if not global_board else None,
            "scores": scores
        })
    
    def get_annals(self, user_only: bool = False, limit: int = 20, offset: int = 0) -> Generator[Dict, None, None]:
        """
        Get Annals of Anachron entries with pagination.
        
        Args:
            user_only: If True, only return entries for current user
            limit: Number of entries per page (max 20)
            offset: Pagination offset
        """
        annals = AnnalsOfAnachron()
        
        if user_only:
            result = annals.get_user_archive(self.user_id, limit=min(limit, 20), offset=offset)
        else:
            result = annals.get_public_feed(limit=min(limit, 20), offset=offset)
        
        # Convert entries to dicts for JSON serialization
        entries_data = []
        for entry in result['entries']:
            entries_data.append({
                "entry_id": entry.entry_id,
                "player_name": entry.player_name,
                "character_name": entry.character_name,
                "final_era": entry.final_era,
                "final_era_year": entry.final_era_year,
                "ending_type": entry.ending_type,
                "total_score": entry.total_score,
                "share_text": entry.get_share_text(),
                "created_at": entry.created_at
            })
        
        yield emit(MessageType.ANNALS, {
            "user_only": user_only,
            "user_id": self.user_id if user_only else None,
            "entries": entries_data,
            "total": result['total'],
            "limit": result['limit'],
            "offset": result['offset'],
            "has_more": result['has_more']
        })
    
    def get_annals_entry(self, entry_id: str) -> Generator[Dict, None, None]:
        """
        Get a single Annals entry by ID (for detail view / sharing).
        """
        annals = AnnalsOfAnachron()
        entry = annals.get_entry(entry_id)
        
        if not entry:
            yield emit(MessageType.ERROR, {
                "message": "Entry not found",
                "entry_id": entry_id
            })
            return
        
        yield emit(MessageType.ANNALS_ENTRY, {
            "entry_id": entry.entry_id,
            "player_name": entry.player_name,
            "character_name": entry.character_name,
            "final_era": entry.final_era,
            "final_era_year": entry.final_era_year,
            "eras_visited": entry.eras_visited,
            "turns_survived": entry.turns_survived,
            "ending_type": entry.ending_type,
            "belonging_score": entry.belonging_score,
            "legacy_score": entry.legacy_score,
            "freedom_score": entry.freedom_score,
            "total_score": entry.total_score,
            "key_npcs": entry.key_npcs,
            "defining_moments": entry.defining_moments,
            "wisdom_moments": entry.wisdom_moments,
            "items_used": entry.items_used,
            "player_narrative": entry.player_narrative,
            "historian_narrative": entry.historian_narrative,
            "share_text": entry.get_share_text(),
            "og_description": entry.get_og_description(),
            "created_at": entry.created_at
        })
    
    # =========================================================================
    # GAMEPLAY - CHOICE HANDLING
    # =========================================================================
    
    def make_choice(self, choice: str) -> Generator[Dict, None, None]:
        """
        Process a player choice (A, B, C, or Q).
        
        Uses intent-based resolution - the choice text determines what happens,
        not the position (A/B/C). This makes the system robust to AI generating
        choices in any order.
        """
        choice = choice.upper()
        
        # =====================================================================
        # DEBUG: Choice handling diagnosis
        # =====================================================================
        print("=" * 60)
        print("DEBUG make_choice() ENTRY")
        print("=" * 60)
        print(f"  choice input: {choice}")
        print(f"  window_active: {self.state.time_machine.window_active}")
        print(f"  window_turns_remaining: {self.state.time_machine.window_turns_remaining}")
        print(f"  current_era: {self.current_era['name'] if self.current_era else 'None'}")
        print(f"  phase: {self.state.phase.value}")
        print(f"  last_choices: {self.state.last_choices}")
        print("-" * 60)
        # =====================================================================
        
        # Handle quit
        if choice == 'Q':
            yield from self._handle_quit()
            return
        
        # Validate choice ID
        if choice not in ('A', 'B', 'C'):
            yield emit(MessageType.ERROR, {"message": f"Invalid choice: {choice}"})
            return
        
        # Get intent from the stored choice text
        window_open = self.state.time_machine.window_active
        intent, choice_text = get_choice_intent_for_submission(
            choice, 
            self.state.last_choices,
            window_open
        )
        
        # =====================================================================
        # DEBUG: Intent detection result
        # =====================================================================
        print(f"  window_open passed to intent: {window_open}")
        print(f"  detected intent: {intent}")
        print(f"  choice_text: {choice_text}")
        print("=" * 60)
        # =====================================================================
        
        if intent is None:
            yield emit(MessageType.ERROR, {"message": f"Choice {choice} not found"})
            return
        
        # Route based on intent
        if intent == ChoiceIntent.LEAVE_ERA:
            print("DEBUG: Routing to _handle_leaving()")
            yield from self._handle_leaving()
            return
        
        if intent == ChoiceIntent.STAY_FOREVER:
            print("DEBUG: Routing to _handle_stay_forever()")
            # Double-check eligibility (should always pass if filter worked)
            if not self.state.can_stay_meaningfully:
                yield emit(MessageType.ERROR, {
                    "message": "You haven't built enough to stay permanently."
                })
                yield from self._re_emit_choices()
                return
            yield from self._handle_stay_forever()
            return
        
        # Intent is CONTINUE_STORY - process as normal turn
        print("DEBUG: Routing to _process_story_turn()")
        yield from self._process_story_turn(choice)
    
    def _process_story_turn(self, choice: str) -> Generator[Dict, None, None]:
        """
        Process a normal story turn (not leave/stay-forever).
        
        This handles:
        - Rolling dice
        - Advancing the turn (which may open/close window)
        - Generating narrative
        - Processing response (anchors, items)
        - Filtering and emitting choices
        """
        # Roll dice for this turn (lab override if set)
        roll = self.dice_roll_override if self.dice_roll_override is not None else random.randint(1, 20)
        self.last_dice_roll = roll

        # Advance turn - this may open or close the window
        events = self.state.advance_turn()
        
        yield emit(MessageType.LOADING, {"message": "The story unfolds..."})
        
        # Determine which prompt to use based on what happened
        window_just_opened = events["window_opened"]
        window_active_after_turn = events["window_active_after_turn"]
        
        if window_just_opened:
            # Window just opened - use window prompt
            self.state.phase = GamePhase.WINDOW_OPEN
            
            yield emit(MessageType.WINDOW_OPEN, {
                "message": "THE WINDOW IS OPEN",
                "can_stay_meaningfully": self.state.can_stay_meaningfully,
                "stay_message": "You've built something here. You could stay forever..." if self.state.can_stay_meaningfully else None
            })
            
            prompt = get_window_prompt(self.state, choice, roll)
            history_prefix = "[The time machine window opens]\n"
        else:
            # Normal turn - use turn prompt
            prompt = get_turn_prompt(self.state, choice, roll, era=self.current_era)
            history_prefix = ""
        
        # Generate narrative
        response = ""
        generator = self.narrator.generate_streaming(
            prompt, model=self.model_override, temperature=self.temperature_override
        )
        try:
            while True:
                msg = next(generator)
                yield msg
        except StopIteration as e:
            response = e.value if e.value else ""

        # Fallback if response is empty
        if not response:
            response = self.narrator.messages[-1]["content"] if self.narrator.messages else ""

        # Record narrative
        if self.current_game:
            self.history.add_narrative(self.current_game, history_prefix + response)

        # Process response (anchors, items) - this may change can_stay_meaningfully
        feedback = self._process_response(response)

        # Emit milestone if a level threshold was crossed (progress feedback)
        if feedback.get("milestone"):
            yield emit(MessageType.PROGRESS_MILESTONE, feedback["milestone"])
        
        # Emit historical wisdom if player made a historically prudent choice
        if feedback.get("wisdom"):
            yield emit(MessageType.HISTORICAL_WISDOM, feedback["wisdom"])
        
        # Parse choices from AI response
        raw_choices = self._parse_choices(response)
        
        # Filter choices - remove stay_forever if not eligible
        # This is the safety layer in case AI generated invalid options
        filtered_choices = filter_choices(
            raw_choices,
            window_active_after_turn,
            self.state.can_stay_meaningfully
        )
        
        # Store filtered choices for next submission
        self.state.set_last_turn(response, filtered_choices)
        
        # Determine if quit should be available
        # Hide quit when stay_forever is an option (to avoid confusion)
        can_stay_forever = self.state.can_stay_meaningfully and window_active_after_turn
        can_quit = not can_stay_forever
        
        # Emit choices to frontend
        yield emit(MessageType.CHOICES, {
            "choices": filtered_choices,
            "can_quit": can_quit,
            "window_open": window_active_after_turn,
            "can_stay_forever": can_stay_forever
        })

        # Emit journey progress for frontend display
        yield emit(MessageType.JOURNEY_PROGRESS, self.state.fulfillment.get_progress_for_frontend())

        # Emit window status messages
        if not window_just_opened:
            if events["window_closing"]:
                yield emit(MessageType.WINDOW_CLOSING, {
                    "message": "The device pulses urgently. The window is closing..."
                })
            elif events["window_closed"]:
                yield emit(MessageType.WINDOW_CLOSED, {
                    "message": "The device falls silent. The moment has passed."
                })
                self.state.phase = GamePhase.LIVING
        
        # Emit device status
        yield self._get_device_status()
        
        # Auto-save after each turn
        if self.narrator:
            self.state.conversation_history = self.narrator.get_conversation_history()
        self.save_manager.save_game(self.user_id, self.game_id, self.state)
    
    def _re_emit_choices(self) -> Generator[Dict, None, None]:
        """Re-emit the current choices after an error."""
        window_open = self.state.time_machine.window_active
        can_stay_forever = self.state.can_stay_meaningfully and window_open
        
        yield emit(MessageType.CHOICES, {
            "choices": self.state.last_choices,
            "can_quit": not can_stay_forever,
            "window_open": window_open,
            "can_stay_forever": can_stay_forever
        })
    
    def get_current_state(self) -> Dict:
        """Get the current game state for frontend rendering"""
        return {
            "game_id": self.game_id,
            "user_id": self.user_id,
            "phase": self.state.phase.value,
            "player_name": self.state.player_name,
            "era": {
                "name": self.current_era["name"] if self.current_era else None,
                "year": self.current_era["year"] if self.current_era else None,
                "location": self.current_era["location"] if self.current_era else None,
                "time_in_era": self.state.current_era.time_in_era_description if self.state.current_era else None
            } if self.current_era else None,
            "device": {
                "indicator": self.state.time_machine.indicator.value,
                "window_active": self.state.time_machine.window_active,
                "window_turns_remaining": self.state.time_machine.window_turns_remaining
            },
            "can_stay_meaningfully": self.state.can_stay_meaningfully,
            "total_turns": self.state.total_turns,
            "eras_visited": len(self.state.time_machine.eras_visited),
            # NEW: Progress feedback for frontend display
            "progress": self.state.fulfillment.get_progress_for_frontend()
        }
    
    # =========================================================================
    # INTERNAL HELPERS
    # =========================================================================
    
    def _enter_random_era(self) -> Generator[Dict, None, None]:
        """Enter a random era"""
        visited_ids = self.state.time_machine.eras_visited
        
        # Debug override: force specific era if DEBUG_MODE=true and DEBUG_ERA is set
        debug_era_id = get_debug_era_id()
        if debug_era_id:
            debug_era = get_era_by_id(debug_era_id)
            if debug_era:
                print(f"[DEBUG] Forcing era: {debug_era_id}")
                self.current_era = debug_era
            else:
                # Fallback to random if debug era not found
                if self.state.region_preference == RegionPreference.EUROPEAN:
                    available_eras = [e for e in ERAS if e['id'] in EUROPEAN_ERA_IDS]
                else:
                    available_eras = ERAS
                self.current_era = select_random_era(available_eras, visited_ids)
        else:
            # Normal random era selection
            if self.state.region_preference == RegionPreference.EUROPEAN:
                available_eras = [e for e in ERAS if e['id'] in EUROPEAN_ERA_IDS]
            else:
                available_eras = ERAS
            
            self.current_era = select_random_era(available_eras, visited_ids)
        self.state.enter_era(self.current_era)
        
        # Initialize milestone tracking for the new era (new - progress feedback)
        self.state.fulfillment.initialize_milestone_tracking()
        
        # Update time machine display
        self.state.time_machine.update_display(
            year=self.current_era['year'],
            location=self.current_era['location'],
            era_name=self.current_era['name']
        )
        
        # Reset inventory revealed status
        self.state.inventory.reset_for_new_era()
        
        # Set up narrator for this era
        self.narrator.set_era(self.current_era)
        
        # Record era in history
        if self.current_game:
            self.history.start_era(
                self.current_game,
                self.current_era['name'],
                self.current_era['year'],
                self.current_era['location']
            )
        
        # Emit era arrival
        year = self.current_era['year']
        year_str = f"{abs(year)} BCE" if year < 0 else f"{year} CE"
        
        yield emit(MessageType.ERA_ARRIVAL, {
            "era_name": self.current_era['name'],
            "year": year,
            "year_display": year_str,
            "location": self.current_era['location'],
            "device_display": self.state.time_machine.display.get_display_text(),
            "era_number": self.state.eras_count,
            "turn_in_era": (self.state.current_era.turns_in_era + 1) if self.state.current_era else 1,
            "time_in_era": self.state.current_era.time_in_era_description if self.state.current_era else "just arrived"
        })

        # Emit journey progress for frontend display
        yield emit(MessageType.JOURNEY_PROGRESS, self.state.fulfillment.get_progress_for_frontend())
        
        # Era summary for every era arrival
        yield emit(MessageType.ERA_SUMMARY, {
            "location": self.current_era['location'],
            "year_display": year_str,
            "key_events": self.current_era.get('key_events', [])[:5]
        })
        
        yield emit(MessageType.LOADING, {"message": "Arriving..."})
        
        # Generate arrival narrative
        prompt = get_arrival_prompt(self.state, self.current_era)
        response = ""

        # Stream the narrative - capture full response from generator
        generator = self.narrator.generate_streaming(
            prompt, model=self.model_override, temperature=self.temperature_override
        )
        try:
            while True:
                msg = next(generator)
                yield msg
        except StopIteration as e:
            response = e.value if e.value else ""
        
        if not response:
            response = self.narrator.messages[-1]["content"] if self.narrator.messages else ""
        
        # Record narrative
        if self.current_game:
            self.history.add_narrative(self.current_game, response)
        
        # Process response (with is_arrival=True to capture character name)
        feedback = self._process_response(response, is_arrival=True)
        
        # Emit milestone if a level threshold was crossed (progress feedback)
        if feedback.get("milestone"):
            yield emit(MessageType.PROGRESS_MILESTONE, feedback["milestone"])
        
        # Emit historical wisdom if player made a historically prudent choice
        if feedback.get("wisdom"):
            yield emit(MessageType.HISTORICAL_WISDOM, feedback["wisdom"])
        
        # Log era arrival event
        self.state.log_event(
            "era_arrival",
            era_id=self.current_era['id'],
            era_name=self.current_era['name']
        )
        
        # Parse choices and filter (window is always closed on arrival)
        raw_choices = self._parse_choices(response)
        filtered_choices = filter_choices(
            raw_choices,
            window_open=False,
            can_stay_meaningfully=self.state.can_stay_meaningfully
        )
        
        # Store for session resume
        self.state.set_last_turn(response, filtered_choices)
        
        yield emit(MessageType.CHOICES, {
            "choices": filtered_choices,
            "can_quit": True
        })
        
        # Set phase
        self.state.phase = GamePhase.LIVING
        
        # Emit device status
        yield self._get_device_status()
        
        # Auto-save
        if self.narrator:
            self.state.conversation_history = self.narrator.get_conversation_history()
        self.save_manager.save_game(self.user_id, self.game_id, self.state)
    
    def _handle_leaving(self) -> Generator[Dict, None, None]:
        """Handle player choosing to leave"""
        self.state.choose_to_travel()
        
        yield emit(MessageType.DEPARTURE, {
            "title": "DEPARTURE",
            "message": "You activate the time machine..."
        })
        
        yield emit(MessageType.LOADING, {"message": "Reality shifts..."})
        
        # Generate departure narrative (premium model — leaving is emotionally weighted)
        prompt = get_leaving_prompt(self.state)
        response = ""

        # Stream the narrative - capture full response from generator
        generator = self.narrator.generate_streaming(prompt, model=PREMIUM_MODEL)
        try:
            while True:
                msg = next(generator)
                yield msg
        except StopIteration as e:
            response = e.value if e.value else ""
        
        if not response:
            response = self.narrator.messages[-1]["content"] if self.narrator.messages else ""
        
        # Record departure
        if self.current_game:
            self.history.add_narrative(self.current_game, "[You activate the time machine]\n" + response)
        
        yield emit(MessageType.WAITING_INPUT, {"action": "continue_to_next_era"})
    
    def continue_to_next_era(self) -> Generator[Dict, None, None]:
        """Continue to the next era after departure"""
        yield from self._enter_random_era()
    
    def _handle_stay_forever(self) -> Generator[Dict, None, None]:
        """Handle player choosing to stay forever"""
        # =====================================================================
        # DEBUG: Verify data flow to ending prompt
        # =====================================================================
        print("=" * 60)
        print("DEBUG: ENDING DATA FLOW CHECK")
        print("=" * 60)
        
        # 1. Anchor values (should be non-zero after real gameplay)
        print(f"Belonging: {self.state.fulfillment.belonging.value}")
        print(f"Legacy: {self.state.fulfillment.legacy.value}")
        print(f"Freedom: {self.state.fulfillment.freedom.value}")
        print(f"Ending type: {self.state.fulfillment.get_ending_type()}")
        print("-" * 40)
        
        # 2. Event log (should have entries)
        print(f"Total events logged: {len(self.state.game_events)}")
        print(f"Event types: {set(e['type'] for e in self.state.game_events)}")
        print("-" * 40)
        
        # 3. Key NPCs (should have names if <key_npc> tags were parsed)
        relationship_events = self.state.get_events_by_type("relationship")
        print(f"Relationship events: {len(relationship_events)}")
        npc_names = [e.get('name') for e in relationship_events[:5]]
        print(f"NPC names: {npc_names}")
        print("-" * 40)
        
        # 4. Wisdom moments (should have IDs if <wisdom> tags were parsed)
        wisdom_events = self.state.get_events_by_type("wisdom")
        print(f"Wisdom events: {len(wisdom_events)}")
        wisdom_ids = [e.get('id') for e in wisdom_events[:5]]
        print(f"Wisdom IDs: {wisdom_ids}")
        print("-" * 40)
        
        # 5. Character name (should be set from arrival)
        char_name = self.state.current_era.character_name if self.state.current_era else 'NO ERA'
        print(f"Character name: {char_name}")
        print("-" * 40)
        
        # 6. Era info
        if self.current_era:
            print(f"Current era: {self.current_era.get('name', 'Unknown')}")
            print(f"Time in era: {self.state.current_era.time_in_era_description if self.state.current_era else 'Unknown'}")
            print(f"Turns in era: {self.state.current_era.turns_in_era if self.state.current_era else 0}")
        print("-" * 40)
        
        # 7. Era history (for "previous lives" context in prompt)
        print(f"Era history count: {len(self.state.era_history)}")
        for h in self.state.era_history[-3:]:
            print(f"  - {h['era_name']}: {h.get('character_name', 'unnamed')}, {h['turns']} turns")
        print("-" * 40)
        
        # 8. Conversation history (verify AI has full context)
        print(f"Conversation messages: {len(self.narrator.messages) if self.narrator else 0}")
        print("-" * 40)
        
        # 9. Ripple conditions (special content when belonging/legacy >= 40)
        belonging_val = self.state.fulfillment.belonging.value
        legacy_val = self.state.fulfillment.legacy.value
        print(f"Ripple enabled: {belonging_val >= 40 or legacy_val >= 40}")
        print("=" * 60)
        # END DEBUG
        
        yield emit(MessageType.STAYING_FOREVER, {
            "title": "A NEW HOME",
            "messages": [
                "You reach for the device on your wrist...",
                "And then you stop.",
                "This is your home now."
            ]
        })
        
        yield emit(MessageType.LOADING, {"message": "Your story concludes..."})
        
        # Generate ending narrative (premium model for quality)
        prompt = get_staying_ending_prompt(self.state, self.current_era)
        response = ""

        # Stream the narrative - capture full response from generator
        generator = self.narrator.generate_streaming(prompt, model=PREMIUM_MODEL)
        try:
            while True:
                msg = next(generator)
                yield msg
        except StopIteration as e:
            response = e.value if e.value else ""
        
        if not response:
            response = self.narrator.messages[-1]["content"] if self.narrator.messages else ""
        
        # Record ending
        if self.current_game:
            self.history.add_narrative(self.current_game, "[You choose to stay forever]\n" + response)
        
        # Store the ending narrative for the score
        self._ending_narrative = response
        
        # End the game
        self.state.choose_to_stay(is_final=True)
        self.state.end_game()
        
        # Wait for user to click continue before showing score
        yield emit(MessageType.WAITING_INPUT, {"action": "continue_to_score"})
    
    def continue_to_score(self) -> Generator[Dict, None, None]:
        """Continue to show the final score after the narrative"""
        # Calculate and emit score, passing the stored ending narrative
        ending_narrative = getattr(self, '_ending_narrative', '')
        yield from self._emit_final_score(ending_narrative=ending_narrative)
        
        # Delete save file (game is complete)
        self.save_manager.delete_game(self.user_id, self.game_id)
    
    def _handle_quit(self) -> Generator[Dict, None, None]:
        """Handle player choosing to quit"""
        yield emit(MessageType.GAME_END, {
            "title": "YOUR JOURNEY ENDS",
            "messages": [
                "You set down the device.",
                "Some journeys end before the destination is found."
            ]
        })
        
        # Generate quit narrative with historical context
        if self.current_era and self.narrator:
            yield emit(MessageType.LOADING, {"message": "Preparing your debrief..."})
            
            prompt = get_quit_ending_prompt(self.state, self.current_era)
            response = ""

            # Stream the narrative (premium model for quality)
            generator = self.narrator.generate_streaming(prompt, model=PREMIUM_MODEL)
            try:
                while True:
                    msg = next(generator)
                    yield msg
            except StopIteration as e:
                response = e.value if e.value else ""
            
            if not response:
                response = self.narrator.messages[-1]["content"] if self.narrator.messages else ""
            
            # Store ending narrative (raw - tags stripped before display)
            self._ending_narrative = response
            
            # Record in history
            if self.current_game:
                self.history.add_narrative(self.current_game, "[Journey abandoned]\n" + response)
        else:
            self._ending_narrative = ""
            if self.current_game:
                self.history.add_narrative(self.current_game, "[Journey abandoned]")
        
        # End the game
        self.state.end_game()
        
        # Calculate and emit score
        ending_narrative = getattr(self, '_ending_narrative', '')
        yield from self._emit_final_score(ending_type_override="abandoned", ending_narrative=ending_narrative)
        
        # Delete save file (game is complete)
        self.save_manager.delete_game(self.user_id, self.game_id)
    
    def _emit_final_score(self, ending_type_override: str = None, ending_narrative: str = "") -> Generator[Dict, None, None]:
        """Calculate and emit final score, and create Annals of Anachron entry if qualified"""
        score = calculate_score(
            self.state, 
            ending_type_override=ending_type_override,
            user_id=self.user_id,
            game_id=self.game_id,
            ending_narrative=ending_narrative
        )
        
        # Save to history
        if self.current_game:
            self.history.end_game(self.current_game, score)
        
        # Add to leaderboard (database-backed)
        leaderboard = Leaderboard(storage=DatabaseLeaderboardStorage())
        rank = leaderboard.add_score(score)
        
        # Create Annals of Anachron entry if qualified
        aoa_entry = None
        aoa_data = None
        annals = AnnalsOfAnachron()
        
        # =====================================================================
        # DEBUG: AoA Entry Creation Check
        # =====================================================================
        print("=" * 60)
        print("DEBUG: AOA ENTRY DATA CHECK")
        print("=" * 60)
        
        # 1. Score data that feeds into AoA
        print(f"Score - turns_survived: {score.turns_survived}")
        print(f"Score - eras_visited: {score.eras_visited}")
        print(f"Score - ending_type: {score.ending_type}")
        print(f"Score - total: {score.total}")
        print(f"Score - fulfillment: {score.belonging_score + score.legacy_score + score.freedom_score}")
        print(f"Score - ending_narrative length: {len(score.ending_narrative) if score.ending_narrative else 0}")
        print("-" * 40)
        
        # 2. Qualification check (thresholds)
        from scoring import AOA_THRESHOLDS
        total_fulfillment = score.belonging_score + score.legacy_score + score.freedom_score
        print(f"Qualification thresholds:")
        print(f"  min_turns: {AOA_THRESHOLDS['min_turns']} (have: {score.turns_survived})")
        print(f"  min_eras: {AOA_THRESHOLDS['min_eras']} (have: {score.eras_visited})")
        print(f"  min_fulfillment: {AOA_THRESHOLDS['min_fulfillment']} (have: {total_fulfillment})")
        print(f"  excluded_endings: {AOA_THRESHOLDS['excluded_endings']} (have: {score.ending_type})")
        print("-" * 40)
        
        # 3. Character name from current era
        char_name = self.state.current_era.character_name if self.state.current_era else 'NO ERA'
        era_year = self.state.current_era.era_year if self.state.current_era else 0
        print(f"Character name: {char_name}")
        print(f"Era year: {era_year}")
        print("-" * 40)
        
        # 4. Key events for AoA
        relationship_events = self.state.get_events_by_type("relationship")
        wisdom_events = self.state.get_events_by_type("wisdom")
        item_events = self.state.get_events_by_type("item_use")
        defining_events = self.state.get_events_by_type("defining_moment")
        print(f"Relationship events: {len(relationship_events)}")
        print(f"Wisdom events: {len(wisdom_events)}")
        print(f"Item use events: {len(item_events)}")
        print(f"Defining moment events: {len(defining_events)}")
        print("=" * 60)
        # END DEBUG
        
        is_stay_ending = ending_type_override is None and score.ending_type != "abandoned"
        portrait_path = None

        try:
            aoa_entry = annals.create_entry(self.state, score)

            if aoa_entry:
                # Generate historian narrative using AI
                historian_prompt = get_historian_narrative_prompt(aoa_entry)
                historian_narrative = self.narrator.generate(historian_prompt)
                aoa_entry.historian_narrative = historian_narrative

                # Save to annals
                annals.save_entry(aoa_entry)

                # Generate portrait via AoA entry
                if score.total >= 300 and is_stay_ending:
                    try:
                        yield emit(MessageType.LOADING, {"text": "Creating your portrait..."})
                        import portrait_generator
                        portrait_path = portrait_generator.generate_portrait(aoa_entry.entry_id)
                        if portrait_path:
                            logger.info(f"Portrait generated: {portrait_path}")
                    except Exception as pe:
                        logger.error(f"Portrait generation failed: {pe}")

                # Prepare AoA data for response
                aoa_data = {
                    "entry_id": aoa_entry.entry_id,
                    "qualified": True,
                    "share_text": aoa_entry.get_share_text(),
                    "historian_narrative": aoa_entry.historian_narrative,
                    "character_name": aoa_entry.character_name,
                    "final_era": aoa_entry.final_era,
                    "final_era_year": aoa_entry.final_era_year,
                    "portrait_image_path": portrait_path,
                }
            else:
                # No AoA entry, but still generate portrait if qualifying
                if score.total >= 300 and is_stay_ending:
                    try:
                        yield emit(MessageType.LOADING, {"text": "Creating your portrait..."})
                        import portrait_generator
                        game_id = self.state.game_id if hasattr(self.state, 'game_id') else 'unknown'
                        image_id = f"portrait_{game_id}"
                        # Build minimal data dict for scene extraction
                        char_name = self.state.current_era.character_name if self.state.current_era else 'The Traveler'
                        era_name = self.state.current_era.era_name if self.state.current_era else 'Unknown'
                        era_year = self.state.current_era.era_year if self.state.current_era else 0
                        portrait_data = {
                            'final_era': era_name,
                            'final_era_year': era_year,
                            'character_name': char_name,
                            'ending_type': score.ending_type,
                            'belonging_score': score.belonging_score,
                            'legacy_score': score.legacy_score,
                            'freedom_score': score.freedom_score,
                            'key_npcs': [e.get('npc_name', '') for e in self.state.get_events_by_type('relationship')],
                            'items_used': [e.get('item_name', '') for e in self.state.get_events_by_type('item_use')],
                            'player_narrative': score.ending_narrative or '',
                            'historian_narrative': '',
                        }
                        portrait_path = portrait_generator.generate_portrait_from_data(portrait_data, image_id)
                        if portrait_path:
                            logger.info(f"Portrait generated (no AoA): {portrait_path}")
                            # Store path in leaderboard for display
                            try:
                                from db import get_db
                                with get_db() as conn:
                                    with conn.cursor() as cur:
                                        cur.execute(
                                            "UPDATE leaderboard_entries SET portrait_image_path = %s WHERE game_id = %s",
                                            (portrait_path, game_id)
                                        )
                            except Exception:
                                pass
                    except Exception as pe:
                        logger.error(f"Portrait generation (no AoA) failed: {pe}")

                aoa_data = {
                    "qualified": False,
                    "portrait_image_path": portrait_path,
                }
        except Exception as e:
            # Don't fail the whole score display if AoA fails
            aoa_data = {
                "qualified": False,
                "reason": "Error creating entry"
            }
        
        # Build response data
        response_data = {
            "total": score.total,
            "rank": rank,
            "breakdown": {
                "survival": {
                    "turns": score.turns_survived,
                    "points": score.survival_points
                },
                "exploration": {
                    "eras": score.eras_visited,
                    "points": score.exploration_points
                },
                "fulfillment": {
                    "belonging": score.belonging_score,
                    "legacy": score.legacy_score,
                    "freedom": score.freedom_score,
                    "total": score.fulfillment_points
                },
                "ending": {
                    "type": score.ending_type,
                    "bonus": score.ending_bonus
                }
            },
            "summary": score.get_narrative_summary(),
            "blurb": score.get_blurb(),
            "final_era": score.final_era,
            "ending_narrative": strip_anchor_tags(strip_event_tags(score.ending_narrative)) if score.ending_narrative else None
        }
        
        # Add AoA data if available
        if aoa_data:
            response_data["annals"] = aoa_data
        
        yield emit(MessageType.FINAL_SCORE, response_data)
    
    def _get_device_status(self) -> Dict:
        """Get device status message"""
        indicator = self.state.time_machine.indicator
        
        status_map = {
            IndicatorState.DARK: {"status": "silent", "description": "The device is silent and cold."},
            IndicatorState.FAINT_PULSE: {"status": "faint_pulse", "description": "A faint pulse stirs in the device."},
            IndicatorState.STEADY_GLOW: {"status": "steady_glow", "description": "The device glows steadily."},
            IndicatorState.BRIGHT_PULSE: {"status": "window_open", "description": "The device pulses urgently. The window is open."}
        }
        
        status_data = status_map.get(indicator, status_map[IndicatorState.DARK])
        status_data["window_active"] = self.state.time_machine.window_active
        status_data["window_turns_remaining"] = self.state.time_machine.window_turns_remaining
        
        if self.state.current_era:
            status_data["era_number"] = self.state.eras_count
            status_data["turn_in_era"] = self.state.current_era.turns_in_era + 1
            status_data["time_in_era"] = self.state.current_era.time_in_era_description
        
        return emit(MessageType.DEVICE_STATUS, status_data)
    
    def _process_response(self, response: str, is_arrival: bool = False) -> Dict:
        """
        Process AI response - extract anchors, items, and log events.
        
        Returns:
            Dict with optional 'milestone' and 'wisdom' keys for caller to emit.
            This is additive - callers that ignore the return value continue to work.
        """
        result = {"milestone": None, "wisdom": None}
        
        # Parse anchor adjustments
        adjustments = parse_anchor_adjustments(response)
        for anchor, delta in adjustments.items():
            if delta != 0:
                self.state.fulfillment.adjust(anchor, delta, "choice")
        
        # Check for defining moment (large anchor shift)
        defining = check_defining_moment(adjustments)
        if defining:
            anchor_name, delta = defining
            self.state.log_event(
                "defining_moment",
                anchor=anchor_name,
                delta=delta
            )
        
        # NEW: Check for milestone crossing (level-up)
        result["milestone"] = self.state.fulfillment.check_milestone_crossed()
        
        # Parse item usage
        used_items = parse_item_usage(response, self.state.inventory)
        for item_id in used_items:
            self.state.inventory.use_item(item_id)
            self.state.log_event("item_use", item_id=item_id)
        
        # Parse character name (primarily on arrival)
        if is_arrival:
            char_name = parse_character_name(response)
            if char_name:
                if self.state.current_era:
                    self.state.current_era.character_name = char_name
                self.state.log_event("character_named", name=char_name)
        
        # Parse key NPCs
        npcs = parse_key_npcs(response)
        for npc_name in npcs:
            self.state.log_event("relationship", name=npc_name)
        
        # Parse wisdom moments and look up full data
        wisdom_id = parse_wisdom_moment(response)
        if wisdom_id:
            self.state.log_event("wisdom", id=wisdom_id)
            # Look up full wisdom data from current era
            if self.current_era:
                wisdom_data = get_wisdom_path_by_id(self.current_era, wisdom_id)
                if wisdom_data:
                    result["wisdom"] = wisdom_data
        
        # Store turn event in era state
        if self.state.current_era:
            self.state.current_era.events.append(f"Turn {self.state.current_era.turns_in_era}")
        
        # Return feedback data for caller to optionally emit
        return result
    
    def _parse_choices(self, response: str) -> List[Dict]:
        """Extract choices from response"""
        # Strip both anchor tags and event tags
        clean_response = strip_anchor_tags(response)
        clean_response = strip_event_tags(clean_response)
        # Strip markdown bold markers so **[A]** still matches
        clean_response = re.sub(r'\*\*', '', clean_response)

        choices = []
        for line in clean_response.split('\n'):
            line = line.strip()
            match = re.match(r'^\[([A-C])\]\s*(.+)$', line, re.IGNORECASE)
            if match:
                choice_text = match.group(2).strip()
                choice_text = re.sub(r'\s*<[^>]+>.*$', '', choice_text)
                choice_text = re.sub(r'\s*SCORES:.*$', '', choice_text, flags=re.IGNORECASE)
                if choice_text and len(choice_text) > 3:
                    choices.append({
                        'id': match.group(1).upper(),
                        'text': choice_text
                    })
        
        return choices[:3]


# =============================================================================
# SIMPLE SYNCHRONOUS WRAPPER (for simpler integrations)
# =============================================================================

class GameSession:
    """
    Simplified wrapper that collects generator output into lists.
    Useful for request/response style APIs (e.g., REST endpoints).
    """
    
    def __init__(self, user_id: str = "default"):
        self.api = GameAPI(user_id=user_id)
    
    def start(self) -> List[Dict]:
        """Start game, return all setup messages"""
        return list(self.api.start_game())
    
    def set_name(self, name: str) -> List[Dict]:
        """Set player name"""
        return list(self.api.set_player_name(name))
    
    def set_region(self, region: str) -> List[Dict]:
        """Set region preference"""
        return list(self.api.set_region(region))
    
    def enter_first_era(self) -> List[Dict]:
        """Enter first era"""
        return list(self.api.enter_first_era())
    
    def choose(self, choice: str) -> List[Dict]:
        """Make a choice"""
        return list(self.api.make_choice(choice))
    
    def continue_to_next_era(self) -> List[Dict]:
        """Continue after departure"""
        return list(self.api.continue_to_next_era())
    
    def continue_to_score(self) -> List[Dict]:
        """Continue to show final score after ending narrative"""
        return list(self.api.continue_to_score())
    
    def get_state(self) -> Dict:
        """Get current state"""
        return self.api.get_current_state()
    
    def save(self) -> List[Dict]:
        """Save current game"""
        return list(self.api.save_game())
    
    def load(self, game_id: str) -> List[Dict]:
        """Load a saved game"""
        return list(self.api.load_game(game_id))
    
    def resume(self) -> List[Dict]:
        """Resume loaded game with full context"""
        return list(self.api.resume_game())
    
    def list_saves(self) -> List[Dict]:
        """List saved games"""
        return list(self.api.list_saved_games())
    
    def leaderboard(self, global_board: bool = True) -> List[Dict]:
        """Get leaderboard"""
        return list(self.api.get_leaderboard(global_board))
    
    def annals(self, user_only: bool = False, limit: int = 20, offset: int = 0) -> List[Dict]:
        """Get Annals of Anachron entries"""
        return list(self.api.get_annals(user_only, limit, offset))
    
    def annals_entry(self, entry_id: str) -> List[Dict]:
        """Get a single Annals entry"""
        return list(self.api.get_annals_entry(entry_id))
