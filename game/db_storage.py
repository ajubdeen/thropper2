"""
Anachron - Database Storage Module

Storage adapters that use direct database access via db.py.
"""

import json
from typing import List, Dict, Optional
from datetime import datetime

from db import storage


class DatabaseSaveManager:
    """Manages saving and loading game states via direct database access"""

    def __init__(self):
        pass

    def save_game(self, user_id: str, game_id: str, state) -> bool:
        """
        Save game state to database.
        Returns True if successful.
        """
        try:
            save_data = state.to_save_dict()

            storage.save_game(
                user_id=user_id,
                game_id=game_id,
                player_name=save_data.get("player_name"),
                current_era=state.current_era.era_name if state.current_era else None,
                phase=save_data.get("phase"),
                state=save_data,
            )
            return True
        except Exception as e:
            print(f"Database save error: {e}")
            return False

    def load_game(self, user_id: str, game_id: str):
        """
        Load game state from database.
        Returns GameState or None if not found.
        """
        try:
            data = storage.load_game(user_id, game_id)
            if not data:
                return None

            save_data = data.get("state", data)
            # Handle JSON string if needed
            if isinstance(save_data, str):
                save_data = json.loads(save_data)

            from game_state import GameState
            return GameState.from_save_dict(save_data)
        except Exception as e:
            print(f"Database load error: {e}")
            return None

    def delete_game(self, user_id: str, game_id: str) -> bool:
        """Delete a saved game"""
        try:
            return storage.delete_game(user_id, game_id)
        except Exception:
            return False

    def list_user_games(self, user_id: str) -> List[Dict]:
        """List all saved games for a user"""
        try:
            games = storage.list_user_games(user_id)
            # Convert to expected format
            return [{
                "game_id": g.get("game_id"),
                "player_name": g.get("player_name"),
                "current_era": g.get("current_era"),
                "phase": g.get("phase"),
                "total_turns": g.get("state", {}).get("total_turns", 0) if isinstance(g.get("state"), dict) else 0,
                "saved_at": g.get("saved_at").isoformat() if g.get("saved_at") else None,
            } for g in games]
        except Exception as e:
            print(f"List games error: {e}")
            return []


class DatabaseLeaderboardStorage:
    """Database storage for leaderboard via direct database access"""

    def __init__(self):
        pass

    def load_scores(self) -> List[dict]:
        """Load all scores from database"""
        try:
            scores = storage.get_top_scores(100)
            return [self._format_score(s) for s in scores]
        except Exception:
            return []

    def save_scores(self, scores: List[dict]):
        """Not needed for database storage - scores are saved individually"""
        pass

    def add_score(self, score: dict) -> int:
        """Add a score and return its rank (1-indexed)"""
        try:
            entry = {
                "userId": score.get("user_id", ""),
                "gameId": score.get("game_id", ""),
                "playerName": score.get("player_name", "Unknown"),
                "turnsSurvived": score.get("turns_survived", 0),
                "erasVisited": score.get("eras_visited", 0),
                "belongingScore": score.get("belonging_score", 0),
                "legacyScore": score.get("legacy_score", 0),
                "freedomScore": score.get("freedom_score", 0),
                "totalScore": score.get("total", 0),
                "endingType": score.get("ending_type", ""),
                "finalEra": score.get("final_era", ""),
                "blurb": score.get("blurb", ""),
                "endingNarrative": score.get("ending_narrative", ""),
            }
            storage.add_leaderboard_entry(entry)
            return storage.get_rank(score.get("total", 0))
        except Exception as e:
            print(f"Add score error: {e}")
            return 1

    def get_top_scores(self, n: int = 10) -> List[dict]:
        """Get top N scores"""
        try:
            scores = storage.get_top_scores(n)
            return [self._format_score(s) for s in scores]
        except Exception:
            return []

    def get_user_scores(self, user_id: str, n: int = 10) -> List[dict]:
        """Get top N scores for a specific user"""
        try:
            scores = storage.get_user_scores(user_id, n)
            return [self._format_score(s) for s in scores]
        except Exception:
            return []

    def _format_score(self, s: dict) -> dict:
        """Format database score to expected format"""
        result = {
            "user_id": s.get("user_id"),
            "game_id": s.get("game_id"),
            "player_name": s.get("player_name"),
            "turns_survived": s.get("turns_survived"),
            "eras_visited": s.get("eras_visited"),
            "belonging_score": s.get("belonging_score"),
            "legacy_score": s.get("legacy_score"),
            "freedom_score": s.get("freedom_score"),
            "total": s.get("total_score"),
            "ending_type": s.get("ending_type"),
            "final_era": s.get("final_era"),
            "blurb": s.get("blurb"),
            "ending_narrative": s.get("ending_narrative"),
            "historian_narrative": s.get("historian_narrative"),
            "timestamp": s.get("created_at").isoformat() if s.get("created_at") else None,
        }
        if s.get("portrait_image_path"):
            result["portrait_image_path"] = s["portrait_image_path"]
        return result


