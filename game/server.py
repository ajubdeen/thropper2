#!/usr/bin/env python3
"""
Anachron V2 Game Server

Unified Python server that handles:
- Static file serving (React frontend)
- REST API endpoints (game saves, leaderboard, history)
- Socket.IO for real-time game communication

This replaces the Node.js/Express layer from V1.
"""

# Gevent monkey patching must happen first
from gevent import monkey
monkey.patch_all()

import os
import sys
import re
import logging
from datetime import timedelta
from flask import Flask, request, send_from_directory
from flask_socketio import SocketIO, emit as raw_emit

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def markdown_bold_to_ansi(text: str) -> str:
    """Convert markdown **bold** to ANSI bold escape codes for terminal display."""
    if not text:
        return text
    return re.sub(r'\*\*([^*]+)\*\*', r'\033[1m\1\033[0m', text)


def emit(event: str, data: dict):
    """Wrapper for emit that converts markdown bold to ANSI in narrative messages."""
    if event == 'message' and isinstance(data, dict):
        msg_type = data.get('type', '')
        if msg_type in ('narrative', 'narrative_chunk') and 'data' in data:
            msg_data = data['data']
            if isinstance(msg_data, dict) and 'text' in msg_data:
                msg_data['text'] = markdown_bold_to_ansi(msg_data['text'])
    raw_emit(event, data)


# Determine static files directory
STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static')

app = Flask(__name__, static_folder=STATIC_DIR, static_url_path='')
app.config['SECRET_KEY'] = os.environ.get('SESSION_SECRET') or os.urandom(24).hex()

# Session configuration - use Flask's secure signed cookie sessions
# Sessions are cryptographically signed with SECRET_KEY
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('RAILWAY_ENVIRONMENT') is not None  # HTTPS in production
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

# Register REST API routes
from routes import api
app.register_blueprint(api)

# Register auth routes and initialize OAuth
from auth import auth, init_oauth
app.register_blueprint(auth)
init_oauth(app)

# Register Narrative Lab routes (admin-only)
from lab_routes import lab
app.register_blueprint(lab)

socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode='gevent',
    ping_timeout=60,
    ping_interval=25
)


# ==================== Static File Serving ====================

@app.route('/')
def serve_index():
    """Serve the React app's index.html."""
    return send_from_directory(STATIC_DIR, 'index.html')


@app.route('/<path:path>')
def serve_static(path):
    """Serve static files, falling back to index.html for SPA routing."""
    # Try to serve the file directly
    file_path = os.path.join(STATIC_DIR, path)
    if os.path.isfile(file_path):
        return send_from_directory(STATIC_DIR, path)
    # Fall back to index.html for SPA routing
    return send_from_directory(STATIC_DIR, 'index.html')

from game_api import GameSession

sessions = {}


def get_session(sid):
    """Get session or emit error"""
    if sid not in sessions:
        emit('message', {'type': 'error', 'data': {'message': 'Session not found'}})
        return None
    return sessions[sid]


@socketio.on('connect')
def handle_connect():
    """Handle new client connection - wait for init event"""
    sid = request.sid
    logger.info(f"Client connected: {sid}")
    # Don't create session yet - wait for init event with user_id


@socketio.on('init')
def handle_init(data):
    """Initialize game session with user_id"""
    sid = request.sid
    user_id = data.get('user_id', 'anonymous')
    logger.info(f"Initializing session for {sid} with user_id: {user_id}")
    
    # Create session with user_id
    session = GameSession(user_id=user_id)
    sessions[sid] = {
        'session': session,
        'user_id': user_id
    }
    
    # Emit ready event - let frontend decide what to do
    emit('message', {'type': 'ready', 'data': {'user_id': user_id}})


@socketio.on('new_game')
def handle_new_game():
    """Start a new game"""
    sid = request.sid
    session_data = get_session(sid)
    if not session_data:
        return
    
    session = session_data['session']
    messages = session.start()
    for msg in messages:
        emit('message', msg)


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    sid = request.sid
    logger.info(f"Client disconnected: {sid}")
    
    if sid in sessions:
        del sessions[sid]


@socketio.on('set_name')
def handle_set_name(data):
    """Set player name and auto-select European region"""
    sid = request.sid
    session_data = get_session(sid)
    if not session_data:
        return
    
    session = session_data['session']
    name = data.get('name', 'Traveler')
    
    # Set name
    messages = session.set_name(name)
    for msg in messages:
        emit('message', msg)
    
    # Auto-select European region (skip region selection)
    messages = session.set_region('european')
    for msg in messages:
        emit('message', msg)


