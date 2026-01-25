"""
Anachron - Database Storage Module

Storage adapters that call the Express API for persistence instead of JSON files.
"""

import os
import json
import requests
from typing import List, Dict, Optional
from datetime import datetime
from abc import ABC, abstractmethod

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:5000")


class DatabaseSaveManager:
    """Manages saving and loading game states via Express API"""
    
    def __init__(self, api_base: str = None):
        self.api_base = api_base or API_BASE_URL
    
    def save_game(self, user_id: str, game_id: str, state) -> bool:
        """
        Save game state to database via API.
        Returns True if successful.
        """
        try:
            save_data = state.to_save_dict()
            
            response = requests.post(
                f"{self.api_base}/api/saves",
                json={
                    "userId": user_id,
                    "gameId": game_id,
                    "playerName": save_data.get("player_name"),
                    "currentEra": state.current_era.era_name if state.current_era else None,
                    "phase": save_data.get("phase"),
                    "state": save_data,
                },
                timeout=10
            )
            return response.status_code == 200
        except Exception as e:
            print(f"Database save error: {e}")
            return False
    
    def load_game(self, user_id: str, game_id: str):
        """
        Load game state from database via API.
        Returns GameState or None if not found.
        """
        try:
            response = requests.get(
                f"{self.api_base}/api/saves/{user_id}/{game_id}",
                timeout=10
            )
            if response.status_code == 404:
                return None
            if response.status_code != 200:
                return None
            
            data = response.json()
            save_data = data.get("state", data)
            
            from game_state import GameState
            return GameState.from_save_dict(save_data)
        except Exception as e:
            print(f"Database load error: {e}")
            return None
    
    def delete_game(self, user_id: str, game_id: str) -> bool:
        """Delete a saved game"""
        try:
            response = requests.delete(
                f"{self.api_base}/api/saves/{user_id}/{game_id}",
                timeout=10
            )
            return response.status_code == 200
        except Exception:
            return False
    
    def list_user_games(self, user_id: str) -> List[Dict]:
        """List all saved games for a user"""
        try:
            response = requests.get(
                f"{self.api_base}/api/saves/{user_id}",
                timeout=10
            )
            if response.status_code != 200:
                return []
            return response.json()
        except Exception:
            return []


