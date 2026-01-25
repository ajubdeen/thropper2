"""
Anachron - Scoring Module

Tracks player score invisibly during gameplay, calculates final score,
and manages the leaderboard with user_id support for multi-user deployments.

Also includes Annals of Anachron (AoA) system for shareable ending summaries.
"""

import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Dict, Optional, Callable
from abc import ABC, abstractmethod


# =============================================================================
# AOA (ANNALS OF ANACHRON) QUALIFICATION THRESHOLDS
# =============================================================================

AOA_THRESHOLDS = {
    "min_turns": 15,           # Minimum turns to qualify
    "min_eras": 1,             # Minimum eras visited
    "min_fulfillment": 30,     # Minimum total fulfillment (belonging + legacy + freedom)
    "excluded_endings": ["abandoned"]  # Endings that don't qualify
}


@dataclass
class Score:
    """
    Player's score breakdown.
    
    Scoring:
    - Survival: 10 points per turn survived
    - Belonging: 0-100 based on final fulfillment
    - Legacy: 0-100 based on final fulfillment
    - Freedom: 0-100 based on final fulfillment
    - Exploration: 50 points per era visited
    - Ending Bonus: Based on ending type (complete=200, balanced=150, single anchor=100, searching=50)
    """
    
    turns_survived: int = 0
    eras_visited: int = 0
    belonging_score: int = 0
    legacy_score: int = 0
    freedom_score: int = 0
    ending_type: str = "searching"
    
    # Metadata
    player_name: str = ""
    user_id: str = ""  # Added for multi-user support
    final_era: str = ""
    timestamp: str = ""
    game_id: str = ""  # Links to saved game
    ending_narrative: str = ""  # Full ending narrative for stay-forever endings
    
    @property
    def survival_points(self) -> int:
        """Points from surviving turns"""
        return self.turns_survived * 10
    
    @property
    def exploration_points(self) -> int:
        """Points from visiting different eras"""
        return self.eras_visited * 50
    
    @property
    def fulfillment_points(self) -> int:
        """Points from fulfillment anchors"""
        return self.belonging_score + self.legacy_score + self.freedom_score
    
    @property
    def ending_bonus(self) -> int:
        """Bonus points based on ending type"""
        bonuses = {
            "complete": 200,      # All three anchors high
            "balanced": 150,      # Two anchors high
            "belonging": 100,     # Found community
            "legacy": 100,        # Built something lasting
            "freedom": 100,       # Found independence
            "searching": 50,      # Chose to stay without fulfillment
            "abandoned": 25       # Quit before finding happiness
        }
        return bonuses.get(self.ending_type, 25)
    
    @property
    def total(self) -> int:
        """Total score"""
        return (self.survival_points + self.exploration_points + 
                self.fulfillment_points + self.ending_bonus)
    
    def get_breakdown_display(self) -> str:
        """Get formatted score breakdown for display"""
        lines = []
        lines.append("-" * 40)
        lines.append("           FINAL SCORE")
        lines.append("-" * 40)
        lines.append("")
        lines.append(f"  Survival ({self.turns_survived} turns x 10)".ljust(32) + f"{self.survival_points:>6}")
        lines.append(f"  Exploration ({self.eras_visited} eras x 50)".ljust(32) + f"{self.exploration_points:>6}")
        lines.append("")
        lines.append("  Fulfillment:")
        lines.append(f"    Belonging".ljust(32) + f"{self.belonging_score:>6}")
        lines.append(f"    Legacy".ljust(32) + f"{self.legacy_score:>6}")
        lines.append(f"    Freedom".ljust(32) + f"{self.freedom_score:>6}")
        lines.append("")
        lines.append(f"  Ending Bonus ({self.ending_type})".ljust(32) + f"{self.ending_bonus:>6}")
        lines.append("")
        lines.append("-" * 40)
        lines.append(f"  TOTAL".ljust(32) + f"{self.total:>6}")
        lines.append("-" * 40)
        return "\n".join(lines)
    
    def get_narrative_summary(self) -> str:
        """Generate a narrative summary of the player's journey"""
        
        # Survival narrative
        if self.turns_survived < 10:
            survival_text = "A brief journey through time"
        elif self.turns_survived < 30:
            survival_text = "Several years spent across history"
        elif self.turns_survived < 50:
            survival_text = "Decades of experience in other eras"
        else:
            survival_text = "A lifetime's worth of temporal wandering"
        
        # Exploration narrative
        if self.eras_visited == 1:
            explore_text = "finding your place in a single era"
        elif self.eras_visited <= 3:
            explore_text = f"passing through {self.eras_visited} different periods of history"
        else:
            explore_text = f"an extensive tour across {self.eras_visited} distinct eras"
        
        # Fulfillment narrative
        high_anchors = []
        if self.belonging_score >= 60:
            high_anchors.append("community")
        if self.legacy_score >= 60:
            high_anchors.append("lasting impact")
        if self.freedom_score >= 60:
            high_anchors.append("personal freedom")
        
        # For abandoned games, skip the fulfillment text
        if self.ending_type == "abandoned":
            fulfillment_text = "The search continues elsewhere—or perhaps it doesn't."
        elif len(high_anchors) == 3:
            fulfillment_text = "You achieved the rare trifecta: belonging, legacy, and freedom."
        elif len(high_anchors) == 2:
            fulfillment_text = f"You found {high_anchors[0]} and {high_anchors[1]}."
        elif len(high_anchors) == 1:
            fulfillment_text = f"Above all, you found {high_anchors[0]}."
        else:
            fulfillment_text = "You chose to stay, seeking what fulfillment might come."
        
        # Ending narrative
        ending_texts = {
            "complete": "Your journey ended in completeness—a full life, fully lived.",
            "balanced": "You found balance, if not perfection. A life well-chosen.",
            "belonging": "In the end, it was people who made a place worth staying.",
            "legacy": "You built something that would outlast you. That was enough.",
            "freedom": "You found freedom on your own terms. Unburdened at last.",
            "searching": "Perhaps happiness would find you yet, in this new home.",
            "abandoned": "Your journey ended before you found what you were seeking."
        }
        ending_text = ending_texts.get(self.ending_type, ending_texts["searching"])
        
        return f"""{survival_text}, {explore_text}.

{fulfillment_text}

{ending_text}"""
    
    def get_blurb(self) -> str:
        """Generate a short blurb for leaderboard display"""
        if self.ending_type == "abandoned":
            return f"Quit in {self.final_era}"
        elif self.ending_type == "complete":
            return f"Found happiness in {self.final_era}"
        elif self.ending_type in ["belonging", "legacy", "freedom"]:
            return f"Stayed in {self.final_era} ({self.ending_type})"
        elif self.ending_type == "balanced":
            return f"Found balance in {self.final_era}"
        else:
            return f"Settled in {self.final_era}"
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON storage"""
        return {
            "player_name": self.player_name,
            "user_id": self.user_id,
            "game_id": self.game_id,
            "total": self.total,
            "turns_survived": self.turns_survived,
            "eras_visited": self.eras_visited,
            "belonging_score": self.belonging_score,
            "legacy_score": self.legacy_score,
            "freedom_score": self.freedom_score,
            "ending_type": self.ending_type,
            "final_era": self.final_era,
            "timestamp": self.timestamp,
            "blurb": self.get_blurb(),
            "ending_narrative": self.ending_narrative
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Score':
        """Create from dictionary"""
        return cls(
            player_name=data.get("player_name", "Unknown"),
            user_id=data.get("user_id", ""),
            game_id=data.get("game_id", ""),
            turns_survived=data.get("turns_survived", 0),
            eras_visited=data.get("eras_visited", 0),
            belonging_score=data.get("belonging_score", 0),
            legacy_score=data.get("legacy_score", 0),
            freedom_score=data.get("freedom_score", 0),
            ending_type=data.get("ending_type", "searching"),
            final_era=data.get("final_era", "Unknown"),
            timestamp=data.get("timestamp", ""),
            ending_narrative=data.get("ending_narrative", "")
        )


# =============================================================================
# ANNALS OF ANACHRON (AOA) ENTRY
# =============================================================================

@dataclass
class AoAEntry:
    """
    An entry in the Annals of Anachron - a shareable summary of a completed journey.
    
    Generated when a player completes a game with sufficient engagement
    (not abandoned, reasonable playtime, some fulfillment achieved).
    
    Contains two narratives:
    - player_version: What the player sees (their personal journey)
    - historian_version: A third-person "historical" account for sharing
    """
    
    # Identity
    entry_id: str = ""           # Unique ID for this entry
    user_id: str = ""            # Owner of this entry
    game_id: str = ""            # Link to original game
    player_name: str = ""        # Player's name
    character_name: str = ""     # Character's name in final era
    
    # Journey summary
    final_era: str = ""          # Where they stayed
    final_era_year: int = 0      # Year in final era
    eras_visited: int = 0        # Total eras visited
    turns_survived: int = 0      # Total turns
    ending_type: str = ""        # Type of ending achieved
    
    # Fulfillment snapshot
    belonging_score: int = 0
    legacy_score: int = 0
    freedom_score: int = 0
    
    # Key events (from game_events log)
    key_npcs: List[str] = field(default_factory=list)      # Important relationships
    defining_moments: List[Dict] = field(default_factory=list)  # Major anchor shifts
    wisdom_moments: List[str] = field(default_factory=list)     # Historical insights shown
    items_used: List[str] = field(default_factory=list)    # Items that mattered
    
    # Narratives
    player_narrative: str = ""      # Personal ending (what player sees)
    historian_narrative: str = ""   # Third-person "history" for sharing
    
    # Metadata
    created_at: str = ""
    total_score: int = 0
    
    def qualifies_for_aoa(self) -> bool:
        """Check if this entry meets AoA qualification thresholds"""
        if self.ending_type in AOA_THRESHOLDS["excluded_endings"]:
            return False
        if self.turns_survived < AOA_THRESHOLDS["min_turns"]:
            return False
        if self.eras_visited < AOA_THRESHOLDS["min_eras"]:
            return False
        total_fulfillment = self.belonging_score + self.legacy_score + self.freedom_score
        if total_fulfillment < AOA_THRESHOLDS["min_fulfillment"]:
            return False
        return True
    
    def get_share_text(self) -> str:
        """Generate shareable text summary"""
        year_str = f"{abs(self.final_era_year)} BCE" if self.final_era_year < 0 else f"{self.final_era_year} CE"
        
        # Build a compelling one-liner
        if self.ending_type == "complete":
            achievement = "found belonging, legacy, and freedom"
        elif self.ending_type == "balanced":
            achievement = "found balance in an unfamiliar time"
        elif self.ending_type == "belonging":
            achievement = "found a community to call home"
        elif self.ending_type == "legacy":
            achievement = "built something that would outlast them"
        elif self.ending_type == "freedom":
            achievement = "found freedom on their own terms"
        else:
            achievement = "chose to stay and build a life"
        
        return f"{self.character_name or self.player_name} {achievement} in {self.final_era} ({year_str}). Score: {self.total_score}"
    
    def get_og_description(self) -> str:
        """Generate Open Graph description for social sharing"""
        year_str = f"{abs(self.final_era_year)} BCE" if self.final_era_year < 0 else f"{self.final_era_year} CE"
        
        lines = []
        lines.append(f"A time traveler's journey ended in {self.final_era}, {year_str}.")
        
        if self.key_npcs:
            lines.append(f"They formed bonds with {', '.join(self.key_npcs[:2])}.")
        
        if self.ending_type == "complete":
            lines.append("They found everything they were looking for.")
        elif self.ending_type in ["belonging", "legacy", "freedom"]:
            lines.append(f"They found {self.ending_type}.")
        
        return " ".join(lines)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for storage"""
        return {
            "entry_id": self.entry_id,
            "user_id": self.user_id,
            "game_id": self.game_id,
            "player_name": self.player_name,
            "character_name": self.character_name,
            "final_era": self.final_era,
            "final_era_year": self.final_era_year,
            "eras_visited": self.eras_visited,
            "turns_survived": self.turns_survived,
            "ending_type": self.ending_type,
            "belonging_score": self.belonging_score,
            "legacy_score": self.legacy_score,
            "freedom_score": self.freedom_score,
            "key_npcs": self.key_npcs,
            "defining_moments": self.defining_moments,
            "wisdom_moments": self.wisdom_moments,
            "items_used": self.items_used,
            "player_narrative": self.player_narrative,
            "historian_narrative": self.historian_narrative,
            "created_at": self.created_at,
            "total_score": self.total_score
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'AoAEntry':
        """Create from dictionary"""
        return cls(
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
            total_score=data.get("total_score", 0)
        )
    
    @classmethod
    def from_game_state(cls, game_state, score: 'Score') -> 'AoAEntry':
        """
        Create an AoA entry from completed game state and score.
        
        Extracts key events from game_state.game_events to build the entry.
        """
        entry = cls(
            entry_id=f"aoa_{score.game_id}_{datetime.now().strftime('%H%M%S')}",
            user_id=score.user_id,
            game_id=score.game_id,
            player_name=score.player_name,
            final_era=score.final_era,
            eras_visited=score.eras_visited,
            turns_survived=score.turns_survived,
            ending_type=score.ending_type,
            belonging_score=score.belonging_score,
            legacy_score=score.legacy_score,
            freedom_score=score.freedom_score,
            created_at=datetime.now().isoformat(),
            total_score=score.total,
            player_narrative=score.ending_narrative
        )
        
        # Extract character name from current era
        if game_state.current_era:
            entry.character_name = getattr(game_state.current_era, 'character_name', '') or ''
            entry.final_era_year = game_state.current_era.era_year
        
        # Extract key events from game_events log
        if hasattr(game_state, 'game_events'):
            for event in game_state.game_events:
                event_type = event.get('type', '')
                
                if event_type == 'relationship':
                    name = event.get('name', '')
                    if name and name not in entry.key_npcs:
                        entry.key_npcs.append(name)
                
                elif event_type == 'defining_moment':
                    entry.defining_moments.append({
                        'anchor': event.get('anchor', ''),
                        'delta': event.get('delta', 0),
                        'era_id': event.get('era_id', '')
                    })
                
                elif event_type == 'wisdom':
                    wisdom_id = event.get('id', '')
                    if wisdom_id and wisdom_id not in entry.wisdom_moments:
                        entry.wisdom_moments.append(wisdom_id)
                
                elif event_type == 'item_use':
                    item_id = event.get('item_id', '')
                    if item_id and item_id not in entry.items_used:
                        entry.items_used.append(item_id)
        
        # Limit lists to reasonable sizes
        entry.key_npcs = entry.key_npcs[:10]
        entry.defining_moments = entry.defining_moments[:5]
        entry.wisdom_moments = entry.wisdom_moments[:5]
        entry.items_used = entry.items_used[:5]
        
        return entry


# =============================================================================
# AOA STORAGE
# =============================================================================

class AoAStorage(ABC):
    """Abstract interface for AoA storage backends"""
    
    @abstractmethod
    def save_entry(self, entry: AoAEntry) -> bool:
        """Save an AoA entry"""
        pass
    
    @abstractmethod
    def get_entry(self, entry_id: str) -> Optional[AoAEntry]:
        """Get a specific entry by ID"""
        pass
    
    @abstractmethod
    def get_user_entries(self, user_id: str, limit: int = 20, offset: int = 0) -> List[AoAEntry]:
        """Get entries for a user with pagination"""
        pass
    
    @abstractmethod
    def get_recent_entries(self, limit: int = 20, offset: int = 0) -> List[AoAEntry]:
        """Get recent entries (for public feed) with pagination"""
        pass
    
    @abstractmethod
    def count_user_entries(self, user_id: str) -> int:
        """Count total entries for a user"""
        pass
    
    @abstractmethod
    def count_all_entries(self) -> int:
        """Count total entries"""
        pass


class JSONAoAStorage(AoAStorage):
    """Local JSON file storage for AoA entries"""
    
    def __init__(self, filepath: str = "annals_of_anachron.json"):
        self.filepath = filepath
        self.entries: List[dict] = []
        self._load()
    
    def _load(self):
        """Load entries from file"""
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, 'r', encoding='utf-8') as f:
                    self.entries = json.load(f)
            except (json.JSONDecodeError, IOError):
                self.entries = []
        else:
            self.entries = []
    
    def _save(self):
        """Save entries to file"""
        try:
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(self.entries, f, indent=2, ensure_ascii=False)
        except IOError:
            pass
    
    def save_entry(self, entry: AoAEntry) -> bool:
        """Save an AoA entry"""
        try:
            self.entries.append(entry.to_dict())
            self.entries = self.entries[-500:]  # Keep last 500 entries
            self._save()
            return True
        except Exception:
            return False
    
    def get_entry(self, entry_id: str) -> Optional[AoAEntry]:
        """Get a specific entry by ID"""
        for entry_dict in self.entries:
            if entry_dict.get("entry_id") == entry_id:
                return AoAEntry.from_dict(entry_dict)
        return None
    
    def get_user_entries(self, user_id: str, limit: int = 20, offset: int = 0) -> List[AoAEntry]:
        """Get entries for a user with pagination"""
        user_entries = [e for e in self.entries if e.get("user_id") == user_id]
        user_entries.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        paginated = user_entries[offset:offset + limit]
        return [AoAEntry.from_dict(e) for e in paginated]
    
    def get_recent_entries(self, limit: int = 20, offset: int = 0) -> List[AoAEntry]:
        """Get recent entries (for public feed) with pagination"""
        sorted_entries = sorted(self.entries, key=lambda x: x.get("created_at", ""), reverse=True)
        paginated = sorted_entries[offset:offset + limit]
        return [AoAEntry.from_dict(e) for e in paginated]
    
    def count_user_entries(self, user_id: str) -> int:
        """Count total entries for a user"""
        return len([e for e in self.entries if e.get("user_id") == user_id])
    
    def count_all_entries(self) -> int:
        """Count total entries"""
        return len(self.entries)