@socketio.on('set_region')
def handle_set_region(data):
    """Set region preference (fallback if frontend sends it)"""
    sid = request.sid
    session_data = get_session(sid)
    if not session_data:
        return
    
    session = session_data['session']
    region = data.get('region', 'european')
    messages = session.set_region(region)
    for msg in messages:
        emit('message', msg)


@socketio.on('enter_first_era')
def handle_enter_first_era():
    """Enter the first era"""
    sid = request.sid
    session_data = get_session(sid)
    if not session_data:
        return
    
    session = session_data['session']
    messages = session.enter_first_era()
    for msg in messages:
        emit('message', msg)


@socketio.on('choose')
def handle_choose(data):
    """Make a choice"""
    sid = request.sid
    session_data = get_session(sid)
    if not session_data:
        return
    
    session = session_data['session']
    choice = data.get('choice', 'A')
    messages = session.choose(choice)
    for msg in messages:
        emit('message', msg)


@socketio.on('continue_to_next_era')
def handle_continue_to_next_era():
    """Continue to next era after departure"""
    sid = request.sid
    session_data = get_session(sid)
    if not session_data:
        return
    
    session = session_data['session']
    messages = session.continue_to_next_era()
    for msg in messages:
        emit('message', msg)


@socketio.on('continue_to_score')
def handle_continue_to_score():
    """Continue to show final score after ending narrative"""
    sid = request.sid
    session_data = get_session(sid)
    if not session_data:
        return
    
    session = session_data['session']
    messages = session.continue_to_score()
    for msg in messages:
        emit('message', msg)


@socketio.on('get_state')
def handle_get_state():
    """Get current game state"""
    sid = request.sid
    session_data = get_session(sid)
    if not session_data:
        return
    
    session = session_data['session']
    state = session.get_state()
    emit('message', {'type': 'state', 'data': state})


@socketio.on('save')
def handle_save():
    """Save current game"""
    sid = request.sid
    session_data = get_session(sid)
    if not session_data:
        return
    
    session = session_data['session']
    messages = session.save()
    for msg in messages:
        emit('message', msg)


@socketio.on('load')
def handle_load(data):
    """Load a saved game"""
    sid = request.sid
    session_data = get_session(sid)
    if not session_data:
        return
    
    session = session_data['session']
    game_id = data.get('game_id')
    if not game_id:
        emit('message', {'type': 'error', 'data': {'message': 'No game_id provided'}})
        return
    
    messages = session.load(game_id)
    for msg in messages:
        emit('message', msg)


@socketio.on('resume')
def handle_resume():
    """Resume a loaded game"""
    sid = request.sid
    session_data = get_session(sid)
    if not session_data:
        return
    
    session = session_data['session']
    messages = session.resume()
    for msg in messages:
        emit('message', msg)


@socketio.on('list_saves')
def handle_list_saves():
    """List saved games for current user"""
    sid = request.sid
    session_data = get_session(sid)
    if not session_data:
        return
    
    session = session_data['session']
    messages = session.list_saves()
    for msg in messages:
        emit('message', msg)


@socketio.on('leaderboard')
def handle_leaderboard(data):
    """Get leaderboard"""
    sid = request.sid
    session_data = get_session(sid)
    if not session_data:
        return
    
    session = session_data['session']
    global_board = data.get('global', True) if data else True
    messages = session.leaderboard(global_board)
    for msg in messages:
        emit('message', msg)


@socketio.on('restart')
def handle_restart():
    """Restart the game"""
    sid = request.sid
    session_data = get_session(sid)
    if not session_data:
        emit('message', {'type': 'error', 'data': {'message': 'Session not found'}})
        return
    
    user_id = session_data['user_id']
    logger.info(f"Restart requested for {sid}")
    
    # Create new session with same user_id
    session = GameSession(user_id=user_id)
    sessions[sid] = {
        'session': session,
        'user_id': user_id
    }
    
    messages = session.start()
    for msg in messages:
        emit('message', msg)


if __name__ == '__main__':
    # Use PORT env var (Railway sets this), default to 5000
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"Starting Anachron V2 server on port {port}")
    logger.info(f"Static files directory: {STATIC_DIR}")

    socketio.run(app, host='0.0.0.0', port=port, debug=False, allow_unsafe_werkzeug=True)
