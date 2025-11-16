"""
User Management API endpoints
Handles user search and public key queries
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from database import db
from models import User

users_bp = Blueprint('users', __name__, url_prefix='/api/users')


@users_bp.route('/search', methods=['GET'])
@jwt_required()
def search_users():
    """
    Search for users by username with pagination

    Headers:
        Authorization: Bearer <access_token>

    Query Parameters:
        query: Username search query (required, min 2 characters)
        page: Page number (optional, default 1)
        per_page: Results per page (optional, default 10, max 50)

    Returns:
        200: List of users matching search query with pagination metadata
        400: Invalid query parameters
        401: Invalid access token
        500: Internal server error
    """
    try:
        query = request.args.get('query', '').strip()
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)

        if not query:
            return jsonify({'error': 'Query parameter is required'}), 400

        if len(query) < 2:
            return jsonify({'error': 'Query must be at least 2 characters long'}), 400

        if page < 1:
            page = 1

        if per_page < 1 or per_page > 50:
            per_page = 10

        # Search for users by username (case-insensitive partial match)
        users_query = User.query.filter(
            User.username.ilike(f'%{query}%')
        )

        # Get total count for pagination
        total_count = users_query.count()
        total_pages = (total_count + per_page - 1) // per_page  # Ceiling division

        # Apply pagination
        users = users_query.offset((page - 1) * per_page).limit(per_page).all()

        # Get public keys for each user
        results = []
        for user in users:
            user_data = {
                'user_id': user.id,
                'username': user.username,
                'public_key': user.public_key
            }
            results.append(user_data)

        return jsonify({
            'users': results,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total_count': total_count,
                'total_pages': total_pages,
                'has_next': page < total_pages,
                'has_prev': page > 1
            }
        }), 200

    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500


@users_bp.route('/<int:user_id>/public-key', methods=['GET'])
@jwt_required()
def get_user_public_key(user_id):
    """
    Get public key for a specific user

    Headers:
        Authorization: Bearer <access_token>

    Path Parameters:
        user_id: User ID (integer)

    Returns:
        200: User's public key
        401: Invalid access token
        404: User not found
        500: Internal server error
    """
    try:
        user = db.session.get(User, user_id)

        if not user:
            return jsonify({'error': 'User not found'}), 404

        return jsonify({
            'user_id': user.id,
            'username': user.username,
            'public_key': user.public_key
        }), 200

    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500


@users_bp.route('/<username>/public-key', methods=['GET'])
@jwt_required()
def get_user_public_key_by_username(username):
    """
    Get public key for a specific user by username

    Headers:
        Authorization: Bearer <access_token>

    Path Parameters:
        username: Username (string)

    Returns:
        200: User's public key
        401: Invalid access token
        404: User not found
        500: Internal server error
    """
    try:
        user = User.query.filter_by(username=username).first()

        if not user:
            return jsonify({'error': 'User not found'}), 404

        return jsonify({
            'user_id': user.id,
            'username': user.username,
            'public_key': user.public_key
        }), 200

    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500
