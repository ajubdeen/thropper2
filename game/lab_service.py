"""
Narrative Lab - Service Layer

Core business logic for the Narrative Lab. Handles snapshot creation,
narrative generation, response parsing, and batch comparison.
Reuses existing game modules — no duplication of game logic.
"""

import re
import time
import uuid
import random
import logging
from typing import Optional, List, Dict, Any

from db import get_db
from psycopg2.extras import RealDictCursor

import lab_db
from config import NARRATIVE_MODEL, PREMIUM_MODEL
from game_state import GameState, GameMode, GamePhase, RegionPreference
from eras import ERAS, get_era_by_id
from prompts import (
    get_system_prompt, get_arrival_prompt, get_turn_prompt,
    get_window_prompt, get_staying_ending_prompt, get_leaving_prompt,
    get_historian_narrative_prompt, get_quit_ending_prompt
)
from fulfillment import parse_anchor_adjustments, strip_anchor_tags
from event_parsing import (
    parse_character_name, parse_key_npcs, parse_wisdom_moment,
    strip_event_tags
)
from items import Inventory

logger = logging.getLogger(__name__)

# Try to import anthropic
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


# ==================== Snapshot Operations ====================

def create_snapshot_from_state(user_id: str, label: str, tags: List[str],
                                game_state_dict: Dict, conversation_history: List[Dict],
                                system_prompt: str = None,
                                available_choices: List[Dict] = None,
                                source: str = 'manual',
                                source_game_id: str = None) -> Dict[str, Any]:
    """Create a snapshot from a raw game state dict."""
    # Extract denormalized fields from game state
    era_data = game_state_dict.get('current_era', {})
    tm_data = game_state_dict.get('time_machine', {})
    ff_data = game_state_dict.get('fulfillment', {})

    snapshot_data = {
        'user_id': user_id,
        'label': label,
        'tags': tags,
        'game_state': game_state_dict,
        'conversation_history': conversation_history,
        'system_prompt': system_prompt,
        'era_id': era_data.get('era_id'),
        'era_name': era_data.get('era_name'),
        'era_year': era_data.get('era_year'),
        'era_location': era_data.get('era_location'),
        'total_turns': tm_data.get('total_turns', 0),
        'phase': game_state_dict.get('phase'),
        'player_name': game_state_dict.get('player_name'),
        'belonging_value': ff_data.get('belonging', {}).get('value', 0),
        'legacy_value': ff_data.get('legacy', {}).get('value', 0),
        'freedom_value': ff_data.get('freedom', {}).get('value', 0),
        'available_choices': available_choices or game_state_dict.get('last_choices', []),
        'source': source,
        'source_game_id': source_game_id,
    }

    return lab_db.save_snapshot(snapshot_data)


def create_snapshot_from_save(admin_user_id: str, save_user_id: str, game_id: str,
                               label: str, tags: List[str] = None) -> Dict[str, Any]:
    """Import a snapshot from any player's existing game save."""
    from db import storage

    save_data = storage.load_game(save_user_id, game_id)
    if not save_data:
        raise ValueError(f"Save not found: user={save_user_id}, game={game_id}")

    state_dict = save_data.get('state', save_data)
    if isinstance(state_dict, str):
        import json
        state_dict = json.loads(state_dict)

    # Reconstruct game state to generate system prompt
    game_state = GameState.from_save_dict(state_dict)
    era_id = state_dict.get('current_era', {}).get('era_id')
    system_prompt = None
    if era_id:
        era = get_era_by_id(era_id)
        if era:
            system_prompt = get_system_prompt(game_state, era)

    # Conversation history from state
    conversation_history = state_dict.get('conversation_history', [])

    return create_snapshot_from_state(
        user_id=admin_user_id,
        label=label,
        tags=tags or ['import'],
        game_state_dict=state_dict,
        conversation_history=conversation_history,
        system_prompt=system_prompt,
        source='import',
        source_game_id=game_id,
    )


