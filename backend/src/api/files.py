"""
File Transfer API endpoints
Handles encrypted file uploads and downloads for E2EE chat attachments
"""

from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
import os
import hashlib
import uuid
from datetime import datetime, timezone
from logging import getLogger

from ..models import User, UploadedFile
from ..database import db
from ..config import Config

files_bp = Blueprint('files', __name__, url_prefix='/api/files')
logger = getLogger('app')

def ensure_upload_folder():
    """Ensure the upload folder exists"""
    if not os.path.exists(Config.UPLOAD_FOLDER):
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)

def generate_unique_filename():
    """Generate a unique filename using UUID"""
    return f"{uuid.uuid4().hex}.enc"


@files_bp.route('/upload', methods=['POST'])
@jwt_required()
def upload_file():
    """
    Upload an encrypted file

    This endpoint receives an encrypted file blob that contains:
    - Digital signature (Dilithium)
    - Metadata JSON
    - File content
    All encrypted with a one-time AES key

    Request (multipart/form-data):
        - file: Binary encrypted blob

    Returns:
        200: File uploaded successfully with URL and hash
        400: Invalid request (no file, file too large)
        401: Unauthorized
        500: Internal server error
    """
    try:
        user_id = get_jwt_identity()
        user = db.session.get(User, int(user_id))

        if not user:
            return jsonify({'error': 'User not found'}), 401

        # Check if file is present in request
        if 'file' not in request.files:
            return jsonify({'error': 'No file part in request'}), 400

        file = request.files['file']

        # Check if file was actually selected
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        # Check file size
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)

        if file_size > Config.MAX_FILE_SIZE:
            return jsonify({'error': f'File too large. Maximum size: {Config.MAX_FILE_SIZE} bytes'}), 400

        if file_size == 0:
            return jsonify({'error': 'File is empty'}), 400

        # Generate unique filename
        ensure_upload_folder()
        filename = generate_unique_filename()
        file_path = os.path.join(Config.UPLOAD_FOLDER, filename)

        # Save encrypted file
        file.save(file_path)

        # Calculate SHA-256 hash of the encrypted file (for integrity verification)
        file_hash = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                file_hash.update(chunk)

        file_hash_hex = file_hash.hexdigest()

        # Generate URL for file access
        file_url = f"/api/files/download/{filename}"

        # Save file metadata to database
        uploaded_file = UploadedFile(
            filename=filename,
            original_size=file_size,
            file_hash=file_hash_hex,
            uploader_id=user.id
        )
        db.session.add(uploaded_file)
        db.session.commit()

        logger.info(f"File uploaded: {filename} by user {user.username} (size: {file_size} bytes)")

        return jsonify({
            'url': file_url,
            'filename': filename,
            'size': file_size,
            'hash': file_hash_hex,
            'uploaded_at': datetime.now(timezone.utc).isoformat()
        }), 200

    except Exception as e:
        logger.error(f"File upload error: {str(e)}")
        return jsonify({'error': 'Failed to upload file'}), 500


@files_bp.route('/download/<filename>', methods=['GET'])
@jwt_required()
def download_file(filename):
    """
    Download an encrypted file

    This endpoint serves encrypted file blobs that were previously uploaded.
    The file remains encrypted on the server and during transfer.

    Path Parameters:
        filename: The unique filename returned from upload

    Returns:
        200: File content (binary)
        401: Unauthorized
        404: File not found
        500: Internal server error
    """
    try:
        user_id = get_jwt_identity()
        user = db.session.get(User, int(user_id))

        if not user:
            return jsonify({'error': 'User not found'}), 401

        # Check if file exists in database
        uploaded_file = UploadedFile.query.filter_by(filename=filename).first()
        if not uploaded_file:
            return jsonify({'error': 'File not found'}), 404

        safe_filename = secure_filename(filename)
        if safe_filename != filename:
            logger.warning(f"Potential directory traversal attempt: {filename} by user {user.username}")
            return jsonify({'error': 'Invalid filename'}), 400

        file_path = os.path.join(Config.UPLOAD_FOLDER, safe_filename)

        # Check if file exists
        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404

        # Check if path is actually within upload folder (prevent directory traversal)
        real_upload_folder = os.path.realpath(Config.UPLOAD_FOLDER)
        real_file_path = os.path.realpath(file_path)

        if not real_file_path.startswith(real_upload_folder):
            logger.warning(f"Directory traversal attempt detected: {filename} by user {user.username}")
            return jsonify({'error': 'Access denied'}), 403

        logger.info(f"File downloaded: {filename} by user {user.username}")

        # Send file as binary with application/octet-stream
        return send_file(
            file_path,
            mimetype='application/octet-stream',
            as_attachment=True,
            download_name=safe_filename
        )

    except Exception as e:
        logger.error(f"File download error: {str(e)}")
        return jsonify({'error': 'Failed to download file'}), 500


@files_bp.route('/delete/<filename>', methods=['DELETE'])
@jwt_required()
def delete_file(filename):
    """
    Delete an encrypted file

    This endpoint allows users to delete files they have uploaded.
    Note: In production, you may want to implement access control to ensure
    only the uploader or authorized recipients can delete files.

    Path Parameters:
        filename: The unique filename to delete

    Returns:
        200: File deleted successfully
        401: Unauthorized
        404: File not found
        500: Internal server error
    """
    try:
        user_id = get_jwt_identity()
        user = db.session.get(User, int(user_id))

        if not user:
            return jsonify({'error': 'User not found'}), 401

        # Check if file exists in database
        uploaded_file = UploadedFile.query.filter_by(filename=filename).first()
        if not uploaded_file:
            return jsonify({'error': 'File not found'}), 404

        # Only uploader can delete the file
        if uploaded_file.uploader_id != user.id:
            logger.warning(f"Unauthorized delete attempt: {filename} by user {user.username}")
            return jsonify({'error': 'Access denied'}), 403

        # Sanitize filename
        safe_filename = secure_filename(filename)
        if safe_filename != filename:
            return jsonify({'error': 'Invalid filename'}), 400

        file_path = os.path.join(Config.UPLOAD_FOLDER, safe_filename)

        # Check if file exists
        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404

        # Check for directory traversal
        real_upload_folder = os.path.realpath(Config.UPLOAD_FOLDER)
        real_file_path = os.path.realpath(file_path)

        if not real_file_path.startswith(real_upload_folder):
            logger.warning(f"Directory traversal attempt in delete: {filename} by user {user.username}")
            return jsonify({'error': 'Access denied'}), 403

        # Delete the file
        os.remove(file_path)

        # Delete the database record
        db.session.delete(uploaded_file)
        db.session.commit()

        logger.info(f"File deleted: {filename} by user {user.username}")

        return jsonify({
            'message': 'File deleted successfully',
            'filename': safe_filename
        }), 200

    except Exception as e:
        logger.error(f"File deletion error: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to delete file'}), 500
