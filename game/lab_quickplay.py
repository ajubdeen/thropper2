"""
Narrative Lab - Quick Play

Wraps GameAPI for REST-based play sessions with auto-snapshotting.
Sessions are in-memory (ephemeral); snapshots persist in DB.
"""

import uuid
import logging
from typing import Dict, Any, List, Optional

from game_api import GameAPI
from fulfillment import strip_anchor_tags
from event_parsing import strip_event_tags
import lab_service
import prompt_overrides

logger = logging.getLogger(__name__)

# In-memory session store (cleared on server restart)
_sessions: Dict[str, 'QuickPlaySession'] = {}


class QuickPlaySession:
    """Wraps GameAPI for REST-based quick play with auto-snapshotting."""

    def __init__(self, session_id: str, user_id: str, player_name: str = "Lab Tester",
                 region: str = "european",
                 system_prompt_override: str = None,
                 turn_prompt_override: str = None,
                 arrival_prompt_override: str = None,
                 window_prompt_override: str = None,
                 model_override: str = None,
                 temperature: float = None,
                 dice_roll: int = None):
        self.session_id = session_id
        self.user_id = user_id
        self.api = GameAPI(user_id=user_id)
        self.turn_count = 0
        self.snapshot_ids: List[str] = []
        self.system_prompt_override = system_prompt_override
        self.turn_prompt_override = turn_prompt_override
        self.arrival_prompt_override = arrival_prompt_override
        self.window_prompt_override = window_prompt_override
        self.model_override = model_override
        self.temperature = temperature
        self.dice_roll = dice_roll

        # Run through setup synchronously
        list(self.api.start_game())
        list(self.api.set_player_name(player_name))
        list(self.api.set_region(region))

    def update_params(self,
                      system_prompt_override=None,
                      turn_prompt_override=None,
                      arrival_prompt_override=None,
                      window_prompt_override=None,
                      model_override=None,
                      temperature=None,
                      dice_roll=None):
        """Update session parameters between turns. Only updates non-None values."""
        if system_prompt_override is not None:
            self.system_prompt_override = system_prompt_override or None
        if turn_prompt_override is not None:
            self.turn_prompt_override = turn_prompt_override or None
        if arrival_prompt_override is not None:
            self.arrival_prompt_override = arrival_prompt_override or None
        if window_prompt_override is not None:
            self.window_prompt_override = window_prompt_override or None
        if model_override is not None:
            self.model_override = model_override or None
        if temperature is not None:
            self.temperature = temperature if temperature != -1 else None
        if dice_roll is not None:
            self.dice_roll = dice_roll if dice_roll != -1 else None

    def _apply_api_overrides(self):
        """Push model/temperature/dice_roll overrides to the GameAPI instance."""
        self.api.model_override = self.model_override
        self.api.temperature_override = self.temperature
        self.api.dice_roll_override = self.dice_roll

    def _apply_system_override(self):
        """Apply system prompt override to the narrator if set.
        Renders the template with current game state variables first."""
        if self.system_prompt_override and self.api.narrator:
            from prompts import _get_system_variables
            era = self.api.current_era
            if era:
                variables = _get_system_variables(self.api.state, era)
                self.api.narrator.system_prompt = self.system_prompt_override.format(**variables)
            else:
                self.api.narrator.system_prompt = self.system_prompt_override

    def _push_turn_override(self):
        """Temporarily push turn template override into the cache."""
        if self.turn_prompt_override:
            prompt_overrides._active_overrides["turn"] = self.turn_prompt_override

    def _pop_turn_override(self):
        """Revert turn template override from the cache."""
        if self.turn_prompt_override:
            prompt_overrides._active_overrides.pop("turn", None)

    def _push_arrival_override(self):
        """Temporarily push arrival template override into the cache."""
        if self.arrival_prompt_override:
            prompt_overrides._active_overrides["arrival"] = self.arrival_prompt_override

    def _pop_arrival_override(self):
        """Revert arrival template override from the cache."""
        if self.arrival_prompt_override:
            prompt_overrides._active_overrides.pop("arrival", None)

    def _push_window_override(self):
        """Temporarily push window template override into the cache."""
        if self.window_prompt_override:
            prompt_overrides._active_overrides["window"] = self.window_prompt_override

    def _pop_window_override(self):
        """Revert window template override from the cache."""
        if self.window_prompt_override:
            prompt_overrides._active_overrides.pop("window", None)

    def enter_era(self) -> Dict[str, Any]:
        """Enter the first/next era. Returns messages and auto-snapshot."""
        self._apply_api_overrides()
        self._push_arrival_override()
        try:
            messages = list(self.api.enter_first_era())
        finally:
            self._pop_arrival_override()
        self._apply_system_override()
        snapshot_id = self._auto_snapshot("arrival")
        return {
            'messages': messages,
            'snapshot_id': snapshot_id,
            'state': self.api.get_current_state(),
        }

    def choose(self, choice: str) -> Dict[str, Any]:
        """Make a choice. Returns messages and auto-snapshot."""
        self.turn_count += 1
        self._apply_api_overrides()
        self._apply_system_override()
        self._push_turn_override()
        self._push_window_override()
        try:
            messages = list(self.api.make_choice(choice))
        finally:
            self._pop_turn_override()
            self._pop_window_override()
        snapshot_id = self._auto_snapshot(f"turn-{self.turn_count}")
        return {
            'messages': messages,
            'snapshot_id': snapshot_id,
            'state': self.api.get_current_state(),
        }

    def continue_to_next_era(self) -> Dict[str, Any]:
        """Continue after departure."""
        self._apply_api_overrides()
        self._push_arrival_override()
        try:
            messages = list(self.api.continue_to_next_era())
        finally:
            self._pop_arrival_override()
        self._apply_system_override()
        snapshot_id = self._auto_snapshot("new-era")
        return {
            'messages': messages,
            'snapshot_id': snapshot_id,
            'state': self.api.get_current_state(),
        }

    def get_state(self) -> Dict[str, Any]:
        """Get current game state."""
        return self.api.get_current_state()

    def _auto_snapshot(self, label_suffix: str) -> Optional[str]:
        """Create a snapshot of the current state."""
        try:
            state = self.api.state
            narrator = self.api.narrator

            state_dict = state.to_save_dict()
            conversation_history = narrator.get_conversation_history() if narrator else []
            system_prompt = narrator.system_prompt if narrator else None

            snapshot = lab_service.create_snapshot_from_state(
                user_id=self.user_id,
                label=f"Quick Play \u2014 {label_suffix}",
                tags=['quick_play', self.session_id],
                game_state_dict=state_dict,
                conversation_history=conversation_history,
                system_prompt=system_prompt,
                available_choices=state.last_choices,
                source='quick_play',
            )
            snapshot_id = snapshot.get('id')
            if snapshot_id:
                self.snapshot_ids.append(snapshot_id)
            return snapshot_id
        except Exception as e:
            logger.error(f"Auto-snapshot failed: {e}")
            return None


def create_session(user_id: str, player_name: str = "Lab Tester",
                   region: str = "european",
                   system_prompt_override: str = None,
                   turn_prompt_override: str = None,
                   arrival_prompt_override: str = None,
                   window_prompt_override: str = None,
                   model_override: str = None,
                   temperature: float = None,
                   dice_roll: int = None) -> Dict[str, Any]:
    """Create a new quick play session."""
    session_id = str(uuid.uuid4())
    session = QuickPlaySession(
        session_id, user_id, player_name, region,
        system_prompt_override=system_prompt_override,
        turn_prompt_override=turn_prompt_override,
        arrival_prompt_override=arrival_prompt_override,
        window_prompt_override=window_prompt_override,
        model_override=model_override,
        temperature=temperature,
        dice_roll=dice_roll,
    )
    _sessions[session_id] = session
    return {
        'session_id': session_id,
        'state': session.get_state(),
    }


def get_session(session_id: str) -> Optional[QuickPlaySession]:
    """Get an existing session."""
    return _sessions.get(session_id)


def delete_session(session_id: str) -> bool:
    """Delete a session."""
    if session_id in _sessions:
        del _sessions[session_id]
        return True
    return False
