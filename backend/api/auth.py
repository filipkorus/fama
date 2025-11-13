"""
Authentication API endpoints
Provides user registration and login functionality with JWT tokens
"""

from flask import Blueprint, request, jsonify, current_app, make_response
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity,
    get_jwt
)
from datetime import datetime, timedelta
from database import db
from models import User, RefreshToken, UserDevice
import re
import base64
from user_agents import parse

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')


def generate_device_name_from_user_agent(user_agent_string):
    """
    Generate a device name from User-Agent string
    Examples: "Chrome 120 on Windows 10", "Safari 17 on iPhone", "Firefox 119 on Ubuntu"
    """
    if not user_agent_string:
        return "Unknown Device"

    try:
        user_agent = parse(user_agent_string)

        # Browser info
        browser = f"{user_agent.browser.family} {user_agent.browser.version_string.split('.')[0]}" if user_agent.browser.family else "Unknown Browser"

        # OS info
        os_name = user_agent.os.family if user_agent.os.family else "Unknown OS"
        os_version = user_agent.os.version_string.split('.')[0] if user_agent.os.version_string else ""

        # Device type (mobile, tablet, pc)
        if user_agent.is_mobile:
            device_type = user_agent.device.family if user_agent.device.family != "Other" else "Mobile"
        elif user_agent.is_tablet:
            device_type = "Tablet"
        else:
            device_type = ""

        # Construct name
        if device_type and device_type not in os_name:
            if os_version:
                return f"{browser} on {device_type} ({os_name} {os_version})"
            return f"{browser} on {device_type} ({os_name})"
        else:
            if os_version:
                return f"{browser} on {os_name} {os_version}"
            return f"{browser} on {os_name}"
    except Exception:
        return "Unknown Device"


def validate_username(username):
    """
    Validate username format
    - Length: 3-80 characters
    - Allowed: letters, numbers, underscore, hyphen
    """
    if not username or len(username) < 3 or len(username) > 80:
        return False, "Username must be between 3 and 80 characters"

    if not re.match(r'^[a-zA-Z0-9_-]+$', username):
        return False, "Username can only contain letters, numbers, _ and -"

    return True, ""


def validate_password(password, validate_strength=None):
    """
    Validate password
    - Minimum 8 characters (always)
    - If validate_strength=True:
      - At least one uppercase letter
      - At least one lowercase letter
      - At least one digit
    """
    if validate_strength is None:
        validate_strength = current_app.config.get('VALIDATE_PASSWORD_STRENGTH', False)

    if not password or len(password) < 8:
        return False, "Password must be at least 8 characters long"

    if validate_strength:
        if not re.search(r'[A-Z]', password):
            return False, "Password must contain at least one uppercase letter"

        if not re.search(r'[a-z]', password):
            return False, "Password must contain at least one lowercase letter"

        if not re.search(r'\d', password):
            return False, "Password must contain at least one digit"

    return True, ""


def validate_public_key(public_key):
    """
    Validate ML-KEM public key format
    - Must be valid Base64 string
    - Expected sizes: ~800 bytes (Kyber512), ~1184 bytes (Kyber768), ~1568 bytes (Kyber1024)
    """
    if not public_key or not isinstance(public_key, str):
        return False, "Public key is required and must be a string"

    try:
        decoded = base64.b64decode(public_key)
        key_size = len(decoded)

        # Valid ML-KEM public key sizes
        valid_sizes = [800, 1184, 1568]  # Kyber512, Kyber768, Kyber1024

        if key_size not in valid_sizes:
            return False, f"Invalid public key size: {key_size} bytes. Expected: {valid_sizes}"

        return True, ""
    except Exception as e:
        return False, f"Invalid Base64 format: {str(e)}"


