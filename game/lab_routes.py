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
import prompt_overrides

logger = logging.getLogger(__name__)

lab = Blueprint('lab', __name__, url_prefix='/api/lab')

ADMIN_EMAIL = 'aju.bdeen@gmail.com'


def require_admin(f):
    """Decorator: require admin email in session.
    In dev (no GOOGLE_CLIENT_ID), skips auth entirely — lab is local-only anyway.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        import os
        if not os.environ.get('GOOGLE_CLIENT_ID'):
            return f(*args, **kwargs)  # Dev mode: no auth required
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


@lab.route('/snapshots/<snapshot_id>/prompts', methods=['GET'])
@require_admin
def preview_snapshot_prompts(snapshot_id):
    """Preview the system and turn prompts that would be used for this snapshot."""
    try:
        choice_id = request.args.get('choice_id', 'A')
        dice_roll = int(request.args.get('dice_roll', 10))
        result = lab_service.preview_prompts(snapshot_id, choice_id, dice_roll)
        return jsonify(result)
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Preview prompts error: {e}")
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
    """Create a prompt variant with auto-versioning and diff computation."""
    try:
        data = request.json
        user_id = session['user_id']
        data['user_id'] = user_id
        prompt_type = data.get('prompt_type', '')

        # Auto-assign version number
        version_number = lab_db.get_next_version_number(user_id, prompt_type)
        data['version_number'] = version_number

        # Compute diffs
        previous = lab_db.get_previous_version(user_id, prompt_type)
        diffs = prompt_overrides.compute_diffs(
            prompt_type,
            data['template'],
            previous['template'] if previous else None
        )
        data['diff_vs_baseline'] = diffs['diff_vs_baseline']
        data['diff_vs_previous'] = diffs['diff_vs_previous']
        data['change_summary'] = diffs['change_summary']

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

        # Recompute diffs when template changes
        if 'template' in data:
            existing = lab_db.get_prompt_variant(variant_id)
            if existing:
                previous = lab_db.get_previous_version(
                    existing['user_id'], existing['prompt_type'],
                    before_version=existing['version_number']
                )
                diffs = prompt_overrides.compute_diffs(
                    existing['prompt_type'],
                    data['template'],
                    previous['template'] if previous else None
                )
                data['diff_vs_baseline'] = diffs['diff_vs_baseline']
                data['diff_vs_previous'] = diffs['diff_vs_previous']
                data['change_summary'] = diffs['change_summary']

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


# ==================== Prompt Version Control ====================

@lab.route('/prompts/<variant_id>/push', methods=['POST'])
@require_admin
def push_prompt_live(variant_id):
    """Push a prompt variant to the live game engine."""
    try:
        variant = lab_db.push_variant_live(variant_id)
        if not variant:
            return jsonify({'error': 'Variant not found'}), 404

        # Update in-memory cache
        prompt_overrides.push_live(variant['prompt_type'], variant['template'])

        return jsonify({
            'success': True,
            'variant': variant,
            'message': f"Prompt '{variant['name']}' is now live for {variant['prompt_type']}"
        })
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Push prompt live error: {e}")
        return jsonify({'error': str(e)}), 500


@lab.route('/prompts/revert/<prompt_type>', methods=['POST'])
@require_admin
def revert_prompt(prompt_type):
    """Revert a prompt type to its baseline (default) template."""
    try:
        reverted = lab_db.revert_prompt_type(prompt_type)

        # Update in-memory cache
        prompt_overrides.revert_to_baseline(prompt_type)

        return jsonify({
            'success': True,
            'reverted': reverted,
            'message': f"Prompt '{prompt_type}' reverted to baseline"
        })
    except Exception as e:
        logger.error(f"Revert prompt error: {e}")
        return jsonify({'error': str(e)}), 500


@lab.route('/prompts/live', methods=['GET'])
@require_admin
def get_live_status():
    """Get live status for all prompt types."""
    try:
        status = prompt_overrides.get_live_status()

        # Also get the live variant details
        details = {}
        for pt, is_live in status.items():
            if is_live:
                variant = lab_db.get_live_variant(pt)
                details[pt] = {
                    'is_live': True,
                    'variant_id': variant['id'] if variant else None,
                    'variant_name': variant['name'] if variant else None,
                    'version_number': variant.get('version_number') if variant else None,
                }
            else:
                details[pt] = {'is_live': False}

        return jsonify(details)
    except Exception as e:
        logger.error(f"Get live status error: {e}")
        return jsonify({'error': str(e)}), 500


@lab.route('/prompts/versions/<prompt_type>', methods=['GET'])
@require_admin
def get_version_history(prompt_type):
    """Get version history for a prompt type."""
    try:
        versions = lab_db.get_version_history(session['user_id'], prompt_type)
        return jsonify(versions)
    except Exception as e:
        logger.error(f"Get version history error: {e}")
        return jsonify({'error': str(e)}), 500


@lab.route('/prompts/baseline/<prompt_type>', methods=['GET'])
@require_admin
def get_baseline_prompt(prompt_type):
    """Get the baseline template text for a prompt type."""
    try:
        baseline = prompt_overrides.get_baseline_template(prompt_type)
        if not baseline:
            return jsonify({'error': f'No baseline found for {prompt_type}'}), 404
        return jsonify({
            'prompt_type': prompt_type,
            'template': baseline,
        })
    except Exception as e:
        logger.error(f"Get baseline prompt error: {e}")
        return jsonify({'error': str(e)}), 500


@lab.route('/prompts/seed-baselines', methods=['POST'])
@require_admin
def seed_baselines():
    """Seed baseline entries for all prompt types (version 0, is_default=True)."""
    try:
        from prompts import BASELINE_TEMPLATES
        user_id = session['user_id']
        created = []

        for prompt_type, template in BASELINE_TEMPLATES.items():
            # Check if baseline already exists
            existing = lab_db.get_baseline_variant(user_id, prompt_type)
            if existing:
                continue

            data = {
                'user_id': user_id,
                'name': f'Baseline ({prompt_type})',
                'description': f'Original production {prompt_type} prompt template',
                'prompt_type': prompt_type,
                'template': template,
                'is_default': True,
                'version_number': 0,
                'change_summary': 'Original baseline',
            }
            result = lab_db.save_prompt_variant(data)
            created.append(prompt_type)

        return jsonify({
            'success': True,
            'created': created,
            'message': f"Seeded baselines for: {', '.join(created)}" if created else "All baselines already exist"
        })
    except Exception as e:
        logger.error(f"Seed baselines error: {e}")
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

def _resolve_variant_id(variant_id: str) -> str:
    """Resolve a prompt variant ID to its template text, or None."""
    if not variant_id:
        return None
    variant = lab_db.get_prompt_variant(variant_id)
    return variant['template'] if variant else None


def _resolve_variant_meta(variant_id: str) -> tuple:
    """Resolve a prompt variant ID to (template, id, name). Returns (None, None, None) if not found."""
    if not variant_id:
        return None, None, None
    variant = lab_db.get_prompt_variant(variant_id)
    if not variant:
        return None, None, None
    return variant['template'], variant['id'], variant['name']


def _apply_per_turn_params(qp, data: dict):
    """Apply per-turn overridable params (model, temperature, dice_roll) to session."""
    if not data:
        return
    updates = {}
    if 'model' in data:
        updates['model_override'] = data['model']
    if 'temperature' in data:
        updates['temperature'] = data['temperature']
    if 'dice_roll' in data:
        updates['dice_roll'] = data['dice_roll']
    if updates:
        qp.update_params(**updates)


@lab.route('/quickplay/start', methods=['POST'])
@require_admin
def quickplay_start():
    """Start a new quick play session."""
    try:
        data = request.json or {}

        # Resolve prompt variant IDs to template text + metadata
        sys_tpl, sys_id, sys_name = _resolve_variant_meta(data.get('system_prompt_variant_id'))
        turn_tpl, turn_id, turn_name = _resolve_variant_meta(data.get('turn_prompt_variant_id'))
        arr_tpl, arr_id, arr_name = _resolve_variant_meta(data.get('arrival_prompt_variant_id'))
        win_tpl, win_id, win_name = _resolve_variant_meta(data.get('window_prompt_variant_id'))

        result = lab_quickplay.create_session(
            user_id=session['user_id'],
            player_name=data.get('player_name', 'Lab Tester'),
            region=data.get('region', 'european'),
            system_prompt_override=sys_tpl,
            turn_prompt_override=turn_tpl,
            arrival_prompt_override=arr_tpl,
            window_prompt_override=win_tpl,
            model_override=data.get('model'),
            temperature=data.get('temperature'),
            dice_roll=data.get('dice_roll'),
            system_prompt_variant_id=sys_id,
            system_prompt_variant_name=sys_name,
            turn_prompt_variant_id=turn_id,
            turn_prompt_variant_name=turn_name,
            arrival_prompt_variant_id=arr_id,
            arrival_prompt_variant_name=arr_name,
            window_prompt_variant_id=win_id,
            window_prompt_variant_name=win_name,
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
        _apply_per_turn_params(qp, request.json)
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
        _apply_per_turn_params(qp, data)
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
        _apply_per_turn_params(qp, request.json)
        result = qp.continue_to_next_era()
        return jsonify(result)
    except Exception as e:
        logger.error(f"Quick play continue error: {e}")
        return jsonify({'error': str(e)}), 500


@lab.route('/quickplay/<session_id>/update-params', methods=['PATCH'])
@require_admin
def quickplay_update_params(session_id):
    """Update session parameters between turns."""
    try:
        qp = lab_quickplay.get_session(session_id)
        if not qp:
            return jsonify({'error': 'Session not found'}), 404
        data = request.json or {}

        # Resolve any new prompt variant IDs
        updates = {}
        for prompt_type in ['system', 'turn', 'arrival', 'window']:
            key = f'{prompt_type}_prompt_variant_id'
            if key in data:
                template, vid, vname = _resolve_variant_meta(data[key])
                updates[f'{prompt_type}_prompt_override'] = template or ''
                updates[f'{prompt_type}_prompt_variant_id'] = vid
                updates[f'{prompt_type}_prompt_variant_name'] = vname

        if 'model' in data:
            updates['model_override'] = data['model']
        if 'temperature' in data:
            updates['temperature'] = data['temperature']
        if 'dice_roll' in data:
            updates['dice_roll'] = data['dice_roll']

        qp.update_params(**updates)
        return jsonify({'ok': True})
    except Exception as e:
        logger.error(f"Quick play update params error: {e}")
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


# ==================== Quick Play History ====================

@lab.route('/quickplay/sessions', methods=['GET'])
@require_admin
def quickplay_sessions():
    """List all quick play sessions."""
    try:
        limit = request.args.get('limit', 20, type=int)
        offset = request.args.get('offset', 0, type=int)
        sessions, total = lab_db.list_quickplay_sessions(
            session['user_id'], limit=limit, offset=offset
        )
        for s in sessions:
            if 'created_at' in s:
                s['created_at'] = format_datetime(s['created_at'])
        return jsonify({'sessions': sessions, 'total': total})
    except Exception as e:
        logger.error(f"List sessions error: {e}")
        return jsonify({'error': str(e)}), 500


@lab.route('/quickplay/history', methods=['GET'])
@require_admin
def quickplay_history():
    """List quick play turns with filtering."""
    try:
        filters = {
            'session_id': request.args.get('session_id'),
            'era_id': request.args.get('era_id'),
            'model': request.args.get('model'),
            'region': request.args.get('region'),
            'system_prompt_variant_id': request.args.get('system_prompt_variant_id'),
            'turn_prompt_variant_id': request.args.get('turn_prompt_variant_id'),
            'arrival_prompt_variant_id': request.args.get('arrival_prompt_variant_id'),
            'window_prompt_variant_id': request.args.get('window_prompt_variant_id'),
            'date_from': request.args.get('date_from'),
            'date_to': request.args.get('date_to'),
        }
        # Remove None values
        filters = {k: v for k, v in filters.items() if v is not None}

        limit = request.args.get('limit', 20, type=int)
        offset = request.args.get('offset', 0, type=int)

        turns, total = lab_db.list_quickplay_turns(
            session['user_id'], limit=limit, offset=offset, **filters
        )
        for t in turns:
            if 'created_at' in t:
                t['created_at'] = format_datetime(t['created_at'])

        # Get filter options
        filter_options = lab_db.get_quickplay_filter_options(session['user_id'])

        return jsonify({
            'turns': turns,
            'total': total,
            'filters': filter_options,
        })
    except Exception as e:
        logger.error(f"Quick play history error: {e}")
        return jsonify({'error': str(e)}), 500


@lab.route('/quickplay/turns/<turn_id>', methods=['GET'])
@require_admin
def quickplay_turn_detail(turn_id):
    """Get a single quick play turn with full details."""
    try:
        turn = lab_db.get_quickplay_turn(turn_id)
        if not turn:
            return jsonify({'error': 'Turn not found'}), 404
        if 'created_at' in turn:
            turn['created_at'] = format_datetime(turn['created_at'])
        return jsonify(turn)
    except Exception as e:
        logger.error(f"Quick play turn detail error: {e}")
        return jsonify({'error': str(e)}), 500


# =============================================================================
# Image Lab
# =============================================================================

@lab.route('/narratives', methods=['GET'])
@require_admin
def list_narratives():
    """List leaderboard entries (joined with AoA) for the Image Lab narrative dropdown."""
    try:
        from db import get_db
        from psycopg2.extras import RealDictCursor
        with get_db() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT l.player_name, l.final_era, l.total_score, l.blurb,
                           a.entry_id, a.player_narrative
                    FROM leaderboard_entries l
                    JOIN aoa_entries a ON l.game_id = a.game_id
                    ORDER BY l.total_score DESC
                    LIMIT 200
                """)
                rows = cur.fetchall()
        result = []
        for r in rows:
            result.append({
                'entry_id': r['entry_id'],
                'player_name': r.get('player_name', 'Unknown'),
                'final_era': r.get('final_era', ''),
                'total_score': r.get('total_score', 0),
                'blurb': r.get('blurb', ''),
                'player_narrative': (r.get('player_narrative') or '')[:400],
            })
        return jsonify({'narratives': result})
    except Exception as e:
        logger.error(f"List narratives error: {e}")
        return jsonify({'error': str(e)}), 500


