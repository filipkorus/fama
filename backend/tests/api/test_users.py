"""
Tests for User Management API (user search and public keys)
Extracted from test_auth.py - handles /api/users/* endpoints
"""

import pytest
from models import User
from database import db


class TestUserSearchAPI:
    """Test class for user search endpoint"""

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
        response = client.get('/api/users/search?query=alice', headers={
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
            assert 'public_key' in user
            assert 'alice' in user['username']

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
        response = client.get('/api/users/search?query=user&page=1&per_page=10', headers={
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
        response = client.get('/api/users/search?query=user&page=2&per_page=10', headers={
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
        response = client.get('/api/users/search', headers={
            'Authorization': f'Bearer {access_token}'
        })
        assert response.status_code == 400
        assert 'error' in response.get_json()

        # Test query too short
        response = client.get('/api/users/search?query=a', headers={
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

        response = client.get('/api/users/search?query=nonexistent', headers={
            'Authorization': f'Bearer {access_token}'
        })

        assert response.status_code == 200
        data = response.get_json()
        assert len(data['users']) == 0
        assert data['pagination']['total_count'] == 0

    def test_search_users_per_page_limit(self, client, sample_public_key):
        """Test that per_page is capped at 50"""
        # Register test user
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

        # Try to request more than 50 per page
        response = client.get('/api/users/search?query=test&per_page=100', headers={
            'Authorization': f'Bearer {access_token}'
        })

        assert response.status_code == 200
        data = response.get_json()
        # Should be capped at 10 (default) since invalid value
        assert data['pagination']['per_page'] == 10

    def test_search_users_case_insensitive(self, client, sample_public_key):
        """Test that search is case-insensitive"""
        # Register users with different cases
        client.post('/api/auth/register', json={
            'username': 'TestUser',
            'password': 'TestPass123',
            'public_key': sample_public_key
        })
        client.post('/api/auth/register', json={
            'username': 'searcher',
            'password': 'TestPass123',
            'public_key': sample_public_key
        })
        login_response = client.post('/api/auth/login', json={
            'username': 'searcher',
            'password': 'TestPass123'
        })
        access_token = login_response.get_json()['access_token']

        # Search with lowercase
        response = client.get('/api/users/search?query=testuser', headers={
            'Authorization': f'Bearer {access_token}'
        })

        assert response.status_code == 200
        data = response.get_json()
        assert len(data['users']) == 1
        assert data['users'][0]['username'] == 'TestUser'

    def test_search_users_unauthorized(self, client):
        """Test user search without authentication"""
        response = client.get('/api/users/search?query=test')
        assert response.status_code == 401

    def test_search_users_invalid_page(self, client, sample_public_key):
        """Test that invalid page numbers are corrected"""
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

        # Test page 0 (should be corrected to 1)
        response = client.get('/api/users/search?query=test&page=0', headers={
            'Authorization': f'Bearer {access_token}'
        })

        assert response.status_code == 200
        data = response.get_json()
        assert data['pagination']['page'] == 1

        # Test negative page (should be corrected to 1)
        response = client.get('/api/users/search?query=test&page=-5', headers={
            'Authorization': f'Bearer {access_token}'
        })

        assert response.status_code == 200
        data = response.get_json()
        assert data['pagination']['page'] == 1


class TestPublicKeysAPI:
    """Test class for public keys retrieval endpoints"""

    def test_get_user_public_key_by_id(self, client, sample_public_key):
        """Test getting user public key by user ID"""
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

        # Get alice's public key
        response = client.get(f'/api/users/{target_user_id}/public-key', headers={
            'Authorization': f'Bearer {access_token}'
        })

        assert response.status_code == 200
        data = response.get_json()

        # Check response structure
        assert 'user_id' in data
        assert 'username' in data
        assert 'public_key' in data
        assert data['user_id'] == target_user_id
        assert data['username'] == 'alice'
        assert data['public_key'] == sample_public_key

    def test_get_user_public_key_by_id_not_found(self, client, sample_public_key):
        """Test getting public key for non-existent user ID"""
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

        response = client.get('/api/users/99999/public-key', headers={
            'Authorization': f'Bearer {access_token}'
        })

        assert response.status_code == 404
        assert 'error' in response.get_json()

    def test_get_user_public_key_by_id_unauthorized(self, client):
        """Test getting public key without authentication"""
        response = client.get('/api/users/1/public-key')
        assert response.status_code == 401

    def test_get_user_public_key_by_username(self, client, sample_public_key):
        """Test getting user public key by username"""
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

        # Get alice's public key by username
        response = client.get('/api/users/alice/public-key', headers={
            'Authorization': f'Bearer {access_token}'
        })

        assert response.status_code == 200
        data = response.get_json()

        assert 'user_id' in data
        assert 'username' in data
        assert 'public_key' in data
        assert data['username'] == 'alice'
        assert data['public_key'] == sample_public_key

    def test_get_user_public_key_by_username_not_found(self, client, sample_public_key):
        """Test getting public key for non-existent username"""
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

        response = client.get('/api/users/nonexistent/public-key', headers={
            'Authorization': f'Bearer {access_token}'
        })

        assert response.status_code == 404
        assert 'error' in response.get_json()

    def test_get_user_public_key_by_username_unauthorized(self, client):
        """Test getting public key by username without authentication"""
        response = client.get('/api/users/testuser/public-key')
        assert response.status_code == 401

    def test_get_user_public_key_special_characters_in_username(self, client, sample_public_key):
        """Test getting public key for username that needs URL encoding"""
        # Register user with allowed special characters
        client.post('/api/auth/register', json={
            'username': 'test_user-123',
            'password': 'TestPass123',
            'public_key': sample_public_key
        })
        client.post('/api/auth/register', json={
            'username': 'searcher',
            'password': 'TestPass123',
            'public_key': sample_public_key
        })
        
        # Login as searcher
        login_response = client.post('/api/auth/login', json={
            'username': 'searcher',
            'password': 'TestPass123'
        })
        access_token = login_response.get_json()['access_token']

        # Get public key - Flask should handle URL encoding automatically
        response = client.get('/api/users/test_user-123/public-key', headers={
            'Authorization': f'Bearer {access_token}'
        })

        assert response.status_code == 200
        data = response.get_json()
        assert data['username'] == 'test_user-123'

    def test_search_users_partial_match(self, client, sample_public_key):
        """Test that search finds partial matches"""
        # Register users
        client.post('/api/auth/register', json={
            'username': 'developer',
            'password': 'TestPass123',
            'public_key': sample_public_key
        })
        client.post('/api/auth/register', json={
            'username': 'devops',
            'password': 'TestPass123',
            'public_key': sample_public_key
        })
        client.post('/api/auth/register', json={
            'username': 'designer',
            'password': 'TestPass123',
            'public_key': sample_public_key
        })

        # Login
        login_response = client.post('/api/auth/login', json={
            'username': 'developer',
            'password': 'TestPass123'
        })
        access_token = login_response.get_json()['access_token']

        # Search for 'dev'
        response = client.get('/api/users/search?query=dev', headers={
            'Authorization': f'Bearer {access_token}'
        })

        assert response.status_code == 200
        data = response.get_json()
        assert data['pagination']['total_count'] == 2
        usernames = [u['username'] for u in data['users']]
        assert 'developer' in usernames
        assert 'devops' in usernames
        assert 'designer' not in usernames
