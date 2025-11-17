import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

@pytest.fixture
def valid_message_payload():
    return {
        'recipient_id': 2,
        'encrypted_content': 'encrypted_content_string',
        'capsule_mlkem': 'capsule_string',
        'nonce': 'nonce_string'
    }

@patch('src.socketio_handlers.messages.emit')
@patch('src.socketio_handlers.messages.sio_conn_users')
@patch('src.socketio_handlers.messages.db')
@patch('src.socketio_handlers.messages.User')
@patch('src.socketio_handlers.messages.Message')
def test_send_message_success_recipient_online(mock_message_cls, mock_user_cls, mock_db, mock_sio_users, mock_emit, test_client):
    """
    Test wysyłania wiadomości, gdy odbiorca jest ONLINE.
    """
    valid_message_payload = {
        'recipient_id': 2,
        'encrypted_content': 'encrypted_content_string',
        'capsule_mlkem': 'capsule_string',
        'nonce': 'nonce_string'
    }

    mock_sio_users.is_authenticated.return_value = True
    mock_sio_users.get_sender_id.return_value = 1
    mock_sio_users.get_sender_username.return_value = "sender_user"

    mock_sio_users.get_sender_sid.return_value = "recipient_sid_123"

    mock_recipient = MagicMock()
    mock_recipient.is_active = True
    mock_db.session.get.return_value = mock_recipient

    mock_message_instance = MagicMock()
    mock_message_instance.id = 100
    mock_message_instance.created_at = datetime.now()
    mock_message_cls.return_value = mock_message_instance

    test_client.emit('send_message', valid_message_payload)

    assert mock_emit.call_count == 2
    calls = mock_emit.call_args_list

    args_recipient, kwargs_recipient = calls[0]

    assert args_recipient[0] == 'receive_message'

    payload = args_recipient[1]
    assert payload['encrypted_content'] == 'encrypted_content_string'
    assert payload['id'] == 100

    assert kwargs_recipient['room'] == 'recipient_sid_123'

    args_sender, kwargs_sender = calls[1]

    assert args_sender[0] == 'message_delivered'

    payload_ack = args_sender[1]
    assert payload_ack['message_id'] == 100

    assert 'room' in kwargs_sender

    mock_db.session.add.assert_called_once()
    mock_db.session.commit.assert_called_once()
    mock_message_instance.mark_as_delivered.assert_called_once()


@patch('src.socketio_handlers.messages.emit')
@patch('src.socketio_handlers.messages.sio_conn_users')
@patch('src.socketio_handlers.messages.db')
@patch('src.socketio_handlers.messages.User')
@patch('src.socketio_handlers.messages.Message')
def test_send_message_success_recipient_offline(mock_message_cls, mock_user_cls, mock_db, mock_sio_users, mock_emit, test_client):
    """
    Test wysyłania wiadomości, gdy odbiorca jest OFFLINE.
    """
    valid_message_payload = {
        'recipient_id': 2,
        'encrypted_content': 'encrypted_content_string',
        'capsule_mlkem': 'capsule_string',
        'nonce': 'nonce_string'
    }

    mock_sio_users.is_authenticated.return_value = True
    mock_sio_users.get_sender_id.return_value = 1

    mock_sio_users.get_sender_sid.return_value = None

    mock_recipient = MagicMock()
    mock_recipient.is_active = True
    mock_db.session.get.return_value = mock_recipient

    test_client.emit('send_message', valid_message_payload)

    mock_emit.assert_not_called()

    mock_db.session.add.assert_called_once()
    mock_db.session.commit.assert_called_once()


@patch('src.socketio_handlers.messages.emit')
@patch('src.socketio_handlers.messages.sio_conn_users')
def test_send_message_not_authenticated(mock_sio_users, mock_emit, test_client):
    """Test próby wysłania bez autoryzacji"""
    mock_sio_users.is_authenticated.return_value = False

    payload = {
        'recipient_id': 2,
        'encrypted_content': 'x',
        'capsule_mlkem': 'x',
        'nonce': 'x'
    }

    test_client.emit('send_message', payload)

    mock_emit.assert_called_once()

    args, _ = mock_emit.call_args
    assert args[0] == 'error'
    assert args[1]['message'] == 'Not authenticated'


@patch('src.socketio_handlers.messages.emit')
@patch('src.socketio_handlers.messages.sio_conn_users')
def test_send_message_validation_errors(mock_sio_users, mock_emit, test_client):
    """Testy walidacji danych wejściowych"""
    mock_sio_users.is_authenticated.return_value = True
    mock_sio_users.get_sender_id.return_value = 1

    test_client.emit('send_message', "Just a string")

    args, _ = mock_emit.call_args
    assert args[0] == 'error'
    assert args[1]['message'] == 'Invalid data format: expected JSON object'

    mock_emit.reset_mock()

    test_client.emit('send_message', {'recipient_id': 2})

    args, _ = mock_emit.call_args
    assert args[0] == 'error'
    assert args[1]['message'] == 'Invalid message data'


@patch('src.socketio_handlers.messages.emit')
@patch('src.socketio_handlers.messages.sio_conn_users')
@patch('src.socketio_handlers.messages.db')
@patch('src.socketio_handlers.messages.Message')
def test_get_messages_history(mock_message_cls, mock_db, mock_sio_users, mock_emit, test_client):
    """Test pobierania historii wiadomości i oznaczania jako przeczytane"""
    mock_sio_users.is_authenticated.return_value = True
    sender_id = 1
    recipient_id = 2
    mock_sio_users.get_sender_id.return_value = sender_id

    mock_history = {
        'messages': [
            {'id': 10, 'recipient_id': sender_id, 'is_delivered': False, 'content': 'msg1'},
            {'id': 11, 'recipient_id': recipient_id, 'is_delivered': False, 'content': 'msg2'}
        ],
        'total': 2
    }
    mock_message_cls.query_messages_between.return_value = mock_history

    mock_recipient = MagicMock()
    mock_recipient.is_active = True
    mock_db.session.get.return_value = mock_recipient

    test_client.emit('get_messages', {'recipient_id': recipient_id})

    mock_emit.assert_any_call('messages_history', mock_history)

    assert mock_db.session.query.return_value.filter_by.return_value.update.called
    mock_db.session.commit.assert_called()


@patch('src.socketio_handlers.messages.emit')
@patch('src.socketio_handlers.messages.sio_conn_users')
@patch('src.socketio_handlers.messages.Message')
def test_get_recent_and_available_users(mock_message_cls, mock_sio_users, mock_emit, test_client):
    """Test pobierania listy użytkowników"""
    mock_sio_users.is_authenticated.return_value = True
    mock_sio_users.get_sender_id.return_value = 1

    expected_result = {
        'recent_users': [{'id': 2, 'last_msg': 'date'}],
        'available_users': [3, 4, 5]
    }
    mock_message_cls.query_recent_and_available_users.return_value = expected_result

    test_client.emit('get_recent_and_available_users', {})

    mock_emit.assert_called_with('recent_and_available_users', expected_result)
