"""
User model for authentication and authorization
"""

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text, Enum, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
from core.database import Base
import enum


class UserRole(enum.Enum):
    """User roles enum"""
    owner = "owner"
    admin = "admin"
    member = "member"


class User(Base):
    """User model for application authentication"""
    
    __tablename__ = "users"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4(), index=True)
    
    # Organization relationship
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True)
    
    # Authentication
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=True)  # Nullable for OAuth users
    
    # Profile information
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    phone = Column(String(50), nullable=True)
    profile_image = Column(String(500), nullable=True)
    
    # OAuth integration
    oauth_provider = Column(String(50), nullable=True)  # 'google', 'azure-ad', etc.
    oauth_provider_id = Column(String(255), nullable=True)  # Provider's user ID
    
    # Role and permissions
    role = Column(Enum(UserRole), default=UserRole.member, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    
    # Profile settings
    profile_settings = Column(Text, nullable=True)  # JSON string for user preferences
    
    # Security
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    password_changed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Verification tokens
    verification_token = Column(String(255), nullable=True)
    reset_token = Column(String(255), nullable=True)
    reset_token_expires = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    organization = relationship("Organization", back_populates="users")
    api_keys = relationship("UserApiKey", back_populates="user", cascade="all, delete-orphan")
    searches = relationship("Search", back_populates="user", cascade="all, delete-orphan")
    exports = relationship("Export", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user")
    
    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"
    
    @property
    def full_name(self):
        """Get user's full name"""
        return f"{self.first_name} {self.last_name}"
    
    @property
    def is_admin(self):
        """Check if user is admin"""
        return self.role == UserRole.admin
    
    @property
    def is_owner(self):
        """Check if user is owner"""
        return self.role == UserRole.owner


class UserApiKey(Base):
    """User API keys for programmatic access"""
    
    __tablename__ = "user_api_keys"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4(), index=True)
    
    # Multi-tenant
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    # API key details
    name = Column(String(255), nullable=False)
    key_hash = Column(String(255), nullable=False, unique=True, index=True)
    key_prefix = Column(String(10), nullable=False)  # First few chars for identification
    
    # Permissions and limits
    scopes = Column(Text, nullable=True)  # JSON array of scopes
    rate_limit = Column(String(50), nullable=True)  # e.g., "1000/hour"
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="api_keys")
    organization = relationship("Organization")
    
    def __repr__(self):
        return f"<UserApiKey(id={self.id}, name='{self.name}', user_id={self.user_id})>"