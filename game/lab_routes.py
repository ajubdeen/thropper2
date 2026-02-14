"""
Narrative Lab - REST API Routes

All endpoints under /api/lab/. Admin-only access.
"""

import logging
from functools import wraps
from flask import Blueprint, request, jsonify, session

import lab_db
import lab_service
import lab_quickplay

logger = logging.getLogger(__name__)

lab = Blueprint('lab', __name__, url_prefix='/api/lab')

ADMIN_EMAIL = 'aju.bdeen@gmail.com'


def require_admin(f):
    """Decorator: require admin email in session."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('email') != ADMIN_EMAIL:
            return jsonify({'error': 'Forbidden'}), 403
        return f(*args, **kwargs)
    return decorated


def format_datetime(dt):
    if not dt:
        return None
    return dt.isoformat() if hasattr(dt, 'isoformat') else str(dt)


# ==================== Snapshots ====================

@lab.route('/snapshots', methods=['POST'])
@require_admin
def create_snapshot():
    """Create snapshot from raw game state dict."""
    try:
        data = request.json
        result = lab_service.create_snapshot_from_state(
            user_id=session['user_id'],
            label=data.get('label', 'Untitled'),
            tags=data.get('tags', []),
            game_state_dict=data['game_state'],
            conversation_history=data.get('conversation_history', []),
            system_prompt=data.get('system_prompt'),
            available_choices=data.get('available_choices'),
            source='manual',
        )
        return jsonify(result), 201
    except KeyError as e:
        return jsonify({'error': f'Missing required field: {e}'}), 400
    except Exception as e:
        logger.error(f"Create snapshot error: {e}")
        return jsonify({'error': str(e)}), 500


@lab.route('/snapshots/from-save', methods=['POST'])
@require_admin
def create_snapshot_from_save():
    """Import snapshot from any player's existing game save."""
    try:
        data = request.json
        result = lab_service.create_snapshot_from_save(
            admin_user_id=session['user_id'],
            save_user_id=data['user_id'],
            game_id=data['game_id'],
            label=data.get('label', 'Imported save'),
            tags=data.get('tags'),
        )
        return jsonify(result), 201
    except KeyError as e:
        return jsonify({'error': f'Missing required field: {e}'}), 400
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Import snapshot error: {e}")
        return jsonify({'error': str(e)}), 500


@lab.route('/snapshots/synthetic', methods=['POST'])
@require_admin
def create_synthetic_snapshot():
    """Create synthetic snapshot by specifying era and parameters."""
    try:
        data = request.json
        result = lab_service.create_synthetic_snapshot(
            user_id=session['user_id'],
            label=data.get('label', 'Synthetic'),
            era_id=data['era_id'],
            total_turns=data.get('total_turns', 5),
            belonging=data.get('belonging', 30),
            legacy=data.get('legacy', 20),
            freedom=data.get('freedom', 25),
            player_name=data.get('player_name', 'Test Player'),
            mode=data.get('mode', 'mature'),
            region=data.get('region', 'european'),
            tags=data.get('tags'),
        )
        return jsonify(result), 201
    except KeyError as e:
        return jsonify({'error': f'Missing required field: {e}'}), 400
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Create synthetic snapshot error: {e}")
        return jsonify({'error': str(e)}), 500


@lab.route('/snapshots', methods=['GET'])
@require_admin
def list_snapshots():
    """List snapshots with optional filtering."""
    try:
        rows, total = lab_db.list_snapshots(
            user_id=session['user_id'],
            era_id=request.args.get('era_id'),
            tags=request.args.getlist('tags') or None,
            search=request.args.get('search'),
            limit=int(request.args.get('limit', 20)),
            offset=int(request.args.get('offset', 0)),
        )
        return jsonify({
            'snapshots': rows,
            'total': total,
        })
    except Exception as e:
        logger.error(f"List snapshots error: {e}")
        return jsonify({'error': str(e)}), 500


@lab.route('/snapshots/<snapshot_id>', methods=['GET'])
@require_admin
def get_snapshot(snapshot_id):
    """Get full snapshot by ID."""
    try:
        snapshot = lab_db.get_snapshot(snapshot_id)
        if not snapshot:
            return jsonify({'error': 'Snapshot not found'}), 404
        return jsonify(snapshot)
    except Exception as e:
        logger.error(f"Get snapshot error: {e}")
        return jsonify({'error': str(e)}), 500


@lab.route('/snapshots/<snapshot_id>', methods=['PATCH'])
@require_admin
def update_snapshot(snapshot_id):
    """Update snapshot label/tags."""
    try:
        data = request.json
        result = lab_db.update_snapshot(snapshot_id, data)
        if not result:
            return jsonify({'error': 'Snapshot not found'}), 404
        return jsonify(result)
    except Exception as e:
        logger.error(f"Update snapshot error: {e}")
        return jsonify({'error': str(e)}), 500


