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

logger = logging.getLogger(__name__)

# In-memory session store (cleared on server restart)
_sessions: Dict[str, 'QuickPlaySession'] = {}


class QuickPlaySession:
    """Wraps GameAPI for REST-based quick play with auto-snapshotting."""

    def __init__(self, session_id: str, user_id: str, player_name: str = "Lab Tester",
                 region: str = "european"):
        self.session_id = session_id
        self.user_id = user_id
        self.api = GameAPI(user_id=user_id)
        self.turn_count = 0
        self.snapshot_ids: List[str] = []

        # Run through setup synchronously
        list(self.api.start_game())
        list(self.api.set_player_name(player_name))
        list(self.api.set_region(region))

    def enter_era(self) -> Dict[str, Any]:
        """Enter the first/next era. Returns messages and auto-snapshot."""
        messages = list(self.api.enter_first_era())
        snapshot_id = self._auto_snapshot("arrival")
        return {
            'messages': messages,
            'snapshot_id': snapshot_id,
            'state': self.api.get_current_state(),
        }

    def choose(self, choice: str) -> Dict[str, Any]:
        """Make a choice. Returns messages and auto-snapshot."""
        self.turn_count += 1
        messages = list(self.api.make_choice(choice))
        snapshot_id = self._auto_snapshot(f"turn-{self.turn_count}")
        return {
            'messages': messages,
            'snapshot_id': snapshot_id,
            'state': self.api.get_current_state(),
        }

    def continue_to_next_era(self) -> Dict[str, Any]:
        """Continue after departure."""
        messages = list(self.api.continue_to_next_era())
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
                label=f"Quick Play — {label_suffix}",
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
                   region: str = "european") -> Dict[str, Any]:
    """Create a new quick play session."""
    session_id = str(uuid.uuid4())
    session = QuickPlaySession(session_id, user_id, player_name, region)
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