class DatabaseLeaderboardStorage:
    """Database storage for leaderboard via Express API"""
    
    def __init__(self, api_base: str = None):
        self.api_base = api_base or API_BASE_URL
    
    def load_scores(self) -> List[dict]:
        """Load all scores from database"""
        try:
            response = requests.get(
                f"{self.api_base}/api/leaderboard?limit=100",
                timeout=10
            )
            if response.status_code != 200:
                return []
            return response.json()
        except Exception:
            return []
    
    def save_scores(self, scores: List[dict]):
        """Not needed for database storage - scores are saved individually"""
        pass
    
    def add_score(self, score: dict) -> int:
        """Add a score and return its rank (1-indexed)"""
        try:
            response = requests.post(
                f"{self.api_base}/api/leaderboard",
                json={
                    "userId": score.get("user_id", ""),
                    "gameId": score.get("game_id", ""),
                    "playerName": score.get("player_name", "Unknown"),
                    "turnsSurvived": score.get("turns_survived", 0),
                    "erasVisited": score.get("eras_visited", 0),
                    "belongingScore": score.get("belonging", 0),
                    "legacyScore": score.get("legacy", 0),
                    "freedomScore": score.get("freedom", 0),
                    "totalScore": score.get("total", 0),
                    "endingType": score.get("ending_type", ""),
                    "finalEra": score.get("final_era", ""),
                    "blurb": score.get("blurb", ""),
                    "endingNarrative": score.get("ending_narrative", ""),
                },
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("rank", 1)
            return 1
        except Exception as e:
            print(f"Add score error: {e}")
            return 1
    
    def get_top_scores(self, n: int = 10) -> List[dict]:
        """Get top N scores"""
        try:
            response = requests.get(
                f"{self.api_base}/api/leaderboard?limit={n}",
                timeout=10
            )
            if response.status_code != 200:
                return []
            return response.json()
        except Exception:
            return []
    
    def get_user_scores(self, user_id: str, n: int = 10) -> List[dict]:
        """Get top N scores for a specific user"""
        try:
            response = requests.get(
                f"{self.api_base}/api/leaderboard/{user_id}?limit={n}",
                timeout=10
            )
            if response.status_code != 200:
                return []
            return response.json()
        except Exception:
            return []


class DatabaseGameHistory:
    """
    Stores the full narrative history via Express API.
    """
    
    def __init__(self, api_base: str = None):
        self.api_base = api_base or API_BASE_URL
    
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
            requests.post(
                f"{self.api_base}/api/history",
                json={
                    "gameId": game["id"],
                    "userId": game.get("user_id", ""),
                    "playerName": game.get("player_name"),
                    "startedAt": game.get("started_at"),
                    "endedAt": game.get("ended_at"),
                    "eras": game.get("eras", []),
                    "finalScore": game.get("final_score"),
                    "endingType": game.get("ending_type"),
                    "blurb": game.get("blurb"),
                },
                timeout=10
            )
        except Exception as e:
            print(f"Save history error: {e}")
    
    def get_game(self, game_id: str) -> Optional[dict]:
        """Get a completed game record"""
        try:
            response = requests.get(
                f"{self.api_base}/api/history/{game_id}",
                timeout=10
            )
            if response.status_code != 200:
                return None
            return response.json()
        except Exception:
            return None
    
    def get_games_by_leaderboard_entry(self, user_id: str, timestamp: str) -> Optional[dict]:
        """Get game history by leaderboard entry"""
        try:
            response = requests.get(
                f"{self.api_base}/api/histories/{user_id}",
                timeout=10
            )
            if response.status_code != 200:
                return None
            histories = response.json()
            for h in histories:
                if h.get("endedAt", "").startswith(timestamp[:10]):
                    return h
            return histories[0] if histories else None
        except Exception:
            return None


class DatabaseAoAStorage:
    """
    Database storage for Annals of Anachron entries via Express API.
    Implements the same interface as AoAStorage from scoring.py.
    """
    
    def __init__(self, api_base: str = None):
        self.api_base = api_base or API_BASE_URL
    
    def save_entry(self, entry) -> bool:
        """Save an AoA entry to database"""
        try:
            entry_dict = entry.to_dict() if hasattr(entry, 'to_dict') else entry
            
            response = requests.post(
                f"{self.api_base}/api/aoa",
                json={
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
                },
                timeout=15
            )
            return response.status_code == 200
        except Exception as e:
            print(f"Save AoA entry error: {e}")
            return False
    
    def get_entry(self, entry_id: str):
        """Get a specific entry by ID"""
        try:
            response = requests.get(
                f"{self.api_base}/api/aoa/entry/{entry_id}",
                timeout=10
            )
            if response.status_code != 200:
                return None
            
            data = response.json()
            return self._dict_to_entry(data)
        except Exception:
            return None
    
    def get_user_entries(self, user_id: str, limit: int = 20, offset: int = 0) -> List:
        """Get entries for a user with pagination"""
        try:
            response = requests.get(
                f"{self.api_base}/api/aoa/user/{user_id}?limit={limit}&offset={offset}",
                timeout=10
            )
            if response.status_code != 200:
                return []
            
            data = response.json()
            entries_data = data.get("entries", [])
            return [self._dict_to_entry(e) for e in entries_data]
        except Exception:
            return []
    
    def get_recent_entries(self, limit: int = 20, offset: int = 0) -> List:
        """Get recent entries (for public feed) with pagination"""
        try:
            response = requests.get(
                f"{self.api_base}/api/aoa/recent?limit={limit}&offset={offset}",
                timeout=10
            )
            if response.status_code != 200:
                return []
            
            data = response.json()
            entries_data = data.get("entries", [])
            return [self._dict_to_entry(e) for e in entries_data]
        except Exception:
            return []
    
    def count_user_entries(self, user_id: str) -> int:
        """Count total entries for a user"""
        try:
            response = requests.get(
                f"{self.api_base}/api/aoa/count?userId={user_id}",
                timeout=10
            )
            if response.status_code != 200:
                return 0
            return response.json().get("count", 0)
        except Exception:
            return 0
    
    def count_all_entries(self) -> int:
        """Count total entries"""
        try:
            response = requests.get(
                f"{self.api_base}/api/aoa/count",
                timeout=10
            )
            if response.status_code != 200:
                return 0
            return response.json().get("count", 0)
        except Exception:
            return 0
    
    def _dict_to_entry(self, data: dict):
        """Convert API response dict to AoAEntry object"""
        from scoring import AoAEntry
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
            key_npcs=data.get("key_npcs", []),
            defining_moments=data.get("defining_moments", []),
            wisdom_moments=data.get("wisdom_moments", []),
            items_used=data.get("items_used", []),
            player_narrative=data.get("player_narrative", ""),
            historian_narrative=data.get("historian_narrative", ""),
            created_at=data.get("created_at", ""),
            total_score=data.get("total_score", 0),
        )
