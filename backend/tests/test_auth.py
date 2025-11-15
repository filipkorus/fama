"""
Testy dla API autoryzacji (rejestracja, logowanie, JWT)
Access token jest wysyłany w JSON, refresh token w HTTP-only cookie
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
        assert 'device' in data
        assert 'access_token' in data
        assert 'refresh_token' not in data  # Refresh token should NOT be in JSON

        assert data['user']['username'] == 'testuser'
        assert 'public_key' not in data['user']  # public_key is in device, not user
        assert 'password' not in data['user']
        assert 'password_hash' not in data['user']

        # Check device data
        assert 'public_key' in data['device']
        assert data['device']['public_key'] == sample_public_key
        assert 'device_name' in data['device']

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

    def test_register_auto_device_name(self, client, sample_public_key):
        """Test that device_name is auto-generated from User-Agent if not provided"""
        response = client.post('/api/auth/register',
            json={
                'username': 'testuser',
                'password': 'TestPass123',
                'public_key': sample_public_key
            },
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
        )

        assert response.status_code == 201
        data = response.get_json()
        assert 'device' in data
        assert data['device']['device_name'] is not None
        assert len(data['device']['device_name']) > 0
        # Should contain browser and OS info
        assert 'Chrome' in data['device']['device_name'] or 'Unknown' in data['device']['device_name']

    def test_register_custom_device_name(self, client, sample_public_key):
        """Test registration with custom device_name"""
        response = client.post('/api/auth/register', json={
            'username': 'testuser',
            'password': 'TestPass123',
            'public_key': sample_public_key,
            'device_name': 'My Custom Device'
        })

        assert response.status_code == 201
        data = response.get_json()
        assert 'device' in data
        assert data['device']['device_name'] == 'My Custom Device'

    def test_login_success(self, client, sample_public_key):
        """Test successful login"""
        # First register a user
        client.post('/api/auth/register', json={
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
        client.post('/api/auth/register', json={
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


class TestPublicKeysAPI:
    """Test class for public keys retrieval endpoints"""

    def test_search_users_success(self, client, sample_public_key):
        """Test successful user search"""
        # Create test users
        client.post('/api/auth/register', json={
            'username': 'alice',
            'password': 'TestPass123',
            'public_key': sample_public_key
        })
        client.post('/api/auth/register', json={
            'username': 'alice123',
            'password': 'TestPass123',
            'public_key': sample_public_key
        })
        client.post('/api/auth/register', json={
            'username': 'bob',
            'password': 'TestPass123',
            'public_key': sample_public_key
        })

        # Login to get access token
        login_response = client.post('/api/auth/login', json={
            'username': 'alice',
            'password': 'TestPass123'
        })
        access_token = login_response.get_json()['access_token']

        # Search for users
        response = client.get('/api/auth/users/search?query=alice', headers={
            'Authorization': f'Bearer {access_token}'
        })

        assert response.status_code == 200
        data = response.get_json()

        # Check response structure
        assert 'users' in data
        assert 'pagination' in data

        # Check pagination metadata
        assert data['pagination']['page'] == 1
        assert data['pagination']['per_page'] == 10
        assert data['pagination']['total_count'] == 2
        assert data['pagination']['total_pages'] == 1
        assert data['pagination']['has_next'] is False
        assert data['pagination']['has_prev'] is False

        # Check users data
        assert len(data['users']) == 2
        for user in data['users']:
            assert 'user_id' in user
            assert 'username' in user
            assert 'devices' in user
            assert 'alice' in user['username']
            # Check minimal device info (privacy)
            for device in user['devices']:
                assert 'device_id' in device
                assert 'public_key' in device
                assert 'device_name' not in device
                assert 'created_at' not in device
                assert 'last_used_at' not in device

    def test_search_users_with_pagination(self, client, sample_public_key):
        """Test user search with pagination"""
        # Create multiple users
        for i in range(15):
            client.post('/api/auth/register', json={
                'username': f'user{i}',
                'password': 'TestPass123',
                'public_key': sample_public_key
            })

        # Login
        login_response = client.post('/api/auth/login', json={
            'username': 'user0',
            'password': 'TestPass123'
        })
        access_token = login_response.get_json()['access_token']

        # Test page 1
        response = client.get('/api/auth/users/search?query=user&page=1&per_page=10', headers={
            'Authorization': f'Bearer {access_token}'
        })

        assert response.status_code == 200
        data = response.get_json()
        assert len(data['users']) == 10
        assert data['pagination']['page'] == 1
        assert data['pagination']['total_count'] == 15
        assert data['pagination']['total_pages'] == 2
        assert data['pagination']['has_next'] is True
        assert data['pagination']['has_prev'] is False

        # Test page 2
        response = client.get('/api/auth/users/search?query=user&page=2&per_page=10', headers={
            'Authorization': f'Bearer {access_token}'
        })

        assert response.status_code == 200
        data = response.get_json()
        assert len(data['users']) == 5
        assert data['pagination']['page'] == 2
        assert data['pagination']['has_next'] is False
        assert data['pagination']['has_prev'] is True

    def test_search_users_invalid_query(self, client, sample_public_key):
        """Test user search with invalid query"""
        # Register and login
        client.post('/api/auth/register', json={
            'username': 'testuser',
            'password': 'TestPass123',
            'public_key': sample_public_key
        })
        login_response = client.post('/api/auth/login', json={
            'username': 'testuser',
            'password': 'TestPass123'
        })
        access_token = login_response.get_json()['access_token']

        # Test missing query
        response = client.get('/api/auth/users/search', headers={
            'Authorization': f'Bearer {access_token}'
        })
        assert response.status_code == 400
        assert 'error' in response.get_json()

        # Test query too short
        response = client.get('/api/auth/users/search?query=a', headers={
            'Authorization': f'Bearer {access_token}'
        })
        assert response.status_code == 400
        assert 'at least 2 characters' in response.get_json()['error']

    def test_search_users_no_results(self, client, sample_public_key):
        """Test user search with no matching results"""
        client.post('/api/auth/register', json={
            'username': 'testuser',
            'password': 'TestPass123',
            'public_key': sample_public_key
        })
        login_response = client.post('/api/auth/login', json={
            'username': 'testuser',
            'password': 'TestPass123'
        })
        access_token = login_response.get_json()['access_token']

        response = client.get('/api/auth/users/search?query=nonexistent', headers={
            'Authorization': f'Bearer {access_token}'
        })

        assert response.status_code == 200
        data = response.get_json()
        assert len(data['users']) == 0
        assert data['pagination']['total_count'] == 0

    def test_search_users_unauthorized(self, client):
        """Test user search without authentication"""
        response = client.get('/api/auth/users/search?query=test')
        assert response.status_code == 401

    def test_get_user_public_keys_by_id(self, client, sample_public_key):
        """Test getting user public keys by user ID"""
        # Register two users
        response1 = client.post('/api/auth/register', json={
            'username': 'alice',
            'password': 'TestPass123',
            'public_key': sample_public_key
        })
        target_user_id = response1.get_json()['user']['id']

        client.post('/api/auth/register', json={
            'username': 'bob',
            'password': 'TestPass123',
            'public_key': sample_public_key
        })

        # Login as bob to get access token
        login_response = client.post('/api/auth/login', json={
            'username': 'bob',
            'password': 'TestPass123'
        })
        access_token = login_response.get_json()['access_token']

        # Get alice's public keys
        response = client.get(f'/api/auth/users/{target_user_id}/public-keys', headers={
            'Authorization': f'Bearer {access_token}'
        })

        assert response.status_code == 200
        data = response.get_json()

        # Check response structure
        assert 'user_id' in data
        assert 'username' in data
        assert 'devices' in data
        assert data['user_id'] == target_user_id
        assert data['username'] == 'alice'

        # Check minimal device info
        assert len(data['devices']) > 0
        for device in data['devices']:
            assert 'device_id' in device
            assert 'public_key' in device
            assert 'device_name' not in device
            assert 'created_at' not in device

    def test_get_user_public_keys_by_id_not_found(self, client, sample_public_key):
        """Test getting public keys for non-existent user ID"""
        client.post('/api/auth/register', json={
            'username': 'testuser',
            'password': 'TestPass123',
            'public_key': sample_public_key
        })
        login_response = client.post('/api/auth/login', json={
            'username': 'testuser',
            'password': 'TestPass123'
        })
        access_token = login_response.get_json()['access_token']

        response = client.get('/api/auth/users/99999/public-keys', headers={
            'Authorization': f'Bearer {access_token}'
        })

        assert response.status_code == 404
        assert 'error' in response.get_json()

    def test_get_user_public_keys_by_id_unauthorized(self, client):
        """Test getting public keys without authentication"""
        response = client.get('/api/auth/users/1/public-keys')
        assert response.status_code == 401

    def test_get_user_public_keys_by_username(self, client, sample_public_key):
        """Test getting user public keys by username"""
        # Register users
        client.post('/api/auth/register', json={
            'username': 'alice',
            'password': 'TestPass123',
            'public_key': sample_public_key
        })
        client.post('/api/auth/register', json={
            'username': 'bob',
            'password': 'TestPass123',
            'public_key': sample_public_key
        })

        # Login as bob
        login_response = client.post('/api/auth/login', json={
            'username': 'bob',
            'password': 'TestPass123'
        })
        access_token = login_response.get_json()['access_token']

        # Get alice's public keys by username
        response = client.get('/api/auth/users/alice/public-keys', headers={
            'Authorization': f'Bearer {access_token}'
        })

        assert response.status_code == 200
        data = response.get_json()

        assert 'user_id' in data
        assert 'username' in data
        assert 'devices' in data
        assert data['username'] == 'alice'

        # Check minimal device info
        for device in data['devices']:
            assert 'device_id' in device
            assert 'public_key' in device
            assert 'device_name' not in device

    def test_get_user_public_keys_by_username_not_found(self, client, sample_public_key):
        """Test getting public keys for non-existent username"""
        client.post('/api/auth/register', json={
            'username': 'testuser',
            'password': 'TestPass123',
            'public_key': sample_public_key
        })
        login_response = client.post('/api/auth/login', json={
            'username': 'testuser',
            'password': 'TestPass123'
        })
        access_token = login_response.get_json()['access_token']

        response = client.get('/api/auth/users/nonexistent/public-keys', headers={
            'Authorization': f'Bearer {access_token}'
        })

        assert response.status_code == 404
        assert 'error' in response.get_json()

    def test_get_user_public_keys_by_username_unauthorized(self, client):
        """Test getting public keys by username without authentication"""
        response = client.get('/api/auth/users/testuser/public-keys')
        assert response.status_code == 401

    def test_pagination_edge_cases(self, client, sample_public_key):
        """Test pagination with edge cases"""
        # Create 5 users
        for i in range(5):
            client.post('/api/auth/register', json={
                'username': f'testuser{i}',
                'password': 'TestPass123',
                'public_key': sample_public_key
            })

        login_response = client.post('/api/auth/login', json={
            'username': 'testuser0',
            'password': 'TestPass123'
        })
        access_token = login_response.get_json()['access_token']

        # Test with per_page > total results
        response = client.get('/api/auth/users/search?query=testuser&per_page=100', headers={
            'Authorization': f'Bearer {access_token}'
        })
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['users']) == 5
        assert data['pagination']['total_pages'] == 1

        # Test with page=0 (should default to 1)
        response = client.get('/api/auth/users/search?query=testuser&page=0', headers={
            'Authorization': f'Bearer {access_token}'
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data['pagination']['page'] == 1

        # Test with per_page > max (50)
        response = client.get('/api/auth/users/search?query=testuser&per_page=100', headers={
            'Authorization': f'Bearer {access_token}'
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data['pagination']['per_page'] == 10  # Should be clamped to default

        # Test with page beyond results
        response = client.get('/api/auth/users/search?query=testuser&page=10', headers={
            'Authorization': f'Bearer {access_token}'
        })
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['users']) == 0