def create_synthetic_snapshot(user_id: str, label: str, era_id: str,
                               total_turns: int = 5,
                               belonging: int = 30, legacy: int = 20, freedom: int = 25,
                               player_name: str = "Test Player",
                               mode: str = "mature",
                               region: str = "european",
                               tags: List[str] = None) -> Dict[str, Any]:
    """
    Create a synthetic snapshot by programmatically building a valid GameState.
    Useful for testing specific era/fulfillment combinations without playing.
    """
    era = get_era_by_id(era_id)
    if not era:
        raise ValueError(f"Unknown era: {era_id}")

    # Build a minimal valid game state
    state = GameState()
    state.player_name = player_name
    state.mode = GameMode(mode)
    state.region_preference = RegionPreference(region)
    state.phase = GamePhase.GAMEPLAY

    # Set fulfillment values
    state.fulfillment.belonging.value = belonging
    state.fulfillment.legacy.value = legacy
    state.fulfillment.freedom.value = freedom
    state.fulfillment.current_turn = total_turns

    # Set time machine state
    state.time_machine.total_turns = total_turns
    state.time_machine.turns_since_last_window = total_turns
    state.time_machine.eras_visited = [era_id]
    state.time_machine.display.current_year = era.get('year', 0)
    state.time_machine.display.current_location = era.get('location', '')
    state.time_machine.display.current_era_name = era.get('name', '')

    # Set current era
    from game_state import EraState
    state.current_era = EraState(
        era_id=era_id,
        era_name=era.get('name', ''),
        era_year=era.get('year', 0),
        era_location=era.get('location', ''),
        turn_count=total_turns,
    )

    # Create inventory
    state.inventory = Inventory.create_starting()

    # Generate system prompt
    system_prompt = get_system_prompt(state, era)

    state_dict = state.to_save_dict()

    return create_snapshot_from_state(
        user_id=user_id,
        label=label,
        tags=tags or ['synthetic', era_id],
        game_state_dict=state_dict,
        conversation_history=[],
        system_prompt=system_prompt,
        source='synthetic',
    )