class DatabaseGameHistory:
    """
    Stores the full narrative history via direct database access.
    """

    def __init__(self):
        pass

    def start_new_game(self, player_name: str, user_id: str = "") -> dict:
        """Create a new game record and return it"""
        game = {
            "id": datetime.now().strftime("%Y%m%d_%H%M%S"),
            "user_id": user_id,
            "player_name": player_name,
            "started_at": datetime.now().isoformat(),
            "ended_at": None,
            "eras": [],
            "current_era_narrative": [],
            "final_score": None,
            "ending_type": None,
            "blurb": None
        }
        return game

    def add_narrative(self, game: dict, text: str):
        """Add a narrative chunk to the current era"""
        game["current_era_narrative"].append(text)

    def start_era(self, game: dict, era_name: str, era_year: int, era_location: str):
        """Start recording a new era"""
        if game["current_era_narrative"]:
            if game["eras"]:
                game["eras"][-1]["narrative"] = "\n\n".join(game["current_era_narrative"])

        game["eras"].append({
            "era_name": era_name,
            "era_year": era_year,
            "era_location": era_location,
            "narrative": ""
        })
        game["current_era_narrative"] = []

    def end_game(self, game: dict, score):
        """Finalize the game record and save to database"""
        if game["current_era_narrative"] and game["eras"]:
            game["eras"][-1]["narrative"] = "\n\n".join(game["current_era_narrative"])

        game["ended_at"] = datetime.now().isoformat()
        game["final_score"] = score.to_dict() if hasattr(score, 'to_dict') else score
        game["ending_type"] = score.ending_type if hasattr(score, 'ending_type') else None
        game["blurb"] = score.get_blurb() if hasattr(score, 'get_blurb') else None

        try:
            storage.save_game_history({
                "gameId": game["id"],
                "userId": game.get("user_id", ""),
                "playerName": game.get("player_name"),
                "startedAt": game.get("started_at"),
                "endedAt": game.get("ended_at"),
                "eras": game.get("eras", []),
                "finalScore": game.get("final_score"),
                "endingType": game.get("ending_type"),
                "blurb": game.get("blurb"),
            })
        except Exception as e:
            print(f"Save history error: {e}")

    def get_game(self, game_id: str) -> Optional[dict]:
        """Get a completed game record"""
        try:
            return storage.get_game_history(game_id)
        except Exception:
            return None

    def get_games_by_leaderboard_entry(self, user_id: str, timestamp: str) -> Optional[dict]:
        """Get game history by leaderboard entry"""
        try:
            histories = storage.get_user_histories(user_id)
            for h in histories:
                ended_at = h.get("ended_at")
                if ended_at:
                    ended_str = ended_at.isoformat() if hasattr(ended_at, 'isoformat') else str(ended_at)
                    if ended_str.startswith(timestamp[:10]):
                        return h
            return histories[0] if histories else None
        except Exception:
            return None


