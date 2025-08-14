"""Security utilities for JWT authentication and authorization."""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import secrets
from cryptography.fernet import Fernet
import base64
import os

from core.config import settings
from models.user import User, UserApiKey

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Encryption for API keys
if settings.KMS_KEY_ID:
    # In production, use AWS KMS
    # This is a placeholder - actual KMS integration would go here
    fernet_key = base64.urlsafe_b64encode(secrets.token_bytes(32))
else:
    # For development, use a local key
    fernet_key = base64.urlsafe_b64encode(secrets.token_bytes(32))

cipher = Fernet(fernet_key)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=settings.JWT_EXPIRATION_HOURS)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError:
        raise ValueError("Invalid token")


def encrypt_api_key(api_key: str) -> str:
    """Encrypt an API key for storage."""
    return cipher.encrypt(api_key.encode()).decode()


def decrypt_api_key(encrypted_key: str) -> str:
    """Decrypt an API key."""
    return cipher.decrypt(encrypted_key.encode()).decode()


async def get_current_user(db: AsyncSession, token: str) -> Optional[User]:
    """Get the current user from a JWT token."""
    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        if not user_id:
            return None
        
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        return user
    except Exception:
        return None


async def verify_org_access(user: User, org_id: str) -> bool:
    """Verify that a user has access to an organization."""
    return str(user.org_id) == org_id


def check_permission(user: User, permission: str) -> bool:
    """Check if a user has a specific permission based on their role."""
    role_permissions = {
        "owner": ["*"],  # All permissions
        "admin": [
            "read:*", "write:*", "delete:*",
            "manage:users", "manage:searches", "manage:exports"
        ],
        "member": [
            "read:parcels", "read:searches", "write:searches",
            "read:exports", "write:exports"
        ]
    }
    
    user_permissions = role_permissions.get(user.role, [])
    
    # Check for wildcard permission
    if "*" in user_permissions:
        return True
    
    # Check for exact match or wildcard match
    for user_perm in user_permissions:
        if user_perm == permission:
            return True
        if user_perm.endswith(":*"):
            perm_prefix = user_perm[:-2]
            if permission.startswith(perm_prefix + ":"):
                return True
    
    return False


def generate_api_key() -> str:
    """Generate a secure API key."""
    return secrets.token_urlsafe(32)


async def validate_nextauth_token(token: str) -> Optional[Dict[str, Any]]:
    """Validate a NextAuth JWT token."""
    try:
        # NextAuth uses a different secret for signing
        payload = jwt.decode(
            token, 
            settings.NEXTAUTH_SECRET, 
            algorithms=["HS256"]
        )
        return payload
    except JWTError:
        return None