def list_all_saves() -> List[Dict[str, Any]]:
    """List all players' saved games for import browsing."""
    with get_db() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT gs.user_id, gs.game_id, gs.player_name, gs.current_era,
                       gs.phase, gs.saved_at,
                       u.email, u.first_name, u.last_name
                FROM game_saves gs
                LEFT JOIN users u ON gs.user_id = u.id
                ORDER BY gs.saved_at DESC
                LIMIT 100
            """)
            return [dict(r) for r in cur.fetchall()]


# ==================== Generation ====================

def _parse_choices_from_response(response: str) -> List[Dict]:
    """Extract [A]/[B]/[C] choices from AI response. Replicates GameAPI._parse_choices logic."""
    clean = strip_anchor_tags(response)
    clean = strip_event_tags(clean)

    choices = []
    for line in clean.split('\n'):
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


def generate_narrative(user_id: str, snapshot_id: str, choice_id: str,
                        model: str = None,
                        system_prompt_override: str = None,
                        turn_prompt_override: str = None,
                        dice_roll: int = None,
                        temperature: float = 1.0,
                        max_tokens: int = 1500,
                        comparison_group: str = None,
                        comparison_label: str = None) -> Dict[str, Any]:
    """
    Generate a single narrative from a snapshot.
    Returns the saved generation record with parsed results.
    """
    if not ANTHROPIC_AVAILABLE:
        raise RuntimeError("Anthropic API not available")

    # 1. Load snapshot
    snapshot = lab_db.get_snapshot(snapshot_id)
    if not snapshot:
        raise ValueError(f"Snapshot not found: {snapshot_id}")

    # 2. Reconstruct game state
    game_state = GameState.from_save_dict(snapshot['game_state'])

    # 3. Get era
    era_id = snapshot.get('era_id')
    era = get_era_by_id(era_id) if era_id else None

    # 4. Build system prompt
    if system_prompt_override:
        system_prompt = system_prompt_override
    elif snapshot.get('system_prompt'):
        system_prompt = snapshot['system_prompt']
    elif era:
        system_prompt = get_system_prompt(game_state, era)
    else:
        raise ValueError("No system prompt available and no era to generate one")

    # 5. Build turn prompt
    roll = dice_roll if dice_roll is not None else random.randint(1, 20)
    if turn_prompt_override:
        turn_prompt = turn_prompt_override
    else:
        # Find the choice text from available choices
        choice_text = choice_id
        for c in snapshot.get('available_choices', []):
            if c.get('id', '').upper() == choice_id.upper():
                choice_text = c.get('text', choice_id)
                break
        turn_prompt = get_turn_prompt(game_state, choice_text, roll, era)

    # 6. Build messages (conversation history + new turn prompt)
    messages = list(snapshot.get('conversation_history', []))
    messages.append({"role": "user", "content": turn_prompt})

    # 7. Call Claude API directly
    client = anthropic.Anthropic()
    model_id = model or NARRATIVE_MODEL

    start_time = time.time()
    try:
        response = client.messages.create(
            model=model_id,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=messages
        )
        raw_response = response.content[0].text
    except Exception as e:
        logger.error(f"API call failed: {e}")
        raise

    elapsed_ms = int((time.time() - start_time) * 1000)

    # 8. Parse response
    anchor_deltas = parse_anchor_adjustments(raw_response)
    npcs = parse_key_npcs(raw_response)
    wisdom = parse_wisdom_moment(raw_response)
    character_name = parse_character_name(raw_response)
    parsed_choices = _parse_choices_from_response(raw_response)

    # Clean narrative text
    narrative_text = strip_anchor_tags(raw_response)
    narrative_text = strip_event_tags(narrative_text)

    # Find choice text
    choice_text_for_db = choice_id
    for c in snapshot.get('available_choices', []):
        if c.get('id', '').upper() == choice_id.upper():
            choice_text_for_db = c.get('text', choice_id)
            break

    # 9. Store generation
    generation_data = {
        'user_id': user_id,
        'snapshot_id': snapshot_id,
        'choice_id': choice_id.upper(),
        'choice_text': choice_text_for_db,
        'model': model_id,
        'system_prompt': system_prompt,
        'turn_prompt': turn_prompt,
        'dice_roll': roll,
        'temperature': temperature,
        'max_tokens': max_tokens,
        'raw_response': raw_response,
        'narrative_text': narrative_text,
        'anchor_deltas': anchor_deltas,
        'parsed_npcs': npcs,
        'parsed_wisdom': wisdom,
        'parsed_character_name': character_name,
        'parsed_choices': parsed_choices,
        'comparison_group': comparison_group,
        'comparison_label': comparison_label,
        'generation_time_ms': elapsed_ms,
    }

    return lab_db.save_generation(generation_data)


def generate_batch(user_id: str, snapshot_id: str, choice_id: str,
                    variants: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generate multiple narrative variants for side-by-side comparison.
    Each variant can have different model, prompts, dice_roll, temperature, etc.
    Returns comparison_group ID and all generations.
    """
    comparison_group = str(uuid.uuid4())
    generations = []

    for i, variant in enumerate(variants):
        label = variant.get('label', f"Variant {chr(65 + i)}")
        gen = generate_narrative(
            user_id=user_id,
            snapshot_id=snapshot_id,
            choice_id=choice_id,
            model=variant.get('model'),
            system_prompt_override=variant.get('system_prompt'),
            turn_prompt_override=variant.get('turn_prompt'),
            dice_roll=variant.get('dice_roll'),
            temperature=variant.get('temperature', 1.0),
            max_tokens=variant.get('max_tokens', 1500),
            comparison_group=comparison_group,
            comparison_label=label,
        )
        generations.append(gen)

    return {
        'comparison_group': comparison_group,
        'generations': generations,
    }


