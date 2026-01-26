"""
Authentication module for Anachron V2.

Implements Google OAuth authentication using Authlib.
Replaces the original Replit Auth/OIDC with Google as the OAuth provider.
"""

import os
import logging
from functools import wraps
from flask import Blueprint, request, jsonify, session, redirect, url_for, current_app
from authlib.integrations.flask_client import OAuth

from db import storage

logger = logging.getLogger(__name__)

auth = Blueprint('auth', __name__, url_prefix='/api')

# OAuth will be initialized when the blueprint is registered with the app
oauth = OAuth()


def init_oauth(app):
    """Initialize OAuth with the Flask app."""
    oauth.init_app(app)

    # Register Google OAuth provider
    oauth.register(
        name='google',
        client_id=os.environ.get('GOOGLE_CLIENT_ID'),
        client_secret=os.environ.get('GOOGLE_CLIENT_SECRET'),
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={
            'scope': 'openid email profile'
        }
    )


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
    Redirects to Google OAuth consent screen.
    """
    # Check if OAuth is configured
    google_client_id = os.environ.get('GOOGLE_CLIENT_ID')
    if not google_client_id:
        logger.warning("Google OAuth not configured, using demo mode")
        # Fallback to demo user for development
        session['user_id'] = 'demo_user'
        session['email'] = 'demo@anachron.game'
        session['firstName'] = 'Demo'
        session['lastName'] = 'User'
        session.permanent = True
        return redirect('/')

    # Build the callback URL
    # Force HTTPS in production (Railway terminates SSL at proxy)
    redirect_uri = url_for('auth.callback', _external=True)
    if redirect_uri.startswith('http://') and 'railway.app' in redirect_uri:
        redirect_uri = redirect_uri.replace('http://', 'https://', 1)
    logger.info(f"Starting OAuth flow, redirect_uri: {redirect_uri}")

    return oauth.google.authorize_redirect(redirect_uri)


@auth.route('/auth/callback', methods=['GET'])
def callback():
    """
    OAuth callback endpoint.
    Handles the redirect from Google after authentication.
    """
    try:
        # Exchange the authorization code for tokens
        token = oauth.google.authorize_access_token()

        # Get user info from the ID token
        user_info = token.get('userinfo')
        if not user_info:
            # Fallback: fetch from userinfo endpoint
            user_info = oauth.google.userinfo()

        logger.info(f"OAuth callback successful for user: {user_info.get('email')}")

        # Prepare user data for database
        user_data = {
            'id': user_info['sub'],  # Google's unique user ID
            'email': user_info.get('email'),
            'first_name': user_info.get('given_name'),
            'last_name': user_info.get('family_name'),
            'profile_image_url': user_info.get('picture')
        }

        # Upsert user in database
        storage.upsert_user(user_data)

        # Create Flask session
        session['user_id'] = user_data['id']
        session['email'] = user_data['email']
        session['firstName'] = user_data['first_name']
        session['lastName'] = user_data['last_name']
        session['profileImageUrl'] = user_data['profile_image_url']
        session.permanent = True  # Use permanent session (7-day TTL)

        logger.info(f"Created session for user {user_data['id']}")

        return redirect('/')

    except Exception as e:
        logger.error(f"OAuth callback error: {e}")
        return redirect('/?error=auth_failed')


@auth.route('/logout', methods=['GET'])
def logout():
    """Logout endpoint - clears the session."""
    user_id = session.get('user_id')
    session.clear()
    logger.info(f"User {user_id} logged out")
    return redirect('/')
