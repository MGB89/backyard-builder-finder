"""Add OAuth support to users

Revision ID: 002_add_oauth_support
Revises: 001_initial_schema
Create Date: 2024-08-14 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002_add_oauth_support'
down_revision = '001_initial_schema'
branch_labels = None
depends_on = None


def upgrade():
    """Add OAuth fields to users table"""
    # Make first_name and last_name nullable for OAuth users
    op.alter_column('users', 'first_name', nullable=True)
    op.alter_column('users', 'last_name', nullable=True)
    
    # Make hashed_password nullable for OAuth users
    op.alter_column('users', 'hashed_password', nullable=True)
    
    # Add OAuth fields
    op.add_column('users', sa.Column('profile_image', sa.String(500), nullable=True))
    op.add_column('users', sa.Column('oauth_provider', sa.String(50), nullable=True))
    op.add_column('users', sa.Column('oauth_provider_id', sa.String(255), nullable=True))
    
    # Add index for OAuth provider lookups
    op.create_index('idx_users_oauth_provider', 'users', ['oauth_provider', 'oauth_provider_id'])


def downgrade():
    """Remove OAuth support from users table"""
    # Remove OAuth fields
    op.drop_index('idx_users_oauth_provider', 'users')
    op.drop_column('users', 'oauth_provider_id')
    op.drop_column('users', 'oauth_provider')
    op.drop_column('users', 'profile_image')
    
    # Make fields non-nullable again
    op.alter_column('users', 'hashed_password', nullable=False)
    op.alter_column('users', 'last_name', nullable=False)
    op.alter_column('users', 'first_name', nullable=False)