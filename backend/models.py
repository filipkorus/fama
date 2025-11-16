from datetime import datetime, timezone
from database import db
from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Model):
    """User model for storing user information"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    public_key = db.Column(db.Text, nullable=False)  # ML-KEM public key (Base64)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<User {self.username}>'

    def set_password(self, password):
        """Hash and set user password"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verify password against hash"""
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        """Convert user object to dictionary"""
        return {
            'id': self.id,
            'username': self.username,
            'public_key': self.public_key,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


class RefreshToken(db.Model):
    """Model for storing refresh tokens"""
    __tablename__ = 'refresh_tokens'

    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(36), nullable=False, unique=True, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    revoked = db.Column(db.Boolean, nullable=False, default=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    user = db.relationship('User', backref=db.backref('refresh_tokens', lazy=True))

    def __repr__(self):
        return f'<RefreshToken {self.jti}>'


# Association table for many-to-many relationship between Room and User
room_participants = db.Table('room_participants',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('room_id', db.Integer, db.ForeignKey('rooms.id'), primary_key=True),
    db.Column('joined_at', db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
)


class Room(db.Model):
    """Model for chat rooms"""
    __tablename__ = 'rooms'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=True)  # Optional room name
    is_group = db.Column(db.Boolean, nullable=False, default=False)  # True for group chats, False for 1-on-1
    current_key_version = db.Column(db.Integer, nullable=False, default=1)  # Current version of symmetric key
    rotation_pending = db.Column(db.Boolean, nullable=False, default=False)  # Flag set when rotation is required
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    participants = db.relationship('User', secondary=room_participants, backref=db.backref('rooms', lazy='dynamic'))
    messages = db.relationship('Message', backref='room', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Room {self.id} ({self.name or "Unnamed"})>'

    def to_dict(self, include_participants=False):
        """Convert room object to dictionary"""
        result = {
            'id': self.id,
            'name': self.name,
            'is_group': self.is_group,
            'current_key_version': self.current_key_version,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'participant_count': len(self.participants)
        }

        if include_participants:
            result['participants'] = [
                {'id': user.id, 'username': user.username}
                for user in self.participants
            ]

        return result


class Message(db.Model):
    """Model for encrypted messages in rooms"""
    __tablename__ = 'messages'

    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Nullable for system messages

    # Message type: 'user' or 'system'
    message_type = db.Column(db.String(20), nullable=False, default='user')

    # E2E encryption fields
    encrypted_content = db.Column(db.Text, nullable=False)  # AES encrypted message (Base64)
    iv = db.Column(db.String(24), nullable=False)  # Initialization vector for AES (Base64)
    key_version = db.Column(db.Integer, nullable=False, default=1)  # Version of symmetric key used

    # Metadata
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)

    # Relationships
    sender = db.relationship('User', backref=db.backref('sent_messages', lazy=True))

    def __repr__(self):
        return f'<Message {self.id} in Room {self.room_id}>'

    def to_dict(self):
        """Convert message object to dictionary"""
        result = {
            'id': self.id,
            'room_id': self.room_id,
            'sender_id': self.sender_id,
            'message_type': self.message_type,
            'encrypted_content': self.encrypted_content,
            'iv': self.iv,
            'key_version': self.key_version,
            'created_at': self.created_at.isoformat()
        }

        # Add sender username only for user messages
        if self.message_type == 'user' and self.sender:
            result['sender_username'] = self.sender.username

        return result


class SymmetricKey(db.Model):
    """Model for storing encrypted symmetric keys for each user in a room"""
    __tablename__ = 'symmetric_keys'

    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    key_version = db.Column(db.Integer, nullable=False, default=1)  # Version of the symmetric key

    # Encrypted symmetric key (encrypted with user's ML-KEM public key)
    encrypted_key = db.Column(db.Text, nullable=False)  # Base64 encoded

    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    revoked_at = db.Column(db.DateTime, nullable=True)  # When this key version was revoked

    # Relationships
    room = db.relationship('Room', backref=db.backref('symmetric_keys', lazy=True))
    user = db.relationship('User', backref=db.backref('symmetric_keys', lazy=True))

    # Unique constraint: one encrypted key per room-user-version combination
    __table_args__ = (
        db.UniqueConstraint('room_id', 'user_id', 'key_version', name='_room_user_version_uc'),
    )

    def __repr__(self):
        return f'<SymmetricKey room={self.room_id} user={self.user_id} v={self.key_version}>'

    def to_dict(self):
        """Convert symmetric key object to dictionary"""
        return {
            'id': self.id,
            'room_id': self.room_id,
            'user_id': self.user_id,
            'key_version': self.key_version,
            'encrypted_key': self.encrypted_key,
            'created_at': self.created_at.isoformat(),
            'revoked_at': self.revoked_at.isoformat() if self.revoked_at else None
        }