@lab.route('/extract-scene', methods=['POST'])
@require_admin
def extract_scene_route():
    """Run Claude scene extraction + prompt assembly for an AoA entry."""
    data = request.get_json()
    entry_id = (data.get('entry_id') or '').strip()
    if not entry_id:
        return jsonify({'error': 'entry_id is required'}), 400
    try:
        from db import storage
        from portrait_generator import extract_scene, build_image_prompt
        aoa_data = storage.get_aoa_entry(entry_id)
        if not aoa_data:
            return jsonify({'error': 'Narrative not found'}), 404
        scene = extract_scene(aoa_data)
        if not scene:
            return jsonify({'error': 'Scene extraction failed'}), 503
        prompt_text = build_image_prompt(scene)
        return jsonify({'prompt_text': prompt_text})
    except Exception as e:
        logger.error(f"Extract scene error: {e}")
        return jsonify({'error': str(e)}), 500


@lab.route('/generate-image', methods=['POST'])
@require_admin
def generate_image():
    """Generate an image from a prompt template + optional narrative entry.
    If entry_id is provided, scene is extracted and appended to the template
    in the background — the user only sees/edits the template portion.
    """
    data = request.get_json()
    prompt = (data.get('prompt') or '').strip()
    if not prompt:
        return jsonify({'error': 'prompt is required'}), 400

    model = data.get('model', 'gpt-image-1.5')
    quality = data.get('quality', 'medium')
    size = data.get('size', '1536x1024')
    entry_id = (data.get('entry_id') or '').strip()

    # If a narrative is selected, extract scene and append dynamic blocks to the template
    if entry_id:
        try:
            from db import storage
            from portrait_generator import extract_scene, build_scene_blocks, IMAGE_PROMPT_FOOTER
            aoa_data = storage.get_aoa_entry(entry_id)
            if aoa_data:
                scene = extract_scene(aoa_data)
                if scene:
                    scene_blocks = build_scene_blocks(scene)
                    prompt = f"{prompt}\n{scene_blocks}\n\n{IMAGE_PROMPT_FOOTER}"
        except Exception as e:
            logger.warning(f"Scene extraction failed, using raw prompt: {e}")

    try:
        from portrait_generator import generate_image_from_prompt
        path = generate_image_from_prompt(prompt, model=model, quality=quality, size=size)
        if not path:
            return jsonify({'error': 'Image generation failed — check OPENAI_API_KEY'}), 503
        return jsonify({'image_path': path, 'prompt': prompt}), 201
    except Exception as e:
        logger.error(f"Image lab generation error: {e}")
        return jsonify({'error': str(e)}), 500