class DatabaseAoAStorage:
    """
    Database storage for Annals of Anachron entries via direct database access.
    Implements the same interface as AoAStorage from scoring.py.
    """

    def __init__(self):
        pass

    def save_entry(self, entry) -> bool:
        """Save an AoA entry to database"""
        try:
            entry_dict = entry.to_dict() if hasattr(entry, 'to_dict') else entry

            storage.save_aoa_entry({
                "entryId": entry_dict.get("entry_id", ""),
                "userId": entry_dict.get("user_id", ""),
                "gameId": entry_dict.get("game_id", ""),
                "playerName": entry_dict.get("player_name", ""),
                "characterName": entry_dict.get("character_name", ""),
                "finalEra": entry_dict.get("final_era", ""),
                "finalEraYear": entry_dict.get("final_era_year", 0),
                "erasVisited": entry_dict.get("eras_visited", 0),
                "turnsSurvived": entry_dict.get("turns_survived", 0),
                "endingType": entry_dict.get("ending_type", ""),
                "belongingScore": entry_dict.get("belonging_score", 0),
                "legacyScore": entry_dict.get("legacy_score", 0),
                "freedomScore": entry_dict.get("freedom_score", 0),
                "totalScore": entry_dict.get("total_score", 0),
                "keyNpcs": entry_dict.get("key_npcs", []),
                "definingMoments": entry_dict.get("defining_moments", []),
                "wisdomMoments": entry_dict.get("wisdom_moments", []),
                "itemsUsed": entry_dict.get("items_used", []),
                "playerNarrative": entry_dict.get("player_narrative", ""),
                "historianNarrative": entry_dict.get("historian_narrative", ""),
            })
            return True
        except Exception as e:
            print(f"Save AoA entry error: {e}")
            return False

    def get_entry(self, entry_id: str):
        """Get a specific entry by ID"""
        try:
            data = storage.get_aoa_entry(entry_id)
            if not data:
                return None
            return self._dict_to_entry(data)
        except Exception:
            return None

    def get_user_entries(self, user_id: str, limit: int = 20, offset: int = 0) -> List:
        """Get entries for a user with pagination"""
        try:
            entries = storage.get_user_aoa_entries(user_id, limit, offset)
            return [self._dict_to_entry(e) for e in entries]
        except Exception:
            return []

    def get_recent_entries(self, limit: int = 20, offset: int = 0) -> List:
        """Get recent entries (for public feed) with pagination"""
        try:
            entries = storage.get_recent_aoa_entries(limit, offset)
            return [self._dict_to_entry(e) for e in entries]
        except Exception:
            return []

    def count_user_entries(self, user_id: str) -> int:
        """Count total entries for a user"""
        try:
            return storage.count_user_aoa_entries(user_id)
        except Exception:
            return 0

    def count_all_entries(self) -> int:
        """Count total entries"""
        try:
            return storage.count_all_aoa_entries()
        except Exception:
            return 0

    def _dict_to_entry(self, data: dict):
        """Convert database dict to AoAEntry object"""
        from scoring import AoAEntry

        # Handle JSON fields that may be strings
        key_npcs = data.get("key_npcs", [])
        if isinstance(key_npcs, str):
            key_npcs = json.loads(key_npcs)

        defining_moments = data.get("defining_moments", [])
        if isinstance(defining_moments, str):
            defining_moments = json.loads(defining_moments)

        wisdom_moments = data.get("wisdom_moments", [])
        if isinstance(wisdom_moments, str):
            wisdom_moments = json.loads(wisdom_moments)

        items_used = data.get("items_used", [])
        if isinstance(items_used, str):
            items_used = json.loads(items_used)

        created_at = data.get("created_at")
        if hasattr(created_at, 'isoformat'):
            created_at = created_at.isoformat()

        return AoAEntry(
            entry_id=data.get("entry_id", ""),
            user_id=data.get("user_id", ""),
            game_id=data.get("game_id", ""),
            player_name=data.get("player_name", ""),
            character_name=data.get("character_name", ""),
            final_era=data.get("final_era", ""),
            final_era_year=data.get("final_era_year", 0),
            eras_visited=data.get("eras_visited", 0),
            turns_survived=data.get("turns_survived", 0),
            ending_type=data.get("ending_type", ""),
            belonging_score=data.get("belonging_score", 0),
            legacy_score=data.get("legacy_score", 0),
            freedom_score=data.get("freedom_score", 0),
            key_npcs=key_npcs,
            defining_moments=defining_moments,
            wisdom_moments=wisdom_moments,
            items_used=items_used,
            player_narrative=data.get("player_narrative", ""),
            historian_narrative=data.get("historian_narrative", ""),
            created_at=created_at or "",
            total_score=data.get("total_score", 0),
        )
