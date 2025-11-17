from ..models import User


class SocketIOConnectedUsersManager:
    """
    Singleton class to manage connected users in the Socket.IO server.
    Maps user IDs to their corresponding socket session IDs.
    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(SocketIOConnectedUsersManager, cls).__new__(cls, *args, **kwargs)
            cls._instance._connected_users = {}
            cls._instance._usernames = {}
        return cls._instance

    def add_user(self, user_id, sid):
        """Add a user to the connected users map."""
        self._connected_users[user_id] = sid
        username = User.get_username_by_userid(user_id)
        self._usernames[user_id] = username

    def remove_user(self, sid):
        """Remove a user from the connected users map."""
        user_id = self.get_sender_id(sid)
        if user_id:
            self._connected_users.pop(user_id, None)
            self._usernames.pop(user_id, None)

    def get_sender_id(self, sid):
        """Get the user ID associated with a given socket session ID."""
        return next((user_id for user_id, session_id in self._connected_users.items() if session_id == sid), None)

    def get_sender_sid(self, user_id):
        """Get the socket session ID associated with a given user ID."""
        return self._connected_users.get(user_id)

    def is_authenticated(self, sid):
        """Check if a socket session ID is associated with any user."""
        return sid in self._connected_users.values()

    def get_username_by_userid(self, user_id):
        """Get the username associated with a given user ID."""
        return self._usernames.get(user_id)