@lab.route('/snapshots/<snapshot_id>', methods=['DELETE'])
@require_admin
def delete_snapshot(snapshot_id):
    """Delete snapshot (cascades to generations)."""
    try:
        deleted = lab_db.delete_snapshot(snapshot_id)
        if not deleted:
            return jsonify({'error': 'Snapshot not found'}), 404
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Delete snapshot error: {e}")
        return jsonify({'error': str(e)}), 500


@lab.route('/saves', methods=['GET'])
@require_admin
def list_all_saves():
    """List all players' saved games for import browsing."""
    try:
        saves = lab_service.list_all_saves()
        return jsonify(saves)
    except Exception as e:
        logger.error(f"List saves error: {e}")
        return jsonify({'error': str(e)}), 500


# ==================== Generation ====================

@lab.route('/generate', methods=['POST'])
@require_admin
def generate_narrative():
    """Generate a single narrative from a snapshot."""
    try:
        data = request.json
        result = lab_service.generate_narrative(
            user_id=session['user_id'],
            snapshot_id=data['snapshot_id'],
            choice_id=data['choice_id'],
            model=data.get('model'),
            system_prompt_override=data.get('system_prompt'),
            turn_prompt_override=data.get('turn_prompt'),
            dice_roll=data.get('dice_roll'),
            temperature=data.get('temperature', 1.0),
            max_tokens=data.get('max_tokens', 1500),
            comparison_group=data.get('comparison_group'),
            comparison_label=data.get('comparison_label'),
        )
        return jsonify(result), 201
    except KeyError as e:
        return jsonify({'error': f'Missing required field: {e}'}), 400
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except RuntimeError as e:
        return jsonify({'error': str(e)}), 503
    except Exception as e:
        logger.error(f"Generate narrative error: {e}")
        return jsonify({'error': str(e)}), 500


@lab.route('/generate/batch', methods=['POST'])
@require_admin
def generate_batch():
    """Generate multiple narrative variants for comparison."""
    try:
        data = request.json
        result = lab_service.generate_batch(
            user_id=session['user_id'],
            snapshot_id=data['snapshot_id'],
            choice_id=data['choice_id'],
            variants=data['variants'],
        )
        return jsonify(result), 201
    except KeyError as e:
        return jsonify({'error': f'Missing required field: {e}'}), 400
    except Exception as e:
        logger.error(f"Generate batch error: {e}")
        return jsonify({'error': str(e)}), 500


@lab.route('/generations', methods=['GET'])
@require_admin
def list_generations():
    """List generation history with filtering."""
    try:
        rating = request.args.get('rating')
        rows, total = lab_db.list_generations(
            user_id=session['user_id'],
            snapshot_id=request.args.get('snapshot_id'),
            model=request.args.get('model'),
            rating=int(rating) if rating is not None else None,
            comparison_group=request.args.get('comparison_group'),
            limit=int(request.args.get('limit', 20)),
            offset=int(request.args.get('offset', 0)),
        )
        return jsonify({
            'generations': rows,
            'total': total,
        })
    except Exception as e:
        logger.error(f"List generations error: {e}")
        return jsonify({'error': str(e)}), 500


@lab.route('/generations/<generation_id>', methods=['GET'])
@require_admin
def get_generation(generation_id):
    """Get a single generation by ID."""
    try:
        gen = lab_db.get_generation(generation_id)
        if not gen:
            return jsonify({'error': 'Generation not found'}), 404
        return jsonify(gen)
    except Exception as e:
        logger.error(f"Get generation error: {e}")
        return jsonify({'error': str(e)}), 500


@lab.route('/generations/<generation_id>', methods=['PATCH'])
@require_admin
def update_generation(generation_id):
    """Update generation rating/notes."""
    try:
        data = request.json
        result = lab_db.update_generation(generation_id, data)
        if not result:
            return jsonify({'error': 'Generation not found'}), 404
        return jsonify(result)
    except Exception as e:
        logger.error(f"Update generation error: {e}")
        return jsonify({'error': str(e)}), 500


@lab.route('/generations/<generation_id>', methods=['DELETE'])
@require_admin
def delete_generation(generation_id):
    """Delete a generation."""
    try:
        deleted = lab_db.delete_generation(generation_id)
        if not deleted:
            return jsonify({'error': 'Generation not found'}), 404
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Delete generation error: {e}")
        return jsonify({'error': str(e)}), 500


# ==================== Prompt Variants ====================

@lab.route('/prompts', methods=['POST'])
@require_admin
def create_prompt_variant():
    """Create a prompt variant."""
    try:
        data = request.json
        data['user_id'] = session['user_id']
        result = lab_db.save_prompt_variant(data)
        return jsonify(result), 201
    except KeyError as e:
        return jsonify({'error': f'Missing required field: {e}'}), 400
    except Exception as e:
        logger.error(f"Create prompt variant error: {e}")
        return jsonify({'error': str(e)}), 500


@lab.route('/prompts', methods=['GET'])
@require_admin
def list_prompt_variants():
    """List prompt variants, optionally filtered by type."""
    try:
        variants = lab_db.list_prompt_variants(
            user_id=session['user_id'],
            prompt_type=request.args.get('prompt_type'),
        )
        return jsonify(variants)
    except Exception as e:
        logger.error(f"List prompt variants error: {e}")
        return jsonify({'error': str(e)}), 500