@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Register a new user

    Request JSON:
        {
            "username": "string",
            "password": "string",
            "public_key": "string (Base64-encoded ML-KEM public key)",
            "device_name": "string (optional, e.g., 'iPhone 15', 'Chrome Desktop')"
        }

    Returns:
        201: User created successfully with access and refresh tokens
        400: Invalid input or user already exists
        500: Internal server error
    """
    try:
        data = request.get_json(silent=True)

        if not data:
            return jsonify({'error': 'No data provided in request'}), 400

        username = data.get('username', '').strip()
        password = data.get('password', '')
        public_key = data.get('public_key', '').strip()
        device_name = data.get('device_name', '').strip()

        # Generate device name from User-Agent if not provided
        if not device_name:
            user_agent = request.headers.get('User-Agent', '')
            device_name = generate_device_name_from_user_agent(user_agent)

        # Validate username
        valid, error = validate_username(username)
        if not valid:
            return jsonify({'error': error}), 400

        # Validate password
        valid, error = validate_password(password)
        if not valid:
            return jsonify({'error': error}), 400

        # Validate public key
        valid, error = validate_public_key(public_key)
        if not valid:
            return jsonify({'error': error}), 400

        # Check if user already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            return jsonify({'error': 'Username already exists'}), 400

        # Create new user
        user = User(username=username)
        user.set_password(password)

        db.session.add(user)
        db.session.flush()  # Get user.id before commit

        # Create device record with public key
        device = UserDevice(
            user_id=user.id,
            device_name=device_name,
            public_key=public_key
        )
        db.session.add(device)
        db.session.commit()

        # Create tokens
        access_token = create_access_token(identity=str(user.id))
        refresh_token = create_refresh_token(identity=str(user.id))

        # Store refresh token
        from flask_jwt_extended import decode_token
        decoded_token = decode_token(refresh_token)

        token_record = RefreshToken(
            jti=decoded_token['jti'],
            user_id=user.id,
            expires_at=datetime.fromtimestamp(decoded_token['exp'])
        )
        db.session.add(token_record)
        db.session.commit()

        # Create response with access token in JSON
        response_data = {
            'message': 'User registered successfully',
            'user': user.to_dict(),
            'device': device.to_dict(),
            'access_token': access_token
        }

        # Create response and set refresh token as HTTP-only cookie
        response = make_response(jsonify(response_data), 201)

        # Set refresh token in HTTP-only cookie
        max_age = current_app.config.get('JWT_REFRESH_TOKEN_EXPIRES', timedelta(days=30))
        if isinstance(max_age, timedelta):
            max_age = int(max_age.total_seconds())

        response.set_cookie(
            'refresh_token',
            value=refresh_token,
            httponly=True,
            secure=current_app.config.get('JWT_COOKIE_SECURE', False),  # Set to True in production with HTTPS
            samesite='Lax',
            max_age=max_age
        )

        return response

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Server error: {str(e)}'}), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Login user

    Request JSON:
        {
            "username": "string",
            "password": "string"
        }

    Returns:
        200: Login successful with access and refresh tokens
        400: Invalid input
        401: Invalid credentials
        500: Internal server error
    """
    try:
        data = request.get_json(silent=True)

        if not data:
            return jsonify({'error': 'No data provided in request'}), 400

        username = data.get('username', '').strip()
        password = data.get('password', '')

        if not username or not password:
            return jsonify({'error': 'Username and password are required'}), 400

        # Find user
        user = User.query.filter_by(username=username).first()

        if not user or not user.check_password(password):
            return jsonify({'error': 'Invalid username or password'}), 401

        # Create tokens
        access_token = create_access_token(identity=str(user.id))
        refresh_token = create_refresh_token(identity=str(user.id))

        # Store refresh token
        from flask_jwt_extended import decode_token
        decoded_token = decode_token(refresh_token)

        token_record = RefreshToken(
            jti=decoded_token['jti'],
            user_id=user.id,
            expires_at=datetime.fromtimestamp(decoded_token['exp'])
        )
        db.session.add(token_record)
        db.session.commit()

        # Create response with access token in JSON
        response_data = {
            'message': 'Login successful',
            'user': user.to_dict(),
            'access_token': access_token
        }

        # Create response and set refresh token as HTTP-only cookie
        response = make_response(jsonify(response_data), 200)

        # Set refresh token in HTTP-only cookie
        max_age = current_app.config.get('JWT_REFRESH_TOKEN_EXPIRES', timedelta(days=30))
        if isinstance(max_age, timedelta):
            max_age = int(max_age.total_seconds())

        response.set_cookie(
            'refresh_token',
            value=refresh_token,
            httponly=True,
            secure=current_app.config.get('JWT_COOKIE_SECURE', False),  # Set to True in production with HTTPS
            samesite='Lax',
            max_age=max_age
        )

        return response

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Server error: {str(e)}'}), 500


@auth_bp.route('/refresh', methods=['POST'])
def refresh():
    """
    Refresh access token using refresh token from HTTP-only cookie

    Cookies:
        refresh_token: The refresh token (HTTP-only)

    Returns:
        200: New access token
        401: Invalid or revoked refresh token
        500: Internal server error
    """
    try:
        # Get refresh token from cookie
        refresh_token = request.cookies.get('refresh_token')

        if not refresh_token:
            return jsonify({'error': 'Refresh token not found'}), 401

        # Verify and decode the refresh token
        from flask_jwt_extended import decode_token
        try:
            decoded_token = decode_token(refresh_token)
        except Exception as e:
            return jsonify({'error': 'Invalid refresh token'}), 401

        # Check if it's a refresh token
        if decoded_token.get('type') != 'refresh':
            return jsonify({'error': 'Invalid token type'}), 401

        current_user_id = int(decoded_token['sub'])
        jti = decoded_token['jti']

        # Check if refresh token is revoked
        token_record = RefreshToken.query.filter_by(jti=jti).first()

        if not token_record or token_record.revoked:
            return jsonify({'error': 'Token has been revoked'}), 401

        # Create new access token
        access_token = create_access_token(identity=str(current_user_id))

        return jsonify({
            'access_token': access_token
        }), 200

    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500


@auth_bp.route('/logout', methods=['POST'])
def logout():
    """
    Logout user by revoking refresh token from HTTP-only cookie

    Cookies:
        refresh_token: The refresh token (HTTP-only)

    Returns:
        200: Logout successful
        401: Invalid refresh token
        500: Internal server error
    """
    try:
        # Get refresh token from cookie
        refresh_token = request.cookies.get('refresh_token')

        if refresh_token:
            # Decode and revoke the token
            from flask_jwt_extended import decode_token
            try:
                decoded_token = decode_token(refresh_token)
                jti = decoded_token['jti']

                # Revoke refresh token
                token_record = RefreshToken.query.filter_by(jti=jti).first()

                if token_record:
                    token_record.revoked = True
                    db.session.commit()
            except Exception:
                pass  # Token might be invalid, but we still clear the cookie

        # Create response and clear the refresh token cookie
        response = make_response(jsonify({
            'message': 'Logout successful'
        }), 200)

        response.set_cookie(
            'refresh_token',
            value='',
            httponly=True,
            secure=current_app.config.get('JWT_COOKIE_SECURE', False),
            samesite='Lax',
            max_age=0  # Expire immediately
        )

        return response

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Server error: {str(e)}'}), 500


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """
    Get current user information

    Headers:
        Authorization: Bearer <access_token>

    Returns:
        200: User information
        401: Invalid access token
        404: User not found
        500: Internal server error
    """
    try:
        current_user_id = int(get_jwt_identity())
        user = db.session.get(User, current_user_id)

        if not user:
            return jsonify({'error': 'User not found'}), 404

        return jsonify({
            'user': user.to_dict()
        }), 200

    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500
