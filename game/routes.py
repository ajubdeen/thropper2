"""
REST API routes for Anachron V2.
Ported from Node.js/Express routes.ts.
"""

import logging
from datetime import datetime
from flask import Blueprint, request, jsonify

from db import storage

logger = logging.getLogger(__name__)

api = Blueprint('api', __name__, url_prefix='/api')


def parse_datetime(dt_str):
    """Parse ISO datetime string."""
    if not dt_str:
        return None
    try:
        return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
    except (ValueError, AttributeError):
        return None


def format_datetime(dt):
    """Format datetime to ISO string."""
    if not dt:
        return None
    return dt.isoformat() if hasattr(dt, 'isoformat') else str(dt)


# ==================== Health Check ====================

@api.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})


# ==================== Game Saves ====================

@api.route('/saves', methods=['POST'])
def save_game():
    try:
        data = request.json
        user_id = data.get('userId')
        game_id = data.get('gameId')
        state = data.get('state')

        if not user_id or not game_id or not state:
            return jsonify({'error': 'Missing required fields'}), 400

        result = storage.save_game(
            user_id=user_id,
            game_id=game_id,
            player_name=data.get('playerName'),
            current_era=data.get('currentEra'),
            phase=data.get('phase'),
            state=state,
            started_at=parse_datetime(state.get('started_at'))
        )
        return jsonify({'success': True, 'id': result['id']})
    except Exception as e:
        logger.error(f"Save game error: {e}")
        return jsonify({'error': 'Failed to save game'}), 500


@api.route('/saves/<user_id>/<game_id>', methods=['GET'])
def load_game(user_id, game_id):
    try:
        result = storage.load_game(user_id, game_id)
        if not result:
            return jsonify({'error': 'Game not found'}), 404
        return jsonify(result)
    except Exception as e:
        logger.error(f"Load game error: {e}")
        return jsonify({'error': 'Failed to load game'}), 500


@api.route('/saves/<user_id>/<game_id>', methods=['DELETE'])
def delete_game(user_id, game_id):
    try:
        storage.delete_game(user_id, game_id)
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Delete game error: {e}")
        return jsonify({'error': 'Failed to delete game'}), 500


@api.route('/saves/<user_id>', methods=['GET'])
def list_saves(user_id):
    try:
        games = storage.list_user_games(user_id)
        return jsonify([{
            'game_id': g['game_id'],
            'player_name': g.get('player_name'),
            'current_era': g.get('current_era'),
            'phase': g.get('phase'),
            'total_turns': g.get('state', {}).get('time_machine', {}).get('total_turns', 0) if isinstance(g.get('state'), dict) else 0,
            'saved_at': format_datetime(g.get('saved_at')),
            'started_at': format_datetime(g.get('started_at')),
        } for g in games])
    except Exception as e:
        logger.error(f"List games error: {e}")
        return jsonify({'error': 'Failed to list games'}), 500


# ==================== Leaderboard ====================

@api.route('/leaderboard', methods=['POST'])
def add_leaderboard():
    try:
        entry = request.json
        if not entry.get('userId') or not entry.get('playerName'):
            return jsonify({'error': 'Missing required fields'}), 400

        result = storage.add_leaderboard_entry(entry)
        rank = storage.get_rank(result.get('total_score', 0))
        return jsonify({'success': True, 'id': result['id'], 'rank': rank})
    except Exception as e:
        logger.error(f"Add leaderboard error: {e}")
        return jsonify({'error': 'Failed to add leaderboard entry'}), 500


@api.route('/leaderboard', methods=['GET'])
def get_leaderboard():
    try:
        limit = int(request.args.get('limit', 10))
        scores = storage.get_top_scores(limit)
        return jsonify([{
            'user_id': s['user_id'],
            'game_id': s.get('game_id'),
            'player_name': s['player_name'],
            'turns_survived': s.get('turns_survived', 0),
            'eras_visited': s.get('eras_visited', 0),
            'belonging_score': s.get('belonging_score', 0),
            'legacy_score': s.get('legacy_score', 0),
            'freedom_score': s.get('freedom_score', 0),
            'total': s.get('total_score', 0),
            'ending_type': s.get('ending_type'),
            'final_era': s.get('final_era'),
            'blurb': s.get('blurb'),
            'ending_narrative': s.get('ending_narrative'),
            'historian_narrative': s.get('historian_narrative'),
            'portrait_image_path': s.get('portrait_image_path'),
            'timestamp': format_datetime(s.get('created_at')),
        } for s in scores])
    except Exception as e:
        logger.error(f"Get leaderboard error: {e}")
        return jsonify({'error': 'Failed to get leaderboard'}), 500


