"""
Authentication module for Anachron V2.

Provides a simple session-based authentication system.
For MVP, uses anonymous sessions with generated user IDs.
Can be extended to support OAuth providers later.
"""

import os
import uuid
import logging
from functools import wraps
from flask import Blueprint, request, jsonify, session, redirect

logger = logging.getLogger(__name__)

auth = Blueprint('auth', __name__, url_prefix='/api')


def get_current_user():
    """Get the current user from session, or None if not authenticated."""
    user_id = session.get('user_id')
    if not user_id:
        return None

    return {
        'id': user_id,
        'email': session.get('email'),
        'firstName': session.get('firstName'),
        'lastName': session.get('lastName'),
        'profileImageUrl': session.get('profileImageUrl'),
        'isAnonymous': session.get('isAnonymous', True),
    }


def require_auth(f):
    """Decorator to require authentication for a route."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({'message': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated_function


@auth.route('/auth/user', methods=['GET'])
def get_user():
    """Get current authenticated user."""
    user = get_current_user()
    if not user:
        return jsonify({'message': 'Unauthorized'}), 401
    return jsonify(user)


@auth.route('/login', methods=['GET'])
def login():
    """
    Login endpoint.
    For MVP, creates an anonymous session with a generated user ID.
    The frontend will redirect here, and we redirect back to home.
    """
    if not session.get('user_id'):
        # Generate anonymous user
        user_id = f"anon_{uuid.uuid4().hex[:12]}"
        session['user_id'] = user_id
        session['isAnonymous'] = True
        session['firstName'] = 'Traveler'
        logger.info(f"Created anonymous session for user {user_id}")

    return redirect('/')


@auth.route('/logout', methods=['GET'])
def logout():
    """Logout endpoint - clears the session."""
    user_id = session.get('user_id')
    session.clear()
    logger.info(f"User {user_id} logged out")
    return redirect('/')


@auth.route('/auth/session', methods=['POST'])
def create_session():
    """
    Create a new session via API (for programmatic use).
    Accepts optional user info, otherwise creates anonymous session.
    """
    data = request.json or {}

    user_id = data.get('userId') or f"anon_{uuid.uuid4().hex[:12]}"
    session['user_id'] = user_id
    session['email'] = data.get('email')
    session['firstName'] = data.get('firstName', 'Traveler')
    session['lastName'] = data.get('lastName')
    session['isAnonymous'] = not data.get('email')

    logger.info(f"Created session for user {user_id}")

    return jsonify({
        'success': True,
        'user': get_current_user()
    })
