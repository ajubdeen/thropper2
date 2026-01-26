"""
Database operations for Anachron V2.
Replaces the Node.js/Drizzle ORM layer with Python/psycopg2.
"""

import os
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)

DATABASE_URL = os.environ.get('DATABASE_URL')


@contextmanager
def get_db():
    """Get a database connection with automatic cleanup."""
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL environment variable not set")

    conn = psycopg2.connect(DATABASE_URL)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


class Storage:
    """Database storage operations."""

    # ==================== Users ====================

    def upsert_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Insert or update a user on OAuth login."""
        with get_db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    INSERT INTO users (id, email, first_name, last_name, profile_image_url, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
                    ON CONFLICT (id) DO UPDATE SET
                        email = EXCLUDED.email,
                        first_name = EXCLUDED.first_name,
                        last_name = EXCLUDED.last_name,
                        profile_image_url = EXCLUDED.profile_image_url,
                        updated_at = NOW()
                    RETURNING *
                """, (
                    user_data['id'],
                    user_data.get('email'),
                    user_data.get('first_name'),
                    user_data.get('last_name'),
                    user_data.get('profile_image_url')
                ))
                return dict(cur.fetchone())

    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Fetch user profile by ID."""
        with get_db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM users WHERE id = %s LIMIT 1",
                    (user_id,)
                )
                result = cur.fetchone()
                return dict(result) if result else None

    # ==================== Game Saves ====================

    def save_game(self, user_id: str, game_id: str, player_name: Optional[str],
                  current_era: Optional[str], phase: Optional[str],
                  state: Dict[str, Any], started_at: Optional[datetime] = None) -> Dict[str, Any]:
        """Save or update a game."""
        with get_db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Check if exists
                cur.execute(
                    "SELECT id FROM game_saves WHERE user_id = %s AND game_id = %s",
                    (user_id, game_id)
                )
                existing = cur.fetchone()

                if existing:
                    cur.execute("""
                        UPDATE game_saves
                        SET state = %s, saved_at = NOW(), player_name = %s,
                            current_era = %s, phase = %s
                        WHERE user_id = %s AND game_id = %s
                        RETURNING *
                    """, (json.dumps(state), player_name, current_era, phase, user_id, game_id))
                else:
                    cur.execute("""
                        INSERT INTO game_saves (user_id, game_id, player_name, current_era, phase, state, started_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        RETURNING *
                    """, (user_id, game_id, player_name, current_era, phase, json.dumps(state), started_at))

                return dict(cur.fetchone())

    def load_game(self, user_id: str, game_id: str) -> Optional[Dict[str, Any]]:
        """Load a saved game."""
        with get_db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM game_saves WHERE user_id = %s AND game_id = %s LIMIT 1",
                    (user_id, game_id)
                )
                result = cur.fetchone()
                return dict(result) if result else None

    def delete_game(self, user_id: str, game_id: str) -> bool:
        """Delete a saved game."""
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM game_saves WHERE user_id = %s AND game_id = %s",
                    (user_id, game_id)
                )
                return True

    def list_user_games(self, user_id: str) -> List[Dict[str, Any]]:
        """List all saved games for a user."""
        with get_db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM game_saves WHERE user_id = %s ORDER BY saved_at DESC",
                    (user_id,)
                )
                return [dict(row) for row in cur.fetchall()]

    # ==================== Leaderboard ====================

    def add_leaderboard_entry(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """Add a leaderboard entry."""
        with get_db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    INSERT INTO leaderboard_entries
                    (user_id, game_id, player_name, turns_survived, eras_visited,
                     belonging_score, legacy_score, freedom_score, total_score,
                     ending_type, final_era, blurb, ending_narrative)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING *
                """, (
                    entry['userId'], entry.get('gameId'), entry['playerName'],
                    entry.get('turnsSurvived', 0), entry.get('erasVisited', 0),
                    entry.get('belongingScore', 0), entry.get('legacyScore', 0),
                    entry.get('freedomScore', 0), entry.get('totalScore', 0),
                    entry.get('endingType'), entry.get('finalEra'),
                    entry.get('blurb'), entry.get('endingNarrative')
                ))
                return dict(cur.fetchone())

    def get_top_scores(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top leaderboard scores."""
        with get_db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM leaderboard_entries ORDER BY total_score DESC LIMIT %s",
                    (limit,)
                )
                return [dict(row) for row in cur.fetchall()]

    def get_user_scores(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get a user's leaderboard scores."""
        with get_db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM leaderboard_entries WHERE user_id = %s ORDER BY total_score DESC LIMIT %s",
                    (user_id, limit)
                )
                return [dict(row) for row in cur.fetchall()]

    def get_rank(self, total_score: int) -> int:
        """Get rank for a given score."""
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT COUNT(*) FROM leaderboard_entries WHERE total_score > %s",
                    (total_score,)
                )
                count = cur.fetchone()[0]
                return count + 1

    # ==================== Game History ====================

    def save_game_history(self, history: Dict[str, Any]) -> Dict[str, Any]:
        """Save or update game history."""
        with get_db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Check if exists
                cur.execute(
                    "SELECT id FROM game_histories WHERE game_id = %s",
                    (history['gameId'],)
                )
                existing = cur.fetchone()

                if existing:
                    cur.execute("""
                        UPDATE game_histories
                        SET user_id = %s, player_name = %s, started_at = %s, ended_at = %s,
                            eras = %s, final_score = %s, ending_type = %s, blurb = %s
                        WHERE game_id = %s
                        RETURNING *
                    """, (
                        history['userId'], history.get('playerName'),
                        history.get('startedAt'), history.get('endedAt'),
                        json.dumps(history.get('eras', [])),
                        json.dumps(history.get('finalScore')),
                        history.get('endingType'), history.get('blurb'),
                        history['gameId']
                    ))
                else:
                    cur.execute("""
                        INSERT INTO game_histories
                        (game_id, user_id, player_name, started_at, ended_at, eras, final_score, ending_type, blurb)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING *
                    """, (
                        history['gameId'], history['userId'], history.get('playerName'),
                        history.get('startedAt'), history.get('endedAt'),
                        json.dumps(history.get('eras', [])),
                        json.dumps(history.get('finalScore')),
                        history.get('endingType'), history.get('blurb')
                    ))

                return dict(cur.fetchone())

    def get_game_history(self, game_id: str) -> Optional[Dict[str, Any]]:
        """Get game history by game ID."""
        with get_db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM game_histories WHERE game_id = %s LIMIT 1",
                    (game_id,)
                )
                result = cur.fetchone()
                return dict(result) if result else None

    def get_user_histories(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all game histories for a user."""
        with get_db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM game_histories WHERE user_id = %s ORDER BY ended_at DESC",
                    (user_id,)
                )
                return [dict(row) for row in cur.fetchall()]

    # ==================== Annals of Anachron (AoA) ====================

    def save_aoa_entry(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """Save an AoA entry."""
        with get_db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    INSERT INTO aoa_entries
                    (entry_id, user_id, game_id, player_name, character_name,
                     final_era, final_era_year, eras_visited, turns_survived,
                     ending_type, belonging_score, legacy_score, freedom_score, total_score,
                     key_npcs, defining_moments, wisdom_moments, items_used,
                     player_narrative, historian_narrative)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING *
                """, (
                    entry['entryId'], entry['userId'], entry.get('gameId'),
                    entry.get('playerName'), entry.get('characterName'),
                    entry.get('finalEra'), entry.get('finalEraYear'),
                    entry.get('erasVisited', 0), entry.get('turnsSurvived', 0),
                    entry.get('endingType'),
                    entry.get('belongingScore', 0), entry.get('legacyScore', 0),
                    entry.get('freedomScore', 0), entry.get('totalScore', 0),
                    json.dumps(entry.get('keyNpcs', [])),
                    json.dumps(entry.get('definingMoments', [])),
                    json.dumps(entry.get('wisdomMoments', [])),
                    json.dumps(entry.get('itemsUsed', [])),
                    entry.get('playerNarrative'), entry.get('historianNarrative')
                ))
                return dict(cur.fetchone())

    def get_aoa_entry(self, entry_id: str) -> Optional[Dict[str, Any]]:
        """Get an AoA entry by entry ID."""
        with get_db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM aoa_entries WHERE entry_id = %s LIMIT 1",
                    (entry_id,)
                )
                result = cur.fetchone()
                return dict(result) if result else None

    def get_user_aoa_entries(self, user_id: str, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        """Get AoA entries for a user."""
        with get_db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM aoa_entries WHERE user_id = %s ORDER BY created_at DESC LIMIT %s OFFSET %s",
                    (user_id, limit, offset)
                )
                return [dict(row) for row in cur.fetchall()]

    def get_recent_aoa_entries(self, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        """Get recent AoA entries."""
        with get_db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM aoa_entries ORDER BY created_at DESC LIMIT %s OFFSET %s",
                    (limit, offset)
                )
                return [dict(row) for row in cur.fetchall()]

    def count_user_aoa_entries(self, user_id: str) -> int:
        """Count AoA entries for a user."""
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT COUNT(*) FROM aoa_entries WHERE user_id = %s",
                    (user_id,)
                )
                return cur.fetchone()[0]

    def count_all_aoa_entries(self) -> int:
        """Count all AoA entries."""
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM aoa_entries")
                return cur.fetchone()[0]


# Global storage instance
storage = Storage()
