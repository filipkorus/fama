from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '001_file_signature_feature'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=80), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('public_key', sa.Text(), nullable=False),
        sa.Column('dilithium_public_key', sa.Text(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_users_username', 'users', ['username'], unique=True)

    # Create refresh_tokens table
    op.create_table(
        'refresh_tokens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('jti', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('revoked', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_refresh_tokens_jti', 'refresh_tokens', ['jti'], unique=True)

    # Create encrypted_session_keys table
    op.create_table(
        'encrypted_session_keys',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('sender_id', sa.Integer(), nullable=False),
        sa.Column('recipient_id', sa.Integer(), nullable=False),
        sa.Column('capsule_mlkem', sa.Text(), nullable=False),
        sa.Column('encrypted_shared_secret', sa.Text(), nullable=False),
        sa.Column('key_nonce', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['sender_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['recipient_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create messages table with message_type field
    op.create_table(
        'messages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('sender_id', sa.Integer(), nullable=False),
        sa.Column('recipient_id', sa.Integer(), nullable=False),
        sa.Column('session_key_id', sa.Integer(), nullable=False),
        sa.Column('message_type', sa.String(length=20), nullable=False, server_default='text'),
        sa.Column('encrypted_content', sa.Text(), nullable=False),
        sa.Column('nonce', sa.Text(), nullable=False),
        sa.Column('is_delivered', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['sender_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['recipient_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['session_key_id'], ['encrypted_session_keys.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_messages_created_at', 'messages', ['created_at'], unique=False)

    # Create uploaded_files table
    op.create_table(
        'uploaded_files',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('original_size', sa.Integer(), nullable=False),
        sa.Column('file_hash', sa.String(length=64), nullable=False),
        sa.Column('uploader_id', sa.Integer(), nullable=False),
        sa.Column('uploaded_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['uploader_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_uploaded_files_filename', 'uploaded_files', ['filename'], unique=True)
    op.create_index('ix_uploaded_files_uploader_id', 'uploaded_files', ['uploader_id'], unique=False)


def downgrade():
    # Drop tables in reverse order
    op.drop_index('ix_uploaded_files_uploader_id', table_name='uploaded_files')
    op.drop_index('ix_uploaded_files_filename', table_name='uploaded_files')
    op.drop_table('uploaded_files')

    op.drop_index('ix_messages_created_at', table_name='messages')
    op.drop_table('messages')

    op.drop_table('encrypted_session_keys')

    op.drop_index('ix_refresh_tokens_jti', table_name='refresh_tokens')
    op.drop_table('refresh_tokens')

    op.drop_index('ix_users_username', table_name='users')
    op.drop_table('users')