def _get_default_aoa_storage():
    """Get the default AoA storage backend (database if available, else JSON)"""
    try:
        from db_storage import DatabaseAoAStorage
        return DatabaseAoAStorage()
    except Exception:
        return JSONAoAStorage()


class AnnalsOfAnachron:
    """
    Manages the Annals of Anachron - a collection of completed journeys.
    
    Provides methods to create, store, and retrieve AoA entries.
    """
    
    def __init__(self, storage: AoAStorage = None):
        self.storage = storage or _get_default_aoa_storage()
    
    def create_entry(self, game_state, score: Score) -> Optional[AoAEntry]:
        """
        Create an AoA entry from a completed game.
        
        Returns None if the game doesn't qualify for AoA.
        """
        entry = AoAEntry.from_game_state(game_state, score)
        
        if not entry.qualifies_for_aoa():
            return None
        
        return entry
    
    def save_entry(self, entry: AoAEntry) -> bool:
        """Save an entry to the archive"""
        return self.storage.save_entry(entry)
    
    def get_entry(self, entry_id: str) -> Optional[AoAEntry]:
        """Get a specific entry"""
        return self.storage.get_entry(entry_id)
    
    def get_user_archive(self, user_id: str, limit: int = 20, offset: int = 0) -> Dict:
        """
        Get a user's archive entries with pagination info.
        
        Returns dict with 'entries', 'total', 'limit', 'offset', 'has_more'
        """
        entries = self.storage.get_user_entries(user_id, limit, offset)
        total = self.storage.count_user_entries(user_id)
        
        return {
            'entries': entries,
            'total': total,
            'limit': limit,
            'offset': offset,
            'has_more': offset + len(entries) < total
        }
    
    def get_public_feed(self, limit: int = 20, offset: int = 0) -> Dict:
        """
        Get recent entries for public display with pagination info.
        
        Returns dict with 'entries', 'total', 'limit', 'offset', 'has_more'
        """
        entries = self.storage.get_recent_entries(limit, offset)
        total = self.storage.count_all_entries()
        
        return {
            'entries': entries,
            'total': total,
            'limit': limit,
            'offset': offset,
            'has_more': offset + len(entries) < total
        }