@api.route('/leaderboard/<user_id>', methods=['GET'])
def get_user_leaderboard(user_id):
    try:
        limit = int(request.args.get('limit', 10))
        scores = storage.get_user_scores(user_id, limit)
        return jsonify([{
            'user_id': s['user_id'],
            'game_id': s.get('game_id'),
            'player_name': s['player_name'],
            'turns_survived': s.get('turns_survived', 0),
            'eras_visited': s.get('eras_visited', 0),
            'belonging_score': s.get('belonging_score', 0),
            'legacy_score': s.get('legacy_score', 0),
            'freedom_score': s.get('freedom_score', 0),
            'total': s.get('total_score', 0),
            'ending_type': s.get('ending_type'),
            'final_era': s.get('final_era'),
            'blurb': s.get('blurb'),
            'ending_narrative': s.get('ending_narrative'),
            'historian_narrative': s.get('historian_narrative'),
            'portrait_image_path': s.get('portrait_image_path'),
            'timestamp': format_datetime(s.get('created_at')),
        } for s in scores])
    except Exception as e:
        logger.error(f"Get user scores error: {e}")
        return jsonify({'error': 'Failed to get user scores'}), 500


# ==================== Game History ====================

@api.route('/history', methods=['POST'])
def save_history():
    try:
        history = request.json
        if not history.get('gameId') or not history.get('userId'):
            return jsonify({'error': 'Missing required fields'}), 400

        history['startedAt'] = parse_datetime(history.get('startedAt'))
        history['endedAt'] = parse_datetime(history.get('endedAt'))

        result = storage.save_game_history(history)
        return jsonify({'success': True, 'id': result['id']})
    except Exception as e:
        logger.error(f"Save history error: {e}")
        return jsonify({'error': 'Failed to save history'}), 500


@api.route('/history/<game_id>', methods=['GET'])
def get_history(game_id):
    try:
        result = storage.get_game_history(game_id)
        if not result:
            return jsonify({'error': 'History not found'}), 404
        return jsonify(result)
    except Exception as e:
        logger.error(f"Get history error: {e}")
        return jsonify({'error': 'Failed to get history'}), 500


@api.route('/histories/<user_id>', methods=['GET'])
def get_user_histories(user_id):
    try:
        histories = storage.get_user_histories(user_id)
        return jsonify(histories)
    except Exception as e:
        logger.error(f"Get user histories error: {e}")
        return jsonify({'error': 'Failed to get user histories'}), 500


# ==================== Annals of Anachron (AoA) ====================

@api.route('/aoa', methods=['POST'])
def save_aoa():
    try:
        entry = request.json
        if not entry.get('entryId') or not entry.get('userId'):
            return jsonify({'error': 'Missing required fields'}), 400

        result = storage.save_aoa_entry(entry)
        return jsonify({'success': True, 'id': result['id']})
    except Exception as e:
        logger.error(f"Save AoA entry error: {e}")
        return jsonify({'error': 'Failed to save AoA entry'}), 500


@api.route('/aoa/entry/<entry_id>', methods=['GET'])
def get_aoa_entry(entry_id):
    try:
        result = storage.get_aoa_entry(entry_id)
        if not result:
            return jsonify({'error': 'Entry not found'}), 404
        return jsonify({
            'entry_id': result['entry_id'],
            'user_id': result['user_id'],
            'game_id': result.get('game_id'),
            'player_name': result.get('player_name'),
            'character_name': result.get('character_name'),
            'final_era': result.get('final_era'),
            'final_era_year': result.get('final_era_year'),
            'eras_visited': result.get('eras_visited', 0),
            'turns_survived': result.get('turns_survived', 0),
            'ending_type': result.get('ending_type'),
            'belonging_score': result.get('belonging_score', 0),
            'legacy_score': result.get('legacy_score', 0),
            'freedom_score': result.get('freedom_score', 0),
            'total_score': result.get('total_score', 0),
            'key_npcs': result.get('key_npcs', []),
            'defining_moments': result.get('defining_moments', []),
            'wisdom_moments': result.get('wisdom_moments', []),
            'items_used': result.get('items_used', []),
            'player_narrative': result.get('player_narrative'),
            'historian_narrative': result.get('historian_narrative'),
            'created_at': format_datetime(result.get('created_at')),
        })
    except Exception as e:
        logger.error(f"Get AoA entry error: {e}")
        return jsonify({'error': 'Failed to get AoA entry'}), 500


