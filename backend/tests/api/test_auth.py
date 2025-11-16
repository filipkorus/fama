"""
Tests for Authentication API (register, login, logout, refresh token, /me)
Handles /api/auth/* endpoints only
"""

import pytest
from models import User, RefreshToken
from database import db


class TestAuthAPI:
    """Test class for authentication API endpoints"""

    def test_register_success(self, client, sample_public_key):
        """Test successful user registration"""
        response = client.post('/api/auth/register', json={
            'username': 'testuser',
            'password': 'TestPass123',
            'public_key': sample_public_key
        })

        assert response.status_code == 201
        data = response.get_json()

        # Check JSON response
        assert 'message' in data
        assert 'user' in data
        assert 'access_token' in data
        assert 'refresh_token' not in data  # Refresh token should NOT be in JSON

        assert data['user']['username'] == 'testuser'
        assert 'password' not in data['user']
        assert 'password_hash' not in data['user']

        # Check HTTP-only cookie
        cookies = response.headers.getlist('Set-Cookie')
        refresh_cookie = None
        for cookie in cookies:
            if cookie.startswith('refresh_token='):
                refresh_cookie = cookie
                break

        assert refresh_cookie is not None, "Refresh token cookie should be set"
        assert 'HttpOnly' in refresh_cookie
        assert 'SameSite=Lax' in refresh_cookie

    def test_register_duplicate_username(self, client, sample_public_key):
        """Test registration with duplicate username"""
        # Create first user
        client.post('/api/auth/register', json={
            'username': 'duplicate',
            'password': 'TestPass123',
            'public_key': sample_public_key
        })

        # Try to create second user with same username
        response = client.post('/api/auth/register', json={
            'username': 'duplicate',
            'password': 'DifferentPass123',
            'public_key': sample_public_key
        })

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'already exists' in data['error'].lower()

    def test_register_missing_username(self, client, sample_public_key):
        """Test registration without username"""
        response = client.post('/api/auth/register', json={
            'password': 'TestPass123',
            'public_key': sample_public_key
        })

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

    def test_register_missing_password(self, client, sample_public_key):
        """Test registration without password"""
        response = client.post('/api/auth/register', json={
            'username': 'testuser',
            'public_key': sample_public_key
        })

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

    def test_register_missing_public_key(self, client):
        """Test registration without public key"""
        response = client.post('/api/auth/register', json={
            'username': 'testuser',
            'password': 'TestPass123'
        })

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

    def test_register_short_username(self, client, sample_public_key):
        """Test registration with too short username"""
        response = client.post('/api/auth/register', json={
            'username': 'ab',
            'password': 'TestPass123',
            'public_key': sample_public_key
        })

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'username' in data['error'].lower()

    def test_register_invalid_username_characters(self, client, sample_public_key):
        """Test registration with invalid characters in username"""
        response = client.post('/api/auth/register', json={
            'username': 'test@user',
            'password': 'TestPass123',
            'public_key': sample_public_key
        })

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'username' in data['error'].lower()

    def test_register_short_password(self, client, sample_public_key):
        """Test registration with too short password"""
        response = client.post('/api/auth/register', json={
            'username': 'testuser',
            'password': 'short',
            'public_key': sample_public_key
        })

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'password' in data['error'].lower()

    def test_register_no_data(self, client):
        """Test registration without data"""
        response = client.post('/api/auth/register')

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

    def test_register_invalid_public_key_format(self, client):
        """Test registration with invalid Base64 public key"""
        response = client.post('/api/auth/register', json={
            'username': 'testuser',
            'password': 'TestPass123',
            'public_key': 'not-valid-base64!!!'
        })

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'base64' in data['error'].lower() or 'public key' in data['error'].lower()

    def test_register_invalid_public_key_size(self, client):
        """Test registration with wrong size public key"""
        import base64
        # Create a key with wrong size (e.g., 100 bytes instead of 1184)
        wrong_size_key = base64.b64encode(b'0' * 100).decode('utf-8')

        response = client.post('/api/auth/register', json={
            'username': 'testuser',
            'password': 'TestPass123',
            'public_key': wrong_size_key
        })

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
        assert 'size' in data['error'].lower() or 'invalid' in data['error'].lower()

    def test_login_success(self, client, sample_public_key):
        """Test successful login"""
        # First register a user
        register_response = client.post('/api/auth/register', json={
            'username': 'loginuser',
            'password': 'TestPass123',
            'public_key': sample_public_key
        })

        # Then login
        response = client.post('/api/auth/login', json={
            'username': 'loginuser',
            'password': 'TestPass123'
        })

        assert response.status_code == 200
        data = response.get_json()

        # Check JSON response
        assert 'message' in data
        assert 'user' in data
        assert 'access_token' in data
        assert 'refresh_token' not in data  # Refresh token should NOT be in JSON

        assert data['user']['username'] == 'loginuser'

        # Check HTTP-only cookie
        cookies = response.headers.getlist('Set-Cookie')
        refresh_cookie = None
        for cookie in cookies:
            if cookie.startswith('refresh_token='):
                refresh_cookie = cookie
                break

        assert refresh_cookie is not None, "Refresh token cookie should be set"
        assert 'HttpOnly' in refresh_cookie

    def test_login_wrong_password(self, client, sample_public_key):
        """Test login with wrong password"""
        # Register user
        register_response = client.post('/api/auth/register', json={
            'username': 'testuser',
            'password': 'TestPass123',
            'public_key': sample_public_key
        })

        # Try to login with wrong password
        response = client.post('/api/auth/login', json={
            'username': 'testuser',
            'password': 'WrongPass123'
        })

        assert response.status_code == 401
        data = response.get_json()
        assert 'error' in data

    def test_login_nonexistent_user(self, client):
        """Test login with nonexistent username"""
        response = client.post('/api/auth/login', json={
            'username': 'nonexistent',
            'password': 'TestPass123'
        })

        assert response.status_code == 401
        data = response.get_json()
        assert 'error' in data

    def test_login_missing_credentials(self, client):
        """Test login without credentials"""
        response = client.post('/api/auth/login', json={})

        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data

    def test_refresh_token_success(self, client, sample_public_key):
        """Test successful token refresh using cookie"""
        # Register and get tokens
        register_response = client.post('/api/auth/register', json={
            'username': 'refreshuser',
            'password': 'TestPass123',
            'public_key': sample_public_key
        })

        # Extract refresh token from cookie
        cookies = register_response.headers.getlist('Set-Cookie')
        refresh_cookie = None
        for cookie in cookies:
            if cookie.startswith('refresh_token='):
                # Extract the token value
                refresh_token = cookie.split(';')[0].split('=')[1]
                refresh_cookie = cookie
                break

        assert refresh_cookie is not None

        # Set the cookie for the next request
        client.set_cookie('refresh_token', refresh_token)

        # Refresh access token
        response = client.post('/api/auth/refresh')

        assert response.status_code == 200
        data = response.get_json()
        assert 'access_token' in data

    def test_refresh_token_missing(self, client):
        """Test token refresh without refresh token cookie"""
        response = client.post('/api/auth/refresh')

        assert response.status_code == 401
        data = response.get_json()
        assert 'error' in data

    def test_refresh_token_invalid(self, client):
        """Test token refresh with invalid refresh token"""
        # Set invalid token in cookie
        client.set_cookie('refresh_token', 'invalid_token')

        response = client.post('/api/auth/refresh')

        assert response.status_code == 401
        data = response.get_json()
        assert 'error' in data

    def test_refresh_token_revoked(self, client, sample_public_key):
        """Test token refresh with revoked token"""
        # Register and get tokens
        register_response = client.post('/api/auth/register', json={
            'username': 'revokeuser',
            'password': 'TestPass123',
            'public_key': sample_public_key
        })

        # Extract refresh token from cookie
        cookies = register_response.headers.getlist('Set-Cookie')
        for cookie in cookies:
            if cookie.startswith('refresh_token='):
                refresh_token = cookie.split(';')[0].split('=')[1]
                break

        # Revoke the token
        from flask_jwt_extended import decode_token
        decoded = decode_token(refresh_token)
        token_record = RefreshToken.query.filter_by(jti=decoded['jti']).first()
        token_record.revoked = True
        db.session.commit()

        # Set the cookie and try to refresh
        client.set_cookie('refresh_token', refresh_token)
        response = client.post('/api/auth/refresh')

        assert response.status_code == 401
        data = response.get_json()
        assert 'error' in data

    def test_logout_success(self, client, sample_public_key):
        """Test successful logout"""
        # Register and get tokens
        register_response = client.post('/api/auth/register', json={
            'username': 'logoutuser',
            'password': 'TestPass123',
            'public_key': sample_public_key
        })

        # Extract refresh token from cookie
        cookies = register_response.headers.getlist('Set-Cookie')
        for cookie in cookies:
            if cookie.startswith('refresh_token='):
                refresh_token = cookie.split(';')[0].split('=')[1]
                break

        # Set the cookie
        client.set_cookie('refresh_token', refresh_token)

        # Logout
        response = client.post('/api/auth/logout')

        assert response.status_code == 200
        data = response.get_json()
        assert 'message' in data

        # Check that cookie is cleared
        cookies = response.headers.getlist('Set-Cookie')
        refresh_cookie = None
        for cookie in cookies:
            if cookie.startswith('refresh_token='):
                refresh_cookie = cookie
                break

        assert refresh_cookie is not None
        assert 'Max-Age=0' in refresh_cookie or 'max-age=0' in refresh_cookie

    def test_logout_without_token(self, client):
        """Test logout without refresh token"""
        response = client.post('/api/auth/logout')

        # Should still succeed and clear cookie
        assert response.status_code == 200
        data = response.get_json()
        assert 'message' in data

    def test_get_current_user_success(self, client, sample_public_key):
        """Test getting current user info with valid access token"""
        # Register and get tokens
        register_response = client.post('/api/auth/register', json={
            'username': 'currentuser',
            'password': 'TestPass123',
            'public_key': sample_public_key
        })

        access_token = register_response.get_json()['access_token']

        # Get current user
        response = client.get('/api/auth/me', headers={
            'Authorization': f'Bearer {access_token}'
        })

        assert response.status_code == 200
        data = response.get_json()
        assert 'user' in data
        assert data['user']['username'] == 'currentuser'

    def test_get_current_user_no_token(self, client):
        """Test getting current user info without token"""
        response = client.get('/api/auth/me')

        assert response.status_code == 401

    def test_get_current_user_invalid_token(self, client):
        """Test getting current user info with invalid token"""
        response = client.get('/api/auth/me', headers={
            'Authorization': 'Bearer invalid_token'
        })

        assert response.status_code == 422

    def test_token_expiration(self, client, app):
        """Test that tokens expire correctly"""
        # This test would require time manipulation or very short token expiry
        # Skipping for now as it requires more complex setup
        pass

    def test_multiple_refresh_tokens(self, client, sample_public_key):
        """Test that user can have multiple active refresh tokens"""
        # Register user
        response1 = client.post('/api/auth/register', json={
            'username': 'multitoken',
            'password': 'TestPass123',
            'public_key': sample_public_key
        })

        # Login again (creates second refresh token)
        response2 = client.post('/api/auth/login', json={
            'username': 'multitoken',
            'password': 'TestPass123'
        })

        # Both should have valid cookies
        assert response1.status_code == 201
        assert response2.status_code == 200

        # Check that user has multiple tokens in database
        user = User.query.filter_by(username='multitoken').first()
        tokens = RefreshToken.query.filter_by(user_id=user.id, revoked=False).all()
        assert len(tokens) == 2

    def test_register_whitespace_trimming(self, client, sample_public_key):
        """Test that username is trimmed of whitespace"""
        response = client.post('/api/auth/register', json={
            'username': '  testuser  ',
            'password': 'TestPass123',
            'public_key': sample_public_key
        })

        assert response.status_code == 201
        data = response.get_json()
        assert data['user']['username'] == 'testuser'

    def test_login_whitespace_trimming(self, client, sample_public_key):
        """Test that username is trimmed during login"""
        # Register user
        client.post('/api/auth/register', json={
            'username': 'testuser',
            'password': 'TestPass123',
            'public_key': sample_public_key
        })

        # Login with whitespace
        response = client.post('/api/auth/login', json={
            'username': '  testuser  ',
            'password': 'TestPass123'
        })

        assert response.status_code == 200
        data = response.get_json()
        assert data['user']['username'] == 'testuser'

    def test_get_current_user_deleted_user(self, client, sample_public_key):
        """Test accessing /me with token of deleted user"""
        # Register and get token
        response = client.post('/api/auth/register', json={
            'username': 'deleteme',
            'password': 'TestPass123',
            'public_key': sample_public_key
        })
        access_token = response.get_json()['access_token']

        # Delete the user and their refresh tokens
        user = User.query.filter_by(username='deleteme').first()
        user_id = user.id

        # First delete all refresh tokens for this user
        RefreshToken.query.filter_by(user_id=user_id).delete()

        # Then delete the user
        db.session.delete(user)
        db.session.commit()

        # Try to access /me with the access token (which is still valid JWT but user doesn't exist)
        response = client.get('/api/auth/me', headers={
            'Authorization': f'Bearer {access_token}'
        })

        assert response.status_code == 404
        assert 'error' in response.get_json()
        assert 'not found' in response.get_json()['error'].lower()
