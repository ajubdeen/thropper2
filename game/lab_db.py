"""
Narrative Lab - Database Operations

CRUD operations for lab_snapshots, lab_generations, and lab_prompt_variants tables.
Follows the same pattern as db.py (get_db(), RealDictCursor).
"""

import json
import logging
from typing import Optional, List, Dict, Any, Tuple

from psycopg2.extras import RealDictCursor, Json

from db import get_db

logger = logging.getLogger(__name__)


# ==================== Snapshots ====================

def save_snapshot(data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a lab snapshot. Returns the created row."""
    with get_db() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                INSERT INTO lab_snapshots
                (user_id, label, tags, game_state, conversation_history, system_prompt,
                 era_id, era_name, era_year, era_location, total_turns, phase, player_name,
                 belonging_value, legacy_value, freedom_value, available_choices,
                 source, source_game_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *
            """, (
                data['user_id'], data['label'], Json(data.get('tags', [])),
                Json(data['game_state']), Json(data.get('conversation_history', [])),
                data.get('system_prompt'),
                data.get('era_id'), data.get('era_name'), data.get('era_year'),
                data.get('era_location'), data.get('total_turns', 0),
                data.get('phase'), data.get('player_name'),
                data.get('belonging_value', 0), data.get('legacy_value', 0),
                data.get('freedom_value', 0),
                Json(data.get('available_choices', [])),
                data.get('source', 'manual'), data.get('source_game_id')
            ))
            return dict(cur.fetchone())


def get_snapshot(snapshot_id: str) -> Optional[Dict[str, Any]]:
    """Get a single snapshot by ID."""
    with get_db() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM lab_snapshots WHERE id = %s", (snapshot_id,))
            row = cur.fetchone()
            return dict(row) if row else None


def list_snapshots(user_id: str, era_id: str = None, tags: List[str] = None,
                   search: str = None, limit: int = 20, offset: int = 0) -> Tuple[List[Dict], int]:
    """List snapshots with filtering. Returns (rows, total_count)."""
    conditions = ["user_id = %s"]
    params: list = [user_id]

    if era_id:
        conditions.append("era_id = %s")
        params.append(era_id)

    if tags:
        conditions.append("tags @> %s")
        params.append(Json(tags))

    if search:
        conditions.append("(label ILIKE %s OR era_name ILIKE %s OR player_name ILIKE %s)")
        like = f"%{search}%"
        params.extend([like, like, like])

    where = " AND ".join(conditions)

    with get_db() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(f"SELECT COUNT(*) FROM lab_snapshots WHERE {where}", params)
            total = cur.fetchone()['count']

            cur.execute(
                f"""SELECT id, user_id, label, tags, era_id, era_name, era_year, era_location,
                    total_turns, phase, player_name, belonging_value, legacy_value, freedom_value,
                    available_choices, source, source_game_id, created_at
                    FROM lab_snapshots WHERE {where}
                    ORDER BY created_at DESC LIMIT %s OFFSET %s""",
                params + [limit, offset]
            )
            rows = [dict(r) for r in cur.fetchall()]
            return rows, total