class LeaderboardStorage(ABC):
    """Abstract interface for leaderboard storage backends"""
    
    @abstractmethod
    def load_scores(self) -> List[dict]:
        """Load all scores"""
        pass
    
    @abstractmethod
    def save_scores(self, scores: List[dict]):
        """Save all scores"""
        pass
    
    @abstractmethod
    def add_score(self, score: dict) -> int:
        """Add a score and return its rank"""
        pass
    
    @abstractmethod
    def get_top_scores(self, n: int = 10) -> List[dict]:
        """Get top N scores"""
        pass
    
    @abstractmethod
    def get_user_scores(self, user_id: str, n: int = 10) -> List[dict]:
        """Get top N scores for a specific user"""
        pass


class JSONLeaderboardStorage(LeaderboardStorage):
    """Local JSON file storage for leaderboard (default implementation)"""
    
    def __init__(self, filepath: str = "leaderboard.json"):
        self.filepath = filepath
        self.scores: List[dict] = []
        self._load()
    
    def _load(self):
        """Load leaderboard from file"""
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, 'r') as f:
                    self.scores = json.load(f)
            except (json.JSONDecodeError, IOError):
                self.scores = []
        else:
            self.scores = []
    
    def _save(self):
        """Save leaderboard to file"""
        try:
            with open(self.filepath, 'w') as f:
                json.dump(self.scores, f, indent=2)
        except IOError:
            pass  # Silently fail if can't save
    
    def load_scores(self) -> List[dict]:
        return self.scores
    
    def save_scores(self, scores: List[dict]):
        self.scores = scores
        self._save()
    
    def add_score(self, score: dict) -> int:
        """Add a score and return its rank (1-indexed)"""
        self.scores.append(score)
        self.scores.sort(key=lambda x: x.get("total", 0), reverse=True)
        self.scores = self.scores[:100]  # Keep top 100
        self._save()
        
        # Find rank
        for i, s in enumerate(self.scores):
            if s.get("timestamp") == score.get("timestamp") and s.get("user_id") == score.get("user_id"):
                return i + 1
        return len(self.scores)
    
    def get_top_scores(self, n: int = 10) -> List[dict]:
        return self.scores[:n]
    
    def get_user_scores(self, user_id: str, n: int = 10) -> List[dict]:
        user_scores = [s for s in self.scores if s.get("user_id") == user_id]
        return user_scores[:n]