@api.route('/aoa/user/<user_id>', methods=['GET'])
def get_user_aoa(user_id):
    try:
        limit = int(request.args.get('limit', 20))
        offset = int(request.args.get('offset', 0))

        entries = storage.get_user_aoa_entries(user_id, limit, offset)
        total = storage.count_user_aoa_entries(user_id)

        return jsonify({
            'entries': [{
                'entry_id': e['entry_id'],
                'user_id': e['user_id'],
                'game_id': e.get('game_id'),
                'player_name': e.get('player_name'),
                'character_name': e.get('character_name'),
                'final_era': e.get('final_era'),
                'final_era_year': e.get('final_era_year'),
                'eras_visited': e.get('eras_visited', 0),
                'turns_survived': e.get('turns_survived', 0),
                'ending_type': e.get('ending_type'),
                'belonging_score': e.get('belonging_score', 0),
                'legacy_score': e.get('legacy_score', 0),
                'freedom_score': e.get('freedom_score', 0),
                'total_score': e.get('total_score', 0),
                'key_npcs': e.get('key_npcs', []),
                'defining_moments': e.get('defining_moments', []),
                'wisdom_moments': e.get('wisdom_moments', []),
                'items_used': e.get('items_used', []),
                'player_narrative': e.get('player_narrative'),
                'historian_narrative': e.get('historian_narrative'),
                'created_at': format_datetime(e.get('created_at')),
            } for e in entries],
            'total': total,
            'limit': limit,
            'offset': offset,
            'has_more': offset + len(entries) < total,
        })
    except Exception as e:
        logger.error(f"Get user AoA entries error: {e}")
        return jsonify({'error': 'Failed to get user AoA entries'}), 500


@api.route('/aoa/recent', methods=['GET'])
def get_recent_aoa():
    try:
        limit = int(request.args.get('limit', 20))
        offset = int(request.args.get('offset', 0))

        entries = storage.get_recent_aoa_entries(limit, offset)
        total = storage.count_all_aoa_entries()

        return jsonify({
            'entries': [{
                'entry_id': e['entry_id'],
                'user_id': e['user_id'],
                'game_id': e.get('game_id'),
                'player_name': e.get('player_name'),
                'character_name': e.get('character_name'),
                'final_era': e.get('final_era'),
                'final_era_year': e.get('final_era_year'),
                'eras_visited': e.get('eras_visited', 0),
                'turns_survived': e.get('turns_survived', 0),
                'ending_type': e.get('ending_type'),
                'belonging_score': e.get('belonging_score', 0),
                'legacy_score': e.get('legacy_score', 0),
                'freedom_score': e.get('freedom_score', 0),
                'total_score': e.get('total_score', 0),
                'key_npcs': e.get('key_npcs', []),
                'defining_moments': e.get('defining_moments', []),
                'wisdom_moments': e.get('wisdom_moments', []),
                'items_used': e.get('items_used', []),
                'player_narrative': e.get('player_narrative'),
                'historian_narrative': e.get('historian_narrative'),
                'created_at': format_datetime(e.get('created_at')),
            } for e in entries],
            'total': total,
            'limit': limit,
            'offset': offset,
            'has_more': offset + len(entries) < total,
        })
    except Exception as e:
        logger.error(f"Get recent AoA entries error: {e}")
        return jsonify({'error': 'Failed to get recent AoA entries'}), 500


@api.route('/aoa/count', methods=['GET'])
def count_aoa():
    try:
        user_id = request.args.get('userId')
        if user_id:
            count = storage.count_user_aoa_entries(user_id)
        else:
            count = storage.count_all_aoa_entries()
        return jsonify({'count': count})
    except Exception as e:
        logger.error(f"Count AoA entries error: {e}")
        return jsonify({'error': 'Failed to count AoA entries'}), 500