def update_snapshot(snapshot_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Update snapshot label/tags."""
    sets = []
    params = []
    if 'label' in updates:
        sets.append("label = %s")
        params.append(updates['label'])
    if 'tags' in updates:
        sets.append("tags = %s")
        params.append(Json(updates['tags']))

    if not sets:
        return get_snapshot(snapshot_id)

    params.append(snapshot_id)
    with get_db() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                f"UPDATE lab_snapshots SET {', '.join(sets)} WHERE id = %s RETURNING *",
                params
            )
            row = cur.fetchone()
            return dict(row) if row else None


def delete_snapshot(snapshot_id: str) -> bool:
    """Delete a snapshot (cascades to generations)."""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM lab_snapshots WHERE id = %s", (snapshot_id,))
            return cur.rowcount > 0


# ==================== Generations ====================

def save_generation(data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a lab generation. Returns the created row."""
    with get_db() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                INSERT INTO lab_generations
                (user_id, snapshot_id, choice_id, choice_text, model,
                 system_prompt, turn_prompt, dice_roll, temperature, max_tokens,
                 raw_response, narrative_text, anchor_deltas, parsed_npcs,
                 parsed_wisdom, parsed_character_name, parsed_choices,
                 comparison_group, comparison_label, generation_time_ms)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *
            """, (
                data['user_id'], data['snapshot_id'], data['choice_id'],
                data.get('choice_text'), data['model'],
                data['system_prompt'], data['turn_prompt'],
                data.get('dice_roll'), data.get('temperature', 1.0),
                data.get('max_tokens', 1500),
                data['raw_response'], data.get('narrative_text'),
                Json(data.get('anchor_deltas')), Json(data.get('parsed_npcs', [])),
                data.get('parsed_wisdom'), data.get('parsed_character_name'),
                Json(data.get('parsed_choices', [])),
                data.get('comparison_group'), data.get('comparison_label'),
                data.get('generation_time_ms')
            ))
            return dict(cur.fetchone())


def get_generation(generation_id: str) -> Optional[Dict[str, Any]]:
    """Get a single generation by ID."""
    with get_db() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM lab_generations WHERE id = %s", (generation_id,))
            row = cur.fetchone()
            return dict(row) if row else None


def list_generations(user_id: str, snapshot_id: str = None, model: str = None,
                     rating: int = None, comparison_group: str = None,
                     limit: int = 20, offset: int = 0) -> Tuple[List[Dict], int]:
    """List generations with filtering. Returns (rows, total_count)."""
    conditions = ["user_id = %s"]
    params: list = [user_id]

    if snapshot_id:
        conditions.append("snapshot_id = %s")
        params.append(snapshot_id)
    if model:
        conditions.append("model = %s")
        params.append(model)
    if rating is not None:
        conditions.append("rating = %s")
        params.append(rating)
    if comparison_group:
        conditions.append("comparison_group = %s")
        params.append(comparison_group)

    where = " AND ".join(conditions)

    with get_db() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(f"SELECT COUNT(*) FROM lab_generations WHERE {where}", params)
            total = cur.fetchone()['count']

            cur.execute(
                f"SELECT * FROM lab_generations WHERE {where} ORDER BY created_at DESC LIMIT %s OFFSET %s",
                params + [limit, offset]
            )
            rows = [dict(r) for r in cur.fetchall()]
            return rows, total


def update_generation(generation_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Update generation rating/notes."""
    sets = []
    params = []
    if 'rating' in updates:
        sets.append("rating = %s")
        params.append(updates['rating'])
    if 'notes' in updates:
        sets.append("notes = %s")
        params.append(updates['notes'])

    if not sets:
        return get_generation(generation_id)

    params.append(generation_id)
    with get_db() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                f"UPDATE lab_generations SET {', '.join(sets)} WHERE id = %s RETURNING *",
                params
            )
            row = cur.fetchone()
            return dict(row) if row else None


def delete_generation(generation_id: str) -> bool:
    """Delete a generation."""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM lab_generations WHERE id = %s", (generation_id,))
            return cur.rowcount > 0


# ==================== Prompt Variants ====================

def save_prompt_variant(data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a prompt variant. Returns the created row."""
    with get_db() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                INSERT INTO lab_prompt_variants
                (user_id, name, description, prompt_type, template, is_default)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING *
            """, (
                data['user_id'], data['name'], data.get('description'),
                data['prompt_type'], data['template'],
                data.get('is_default', False)
            ))
            return dict(cur.fetchone())


def get_prompt_variant(variant_id: str) -> Optional[Dict[str, Any]]:
    """Get a single prompt variant by ID."""
    with get_db() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM lab_prompt_variants WHERE id = %s", (variant_id,))
            row = cur.fetchone()
            return dict(row) if row else None


def list_prompt_variants(user_id: str, prompt_type: str = None) -> List[Dict[str, Any]]:
    """List prompt variants, optionally filtered by type."""
    with get_db() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if prompt_type:
                cur.execute(
                    "SELECT * FROM lab_prompt_variants WHERE user_id = %s AND prompt_type = %s ORDER BY created_at DESC",
                    (user_id, prompt_type)
                )
            else:
                cur.execute(
                    "SELECT * FROM lab_prompt_variants WHERE user_id = %s ORDER BY prompt_type, created_at DESC",
                    (user_id,)
                )
            return [dict(r) for r in cur.fetchall()]


def update_prompt_variant(variant_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Update a prompt variant."""
    sets = ["updated_at = NOW()"]
    params = []

    for field in ('name', 'description', 'template', 'is_default'):
        if field in updates:
            sets.append(f"{field} = %s")
            params.append(updates[field])

    if len(sets) == 1:  # only updated_at
        return get_prompt_variant(variant_id)

    params.append(variant_id)
    with get_db() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                f"UPDATE lab_prompt_variants SET {', '.join(sets)} WHERE id = %s RETURNING *",
                params
            )
            row = cur.fetchone()
            return dict(row) if row else None


def delete_prompt_variant(variant_id: str) -> bool:
    """Delete a prompt variant."""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM lab_prompt_variants WHERE id = %s", (variant_id,))
            return cur.rowcount > 0