class Leaderboard:
    """Manages high scores across games with pluggable storage backend"""
    
    def __init__(self, storage: LeaderboardStorage = None, filepath: str = "leaderboard.json"):
        """
        Initialize leaderboard with optional custom storage backend.
        
        Args:
            storage: Custom storage backend (for external databases)
            filepath: Path for default JSON storage (ignored if storage is provided)
        """
        self.storage = storage or JSONLeaderboardStorage(filepath)
    
    def add_score(self, score: Score) -> int:
        """
        Add a score to the leaderboard.
        Returns the rank (1-indexed).
        """
        return self.storage.add_score(score.to_dict())
    
    def get_top_scores(self, n: int = 10) -> List[dict]:
        """Get top N scores globally"""
        return self.storage.get_top_scores(n)
    
    def get_user_scores(self, user_id: str, n: int = 10) -> List[dict]:
        """Get top N scores for a specific user"""
        return self.storage.get_user_scores(user_id, n)
    
    def get_display(self, highlight_score: Optional[Score] = None) -> str:
        """Get formatted leaderboard display"""
        lines = []
        lines.append("-" * 60)
        lines.append("                    LEADERBOARD")
        lines.append("-" * 60)
        lines.append("")
        
        top_scores = self.get_top_scores(10)
        
        if not top_scores:
            lines.append("  No scores yet. You're the first!")
        else:
            for i, s in enumerate(top_scores):
                rank = i + 1
                name = s.get("player_name", "Unknown")[:16].ljust(16)
                total = s.get("total", 0)
                blurb = s.get("blurb", "")[:40]
                
                # Highlight current score if provided
                marker = ""
                if highlight_score and s.get("timestamp") == highlight_score.timestamp:
                    marker = " <-"
                
                lines.append(f"  {rank:>2}. {name}   {total:>5} pts{marker}")
                if blurb:
                    lines.append(f"      {blurb}")
                lines.append("")
        
        lines.append("-" * 60)
        return "\n".join(lines)