@lab.route('/push-image-prompt', methods=['POST'])
@require_admin
def push_image_prompt():
    """Save the current image prompt template as the live production style block."""
    data = request.get_json()
    template = (data.get('template') or '').strip()
    if not template:
        return jsonify({'error': 'template is required'}), 400

    try:
        from db import get_db
        import psycopg2.extras
        user_id = session.get('user_id', 'dev')
        with get_db() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    "SELECT COALESCE(MAX(version_number), 0) + 1 AS next_v FROM lab_prompt_variants WHERE prompt_type = 'image_style'"
                )
                version = cur.fetchone()['next_v']
                # Unmark any existing live image_style variant
                cur.execute(
                    "UPDATE lab_prompt_variants SET is_live = false WHERE prompt_type = 'image_style' AND is_live = true"
                )
                cur.execute(
                    """INSERT INTO lab_prompt_variants
                       (user_id, name, prompt_type, template, is_live, version_number)
                       VALUES (%s, %s, 'image_style', %s, true, %s)
                       RETURNING id""",
                    (user_id, f'image_style_v{version}', template, version)
                )
                new_id = cur.fetchone()['id']
        logger.info(f"Image prompt pushed to production: v{version} ({new_id})")
        return jsonify({'success': True, 'version': version, 'id': new_id})
    except Exception as e:
        logger.error(f"Push image prompt error: {e}")
        return jsonify({'error': str(e)}), 500