# ==================== Prompt Rendering ====================

def render_default_prompt(prompt_type: str, era_id: str = None,
                           game_state_dict: Dict = None,
                           choice: str = None, roll: int = None) -> Dict[str, str]:
    """
    Render a default prompt template with actual game context.
    Returns {'template': str, 'rendered': str}.
    """
    game_state = None
    era = None

    if game_state_dict:
        game_state = GameState.from_save_dict(game_state_dict)
    if era_id:
        era = get_era_by_id(era_id)

    rendered = ""
    try:
        if prompt_type == 'system' and game_state and era:
            rendered = get_system_prompt(game_state, era)
        elif prompt_type == 'arrival' and game_state and era:
            rendered = get_arrival_prompt(game_state, era)
        elif prompt_type == 'turn' and game_state:
            rendered = get_turn_prompt(game_state, choice or "Continue exploring", roll or 10, era)
        elif prompt_type == 'window' and game_state:
            rendered = get_window_prompt(game_state, choice, roll)
        elif prompt_type == 'staying_ending' and game_state and era:
            rendered = get_staying_ending_prompt(game_state, era)
    except Exception as e:
        logger.error(f"Error rendering prompt: {e}")
        rendered = f"Error rendering: {e}"

    return {
        'prompt_type': prompt_type,
        'rendered': rendered,
    }


def preview_prompts(snapshot_id: str, choice_id: str, dice_roll: int = 10) -> Dict[str, str]:
    """
    Preview the actual system_prompt and turn_prompt that would be sent to Claude
    for a given snapshot, choice, and dice roll.
    """
    snapshot = lab_db.get_snapshot(snapshot_id)
    if not snapshot:
        raise ValueError(f"Snapshot not found: {snapshot_id}")

    game_state = GameState.from_save_dict(snapshot['game_state'])
    era_id = snapshot.get('era_id')
    era = get_era_by_id(era_id) if era_id else None

    # System prompt (same fallback as generate_narrative)
    if snapshot.get('system_prompt'):
        system_prompt = snapshot['system_prompt']
    elif era:
        system_prompt = get_system_prompt(game_state, era)
    else:
        system_prompt = ""

    # Turn prompt
    choice_text = choice_id
    for c in snapshot.get('available_choices', []):
        if c.get('id', '').upper() == choice_id.upper():
            choice_text = c.get('text', choice_id)
            break
    turn_prompt = get_turn_prompt(game_state, choice_text, dice_roll, era) if era else ""

    return {
        'system_prompt': system_prompt,
        'turn_prompt': turn_prompt,
    }


# ==================== Utility ====================

def get_all_eras() -> List[Dict[str, Any]]:
    """Return simplified era list for the lab UI."""
    return [{
        'id': era['id'],
        'name': era['name'],
        'year': era.get('year'),
        'location': era.get('location'),
    } for era in ERAS]


def get_available_models() -> List[Dict[str, str]]:
    """Return list of available Claude models."""
    return [
        {'id': 'claude-opus-4-6', 'label': 'Opus 4.6', 'description': 'Most capable, slowest'},
        {'id': 'claude-sonnet-4-5-20250929', 'label': 'Sonnet 4.5', 'description': 'Fast, excellent quality'},
        {'id': 'claude-haiku-4-5-20251001', 'label': 'Haiku 4.5', 'description': 'Fastest, good quality'},
    ]


def get_default_config() -> Dict[str, Any]:
    """Return default generation configuration."""
    return {
        'default_model': NARRATIVE_MODEL,
        'premium_model': PREMIUM_MODEL,
        'default_temperature': 1.0,
        'default_max_tokens': 1500,
        'dice_range': {'min': 1, 'max': 20},
    }