def calculate_score(game_state, ending_type_override: str = None, user_id: str = "", game_id: str = "", ending_narrative: str = "") -> Score:
    """Calculate the final score from game state
    
    Args:
        game_state: The current game state
        ending_type_override: If provided, use this instead of calculating from fulfillment
                              (e.g., "abandoned" when player quits)
        user_id: User ID for multi-user support
        game_id: Game ID to link score to saved game
        ending_narrative: The full ending narrative for stay-forever endings
    """
    
    # Get values from game state
    turns = game_state.time_machine.total_turns
    eras = len(game_state.time_machine.eras_visited)
    
    # Get fulfillment scores (they're 0-100, stored in Anchor objects)
    belonging = game_state.fulfillment.belonging.value
    legacy = game_state.fulfillment.legacy.value
    freedom = game_state.fulfillment.freedom.value
    
    # Get ending type (use override if provided)
    if ending_type_override:
        ending_type = ending_type_override
    else:
        ending_type = game_state.fulfillment.get_ending_type()
    
    # Create score
    score = Score(
        turns_survived=turns,
        eras_visited=eras,
        belonging_score=belonging,
        legacy_score=legacy,
        freedom_score=freedom,
        ending_type=ending_type,
        player_name=game_state.player_name,
        user_id=user_id,
        game_id=game_id,
        final_era=game_state.current_era.era_name if game_state.current_era else "Unknown",
        timestamp=datetime.now().isoformat(),
        ending_narrative=ending_narrative
    )
    
    return score


