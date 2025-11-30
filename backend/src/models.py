from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone

from .database import db


def to_utc_z(dt):
    """Convert any datetime to UTC and format as 2023-11-28T10:00:00Z"""
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class User(db.Model):
    """User model for storing user information"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    public_key = db.Column(db.Text, nullable=False)  # ML-KEM public key (Base64)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<User {self.username}>'

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @staticmethod
    def get_username_by_userid(user_id):
        user = db.session.get(User, user_id)
        return user.username if user else None

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'public_key': self.public_key,
            'is_active': self.is_active,
            'created_at': to_utc_z(self.created_at)
        }


class RefreshToken(db.Model):
    """Model for storing refresh tokens"""
    __tablename__ = 'refresh_tokens'

    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(36), nullable=False, unique=True, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    revoked = db.Column(db.Boolean, nullable=False, default=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    user = db.relationship('User', backref=db.backref('refresh_tokens', lazy=True, cascade="all, delete"))

    def __repr__(self):
        return f'<RefreshToken {self.jti}>'


class EncryptedSessionKey(db.Model):
    """
    Model for storing the Shared Secret (AES Key) used for a conversation.
    """
    __tablename__ = 'encrypted_session_keys'

    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)

    capsule_mlkem = db.Column(db.Text, nullable=False)
    encrypted_shared_secret = db.Column(db.Text, nullable=False)
    key_nonce = db.Column(db.Text, nullable=False)

    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id': self.id,
            'sender_id': self.sender_id,
            'recipient_id': self.recipient_id,
            'capsule_mlkem': self.capsule_mlkem,
            'encrypted_shared_secret': self.encrypted_shared_secret,
            'key_nonce': self.key_nonce,
            'created_at': to_utc_z(self.created_at)
        }


class Message(db.Model):
    """Model for encrypted messages in 1:1 chats"""
    __tablename__ = 'messages'

    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)

    session_key_id = db.Column(db.Integer, db.ForeignKey('encrypted_session_keys.id'), nullable=False)

    encrypted_content = db.Column(db.Text, nullable=False)
    nonce = db.Column(db.Text, nullable=False)

    is_delivered = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)

    sender = db.relationship('User', foreign_keys=[sender_id], backref=db.backref('sent_messages', lazy=True))
    recipient = db.relationship('User', foreign_keys=[recipient_id], backref=db.backref('received_messages', lazy=True))
    session_key = db.relationship('EncryptedSessionKey', backref=db.backref('messages', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'sender_id': self.sender_id,
            'recipient_id': self.recipient_id,
            'session_key_id': self.session_key_id,
            'encrypted_content': self.encrypted_content,
            'nonce': self.nonce,
            'is_delivered': self.is_delivered,
            'created_at': to_utc_z(self.created_at),
            'sender': {
                'id': self.sender.id,
                'username': self.sender.username
            }
        }

    @staticmethod
    def query_messages_between(sender_id, recipient_id, limit=None, offset=None):
        query = Message.query.filter(
            ((Message.sender_id == sender_id) & (Message.recipient_id == recipient_id)) |
            ((Message.sender_id == recipient_id) & (Message.recipient_id == sender_id))
        ).order_by(Message.created_at.desc())

        total_count = query.count()

        if offset is not None:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)

        paginated_messages = query.all()

        return {
            'messages': [
                {
                    'id': msg.id,
                    'recipient_id': msg.recipient_id,
                    'session_key_id': msg.session_key_id,
                    'encrypted_content': msg.encrypted_content,
                    'nonce': msg.nonce,
                    'is_delivered': msg.is_delivered,
                    'created_at': to_utc_z(msg.created_at),
                    'sender': {
                        'id': msg.sender.id,
                        'username': msg.sender.username,
                    },
                    'recipient': {
                        'id': msg.recipient.id,
                        'username': msg.recipient.username
                    }
                }
                for msg in paginated_messages
            ],
            'count': len(paginated_messages),
            'total': total_count,
            'offset': offset,
            'limit': limit,
            'has_more': offset + len(paginated_messages) < total_count if offset is not None else len(paginated_messages) < total_count
        }

    def mark_as_delivered(self):
        self.is_delivered = True
        db.session.commit()

    @staticmethod
    def query_recent_and_available_users(sender_id):
        recent_messages = (
            db.session.query(
                Message.recipient_id,
                User.username,
                User.public_key,
                db.func.max(Message.created_at).label('last_message_date')
            )
            .join(User, User.id == Message.recipient_id)
            .filter(Message.sender_id == sender_id)
            .group_by(Message.recipient_id, User.username, User.public_key)
            .order_by(db.func.max(Message.created_at).desc())
            .all()
        )

        recent_users = [
            {
                'id': recipient_id,
                'username': username,
                'public_key': public_key,
                'last_message_date': to_utc_z(last_message_date) if last_message_date else None
            }
            for recipient_id, username, public_key, last_message_date in recent_messages
        ]

        all_users = db.session.query(User.id, User.username, User.public_key).filter(User.is_active == True).all()

        all_user_objects = [
            {
                'id': user.id,
                'username': user.username,
                'public_key': user.public_key
            }
            for user in all_users
        ]

        recent_user_ids = {user['id'] for user in recent_users}
        available_users = [user for user in all_user_objects if user['id'] not in recent_user_ids and user['id'] != sender_id]

        return {
            'recent_users': recent_users,
            'available_users': available_users
        }