@lab.route('/generate-aoa-narrative', methods=['POST'])
def generate_aoa_narrative():
    """Generate and save historian + ending narratives for an AoA entry that has none.
    Auth: SESSION_SECRET token in X-Admin-Token header OR admin session."""
    import os
    token = request.headers.get('X-Admin-Token', '')
    secret = os.environ.get('SESSION_SECRET', '')
    if not token or not secret or token != secret:
        if not os.environ.get('GOOGLE_CLIENT_ID') or session.get('email') == ADMIN_EMAIL:
            pass
        else:
            return jsonify({'error': 'Forbidden'}), 403

    data = request.get_json()
    entry_id = (data.get('entry_id') or '').strip()
    if not entry_id:
        return jsonify({'error': 'entry_id is required'}), 400

    try:
        from db import get_db, storage
        import anthropic, json as _json

        aoa = storage.get_aoa_entry(entry_id)
        if not aoa:
            return jsonify({'error': 'AoA entry not found'}), 404

        client = anthropic.Anthropic()

        # Build a prompt for the ending narrative (player perspective)
        npcs = aoa.get('key_npcs', [])
        if isinstance(npcs, str):
            npcs = _json.loads(npcs)
        items = aoa.get('items_used', [])
        if isinstance(items, str):
            items = _json.loads(items)

        ending_prompt = f"""You are writing the ending narrative for a time-travel adventure game.

The player's character is {aoa.get('character_name', 'the traveler')} in {aoa.get('final_era', 'an unknown era')} ({aoa.get('final_era_year', '')}).
Player name: {aoa.get('player_name', 'the player')}
Ending type: {aoa.get('ending_type', 'balanced')}
Belonging: {aoa.get('belonging_score', 0)}, Legacy: {aoa.get('legacy_score', 0)}, Freedom: {aoa.get('freedom_score', 0)}
Key NPCs: {', '.join(npcs) if npcs else 'none recorded'}
Items used: {', '.join(items) if items else 'none'}
Turns survived: {aoa.get('turns_survived', 0)}

Write a rich, evocative 3-paragraph ending narrative in second person ("you") describing:
1. The moment the time device goes dark and the character accepts this era as home
2. The life they built in the decades that followed, weaving in the key NPCs
3. A brief historical footnote about the era

Keep it under 500 words. Write only the narrative, no titles or headers."""

        ending_response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1000,
            messages=[{"role": "user", "content": ending_prompt}]
        )
        player_narrative = ending_response.content[0].text.strip()

        # Generate historian narrative (third-person chronicle with a title heading)
        historian_prompt = f"""Write a short historian's chronicle entry about {aoa.get('character_name', 'the traveler')}, a time-traveler who chose to stay in {aoa.get('final_era', 'an unknown era')} ({aoa.get('final_era_year', '')}).

Player: {aoa.get('player_name', '')}, ending: {aoa.get('ending_type', 'balanced')}
Key NPCs: {', '.join(npcs) if npcs else 'none'}

Format:
- First line must be a markdown heading: # [Poetic name for the character] (e.g. "# Eirik of the Longhouse" or "# The Healer of Jutland")
- Then 2-3 short paragraphs in third person, like a historical record
- Tone: dignified, literary, slightly archaic
- Under 200 words total"""

        historian_response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=400,
            messages=[{"role": "user", "content": historian_prompt}]
        )
        historian_narrative = historian_response.content[0].text.strip()

        # Save both to DB
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE aoa_entries SET player_narrative = %s, historian_narrative = %s WHERE entry_id = %s",
                    (player_narrative, historian_narrative, entry_id)
                )
                # Also update the leaderboard ending_narrative
                game_id = aoa.get('game_id')
                if game_id:
                    cur.execute(
                        "UPDATE leaderboard_entries SET ending_narrative = %s WHERE game_id = %s",
                        (player_narrative, game_id)
                    )

        logger.info(f"Narratives generated for AoA entry {entry_id}")
        return jsonify({'success': True, 'historian_narrative': historian_narrative[:120] + '...'})

    except Exception as e:
        logger.error(f"Generate AoA narrative error: {e}")
        return jsonify({'error': str(e)}), 500