class GameHistory:
    """
    Stores the full narrative history of each playthrough.
    Saved to game_history.json for players to revisit their stories.
    """
    
    def __init__(self, filepath: str = "game_history.json"):
        self.filepath = filepath
        self.games: List[dict] = []
        self._load()
    
    def _load(self):
        """Load history from file"""
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, 'r', encoding='utf-8') as f:
                    self.games = json.load(f)
            except (json.JSONDecodeError, IOError):
                self.games = []
        else:
            self.games = []
    
    def _save(self):
        """Save history to file"""
        try:
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(self.games, f, indent=2, ensure_ascii=False)
        except IOError:
            pass  # Silently fail if can't save
    
    def start_new_game(self, player_name: str, user_id: str = "") -> dict:
        """Create a new game record and return it"""
        game = {
            "id": datetime.now().strftime("%Y%m%d_%H%M%S"),
            "user_id": user_id,
            "player_name": player_name,
            "started_at": datetime.now().isoformat(),
            "ended_at": None,
            "eras": [],  # List of era records
            "current_era_narrative": [],  # Narrative chunks for current era
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
        # Save previous era if exists
        if game["current_era_narrative"]:
            if game["eras"]:
                game["eras"][-1]["narrative"] = "\n\n".join(game["current_era_narrative"])
        
        # Start new era record
        game["eras"].append({
            "era_name": era_name,
            "era_year": era_year,
            "era_location": era_location,
            "narrative": ""
        })
        game["current_era_narrative"] = []
    
    def end_game(self, game: dict, score: Score):
        """Finalize the game record"""
        # Save final era narrative
        if game["current_era_narrative"] and game["eras"]:
            game["eras"][-1]["narrative"] = "\n\n".join(game["current_era_narrative"])
        
        game["ended_at"] = datetime.now().isoformat()
        game["final_score"] = score.to_dict()
        game["ending_type"] = score.ending_type
        game["blurb"] = score.get_blurb()
        
        # Add to history
        self.games.append(game)
        self._save()
    
    def get_user_games(self, user_id: str, include_in_progress: bool = False) -> List[dict]:
        """Get all games for a specific user"""
        user_games = [g for g in self.games if g.get("user_id") == user_id]
        if not include_in_progress:
            user_games = [g for g in user_games if g.get("ended_at") is not None]
        return user_games
    
    def get_game_summary(self, game: dict) -> str:
        """Get a readable summary of a game"""
        lines = []
        lines.append(f"--- {game['player_name']}'s Journey ---")
        lines.append(f"Started: {game['started_at'][:10]}")
        
        if game['final_score']:
            lines.append(f"Score: {game['final_score'].get('total', 0)} pts")
            lines.append(f"Ending: {game.get('blurb', 'Unknown')}")
        
        lines.append("")
        lines.append("Eras Visited:")
        for era in game.get('eras', []):
            year = era.get('era_year', 0)
            year_str = f"{abs(year)} BCE" if year < 0 else f"{year} CE"
            lines.append(f"  - {era.get('era_name', 'Unknown')} ({year_str})")
        
        return "\n".join(lines)
    
    def get_full_story(self, game_id: str) -> Optional[str]:
        """Get the full narrative of a specific game"""
        for game in self.games:
            if game.get('id') == game_id:
                lines = []
                lines.append("-" * 60)
                lines.append(f"  THE JOURNEY OF {game['player_name'].upper()}")
                lines.append("-" * 60)
                lines.append("")
                
                for era in game.get('eras', []):
                    year = era.get('era_year', 0)
                    year_str = f"{abs(year)} BCE" if year < 0 else f"{year} CE"
                    
                    lines.append(f"--- {era.get('era_name', 'Unknown')} ({year_str}) ---")
                    lines.append("")
                    lines.append(era.get('narrative', '[No narrative recorded]'))
                    lines.append("")
                    lines.append("")
                
                if game.get('final_score'):
                    lines.append("-" * 60)
                    lines.append(f"  Final Score: {game['final_score'].get('total', 0)}")
                    lines.append(f"  {game.get('blurb', '')}")
                    lines.append("-" * 60)
                
                return "\n".join(lines)
        
        return None
    
    def list_games(self, user_id: str = None) -> str:
        """List saved games, optionally filtered by user"""
        games_to_show = self.games
        if user_id:
            games_to_show = [g for g in games_to_show if g.get("user_id") == user_id]
        
        if not games_to_show:
            return "No saved games yet."
        
        lines = []
        lines.append("-" * 60)
        lines.append("               SAVED JOURNEYS")
        lines.append("-" * 60)
        lines.append("")
        
        for i, game in enumerate(reversed(games_to_show[-20:])):  # Last 20 games, newest first
            score = game.get('final_score', {}).get('total', 0)
            date = game.get('started_at', '')[:10]
            name = game.get('player_name', 'Unknown')
            blurb = game.get('blurb', 'Unknown ending')
            game_id = game.get('id', '')
            
            lines.append(f"  [{game_id}] {name} - {score} pts")
            lines.append(f"      {date} | {blurb}")
            lines.append("")
        
        lines.append("-" * 60)
        lines.append("  To read a story, open game_history.json")
        lines.append("-" * 60)
        
        return "\n".join(lines)
