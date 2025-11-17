"""
Tests for WebSocket connection handlers
"""

import pytest
from unittest.mock import patch
from src.socketio_handlers.connection import verify_socket_token

@patch('src.socketio_handlers.connection.decode_token')
@patch('src.socketio_handlers.connection.db')
def test_verify_socket_token_success(mock_db, mock_decode):
    """
    Test successful verification of a valid JWT token.
    """
    mock_decode.return_value = {'sub': 1, 'type': 'access'}
    mock_db.session.get.return_value = type('User', (object,), {'id': 1, 'username': 'test_user', 'is_active': True})()

    user_data, error = verify_socket_token('valid_token')

    assert error is None
    assert user_data['user_id'] == 1
    assert user_data['username'] == 'test_user'

@patch('src.socketio_handlers.connection.decode_token')
def test_verify_socket_token_invalid_type(mock_decode):
    """
    Test verification failure for a token with an invalid type.
    """
    mock_decode.return_value = {'sub': 1, 'type': 'refresh'}

    user_data, error = verify_socket_token('invalid_token')

    assert user_data is None
    assert error == 'Invalid token type: expected access token'

@patch('src.socketio_handlers.connection.decode_token')
@patch('src.socketio_handlers.connection.db')
def test_verify_socket_token_user_not_found(mock_db, mock_decode):
    """
    Test verification failure when the user is not found in the database.
    """
    mock_decode.return_value = {'sub': 1, 'type': 'access'}
    mock_db.session.get.return_value = None

    user_data, error = verify_socket_token('valid_token')

    assert user_data is None
    assert error == 'User not found'

@patch('src.socketio_handlers.connection.decode_token')
@patch('src.socketio_handlers.connection.db')
def test_verify_socket_token_user_disabled(mock_db, mock_decode):
    """
    Test verification failure when the user account is disabled.
    """
    mock_decode.return_value = {'sub': 1, 'type': 'access'}
    mock_db.session.get.return_value = type('User', (object,), {'id': 1, 'username': 'test_user', 'is_active': False})()

    user_data, error = verify_socket_token('valid_token')

    assert user_data is None
    assert error == 'User account is disabled'

@patch('src.socketio_handlers.connection.decode_token')
def test_verify_socket_token_invalid_or_expired(mock_decode):
    """
    Test verification failure for an invalid or expired token.
    """
    mock_decode.side_effect = Exception('Invalid or expired token')

    user_data, error = verify_socket_token('invalid_token')

    assert user_data is None
    assert error == 'Invalid or expired token'

def test_socket_connect_success(test_client):
    """
    Test successful WebSocket connection with mocked Auth and DB.
    """
    with patch('src.socketio_handlers.connection.verify_socket_token') as mock_verify, \
         patch('src.models.User.get_username_by_userid') as mock_get_username:

        mock_verify.return_value = ({'user_id': 1, 'username': 'test_user'}, None)
        mock_get_username.return_value = 'test_user_from_db'

        auth_payload = {"token": "Bearer fake_token"}
        test_client.connect(auth=auth_payload)

        assert test_client.is_connected()

def test_socket_disconnect(test_client):
    """
    Test WebSocket disconnection.
    """
    with patch('src.socketio_handlers.connection.verify_socket_token') as mock_verify, \
         patch('src.models.User.get_username_by_userid') as mock_get_username:

        mock_verify.return_value = ({'user_id': 1, 'username': 'disconnect_tester'}, None)
        mock_get_username.return_value = 'disconnect_tester'

        test_client.connect(auth={"token": "Bearer mock_token"})

        assert test_client.is_connected()

        test_client.disconnect()

        assert not test_client.is_connected()