@lab.route('/prompts/<variant_id>', methods=['GET'])
@require_admin
def get_prompt_variant(variant_id):
    """Get a single prompt variant."""
    try:
        variant = lab_db.get_prompt_variant(variant_id)
        if not variant:
            return jsonify({'error': 'Variant not found'}), 404
        return jsonify(variant)
    except Exception as e:
        logger.error(f"Get prompt variant error: {e}")
        return jsonify({'error': str(e)}), 500


@lab.route('/prompts/<variant_id>', methods=['PUT'])
@require_admin
def update_prompt_variant(variant_id):
    """Update a prompt variant."""
    try:
        data = request.json
        result = lab_db.update_prompt_variant(variant_id, data)
        if not result:
            return jsonify({'error': 'Variant not found'}), 404
        return jsonify(result)
    except Exception as e:
        logger.error(f"Update prompt variant error: {e}")
        return jsonify({'error': str(e)}), 500


@lab.route('/prompts/<variant_id>', methods=['DELETE'])
@require_admin
def delete_prompt_variant(variant_id):
    """Delete a prompt variant."""
    try:
        deleted = lab_db.delete_prompt_variant(variant_id)
        if not deleted:
            return jsonify({'error': 'Variant not found'}), 404
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Delete prompt variant error: {e}")
        return jsonify({'error': str(e)}), 500


@lab.route('/prompts/default/<prompt_type>', methods=['GET'])
@require_admin
def get_default_prompt(prompt_type):
    """Render default prompt template with optional game context."""
    try:
        result = lab_service.render_default_prompt(
            prompt_type=prompt_type,
            era_id=request.args.get('era_id'),
            game_state_dict=request.args.get('game_state'),  # JSON string from query
            choice=request.args.get('choice'),
            roll=int(request.args.get('roll')) if request.args.get('roll') else None,
        )
        return jsonify(result)
    except Exception as e:
        logger.error(f"Get default prompt error: {e}")
        return jsonify({'error': str(e)}), 500


# ==================== Utility ====================

@lab.route('/eras', methods=['GET'])
@require_admin
def list_eras():
    """List all available eras."""
    return jsonify(lab_service.get_all_eras())


@lab.route('/models', methods=['GET'])
@require_admin
def list_models():
    """List available Claude models."""
    return jsonify(lab_service.get_available_models())


@lab.route('/config', methods=['GET'])
@require_admin
def get_config():
    """Get default generation configuration."""
    return jsonify(lab_service.get_default_config())


# ==================== Quick Play ====================

@lab.route('/quickplay/start', methods=['POST'])
@require_admin
def quickplay_start():
    """Start a new quick play session."""
    try:
        data = request.json or {}
        result = lab_quickplay.create_session(
            user_id=session['user_id'],
            player_name=data.get('player_name', 'Lab Tester'),
            region=data.get('region', 'european'),
        )
        return jsonify(result), 201
    except Exception as e:
        logger.error(f"Quick play start error: {e}")
        return jsonify({'error': str(e)}), 500


@lab.route('/quickplay/<session_id>/enter-era', methods=['POST'])
@require_admin
def quickplay_enter_era(session_id):
    """Enter the first era in a quick play session."""
    try:
        qp = lab_quickplay.get_session(session_id)
        if not qp:
            return jsonify({'error': 'Session not found'}), 404
        result = qp.enter_era()
        return jsonify(result)
    except Exception as e:
        logger.error(f"Quick play enter era error: {e}")
        return jsonify({'error': str(e)}), 500


@lab.route('/quickplay/<session_id>/choose', methods=['POST'])
@require_admin
def quickplay_choose(session_id):
    """Make a choice in a quick play session."""
    try:
        qp = lab_quickplay.get_session(session_id)
        if not qp:
            return jsonify({'error': 'Session not found'}), 404
        data = request.json
        result = qp.choose(data['choice'])
        return jsonify(result)
    except KeyError as e:
        return jsonify({'error': f'Missing required field: {e}'}), 400
    except Exception as e:
        logger.error(f"Quick play choose error: {e}")
        return jsonify({'error': str(e)}), 500


@lab.route('/quickplay/<session_id>/continue', methods=['POST'])
@require_admin
def quickplay_continue(session_id):
    """Continue to next era after departure."""
    try:
        qp = lab_quickplay.get_session(session_id)
        if not qp:
            return jsonify({'error': 'Session not found'}), 404
        result = qp.continue_to_next_era()
        return jsonify(result)
    except Exception as e:
        logger.error(f"Quick play continue error: {e}")
        return jsonify({'error': str(e)}), 500


@lab.route('/quickplay/<session_id>/state', methods=['GET'])
@require_admin
def quickplay_state(session_id):
    """Get current state of a quick play session."""
    try:
        qp = lab_quickplay.get_session(session_id)
        if not qp:
            return jsonify({'error': 'Session not found'}), 404
        return jsonify(qp.get_state())
    except Exception as e:
        logger.error(f"Quick play state error: {e}")
        return jsonify({'error': str(e)}), 500