@lab.route('/regenerate-portrait', methods=['POST'])
def regenerate_portrait():
    """Regenerate portrait for an AoA entry. Runs synchronously — expect 30-60s.
    Auth: requires admin session OR SESSION_SECRET token in X-Admin-Token header."""
    import os
    token = request.headers.get('X-Admin-Token', '')
    secret = os.environ.get('SESSION_SECRET', '')
    if not token or not secret or token != secret:
        # Fall back to session check
        if not os.environ.get('GOOGLE_CLIENT_ID') or session.get('email') == ADMIN_EMAIL:
            pass  # dev mode or valid session
        else:
            return jsonify({'error': 'Forbidden'}), 403

    data = request.get_json()
    entry_id = (data.get('entry_id') or '').strip()
    if not entry_id:
        return jsonify({'error': 'entry_id is required'}), 400
    try:
        from portrait_generator import generate_portrait
        path = generate_portrait(entry_id)
        if not path:
            return jsonify({'error': 'Portrait generation failed — check OPENAI_API_KEY'}), 503
        logger.info(f"Portrait regenerated for {entry_id}: {path}")
        return jsonify({'success': True, 'portrait_image_path': path})
    except Exception as e:
        logger.error(f"Regenerate portrait error: {e}")
        return jsonify({'error': str(e)}), 500
