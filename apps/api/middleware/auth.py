"""Authentication middleware for FastAPI."""
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import logging

from core.database import AsyncSessionLocal
from core.security import decode_token, validate_nextauth_token
from models.user import User

logger = logging.getLogger(__name__)

security = HTTPBearer()


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware to handle authentication and set RLS context."""
    
    async def dispatch(self, request: Request, call_next):
        """Process each request for authentication."""
        # Skip auth for public endpoints
        public_paths = [
            "/docs", "/redoc", "/openapi.json", "/health",
            "/api/auth/callback", "/api/auth/session"
        ]
        
        if any(request.url.path.startswith(path) for path in public_paths):
            response = await call_next(request)
            return response
        
        # Get token from Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            # Check for NextAuth session cookie
            session_cookie = request.cookies.get("next-auth.session-token") or \
                           request.cookies.get("__Secure-next-auth.session-token")
            
            if not session_cookie:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            # Validate NextAuth token
            payload = await validate_nextauth_token(session_cookie)
            if not payload:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid session"
                )
            
            # Set user context from NextAuth payload
            request.state.user_id = payload.get("sub")
            request.state.org_id = payload.get("org_id")
            request.state.user_email = payload.get("email")
        else:
            # Validate JWT token
            token = auth_header.split(" ")[1]
            try:
                payload = decode_token(token)
                request.state.user_id = payload.get("sub")
                request.state.org_id = payload.get("org_id")
                request.state.user_role = payload.get("role")
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token"
                )
        
        # Set database RLS context
        if hasattr(request.state, "org_id") and request.state.org_id:
            # Store context for database session
            request.state.db_context = {
                "org_id": request.state.org_id,
                "user_id": request.state.user_id
            }
        
        response = await call_next(request)
        return response


async def get_current_user(request: Request) -> dict:
    """Dependency to get the current user from request state."""
    if not hasattr(request.state, "user_id"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    return {
        "id": request.state.user_id,
        "org_id": request.state.org_id,
        "email": getattr(request.state, "user_email", None),
        "role": getattr(request.state, "user_role", None)
    }


async def require_role(required_role: str):
    """Dependency to require a specific role."""
    async def role_checker(request: Request):
        user = await get_current_user(request)
        user_role = user.get("role")
        
        if not user_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Role information missing"
            )
        
        # Role hierarchy: owner > admin > member
        role_hierarchy = {"owner": 3, "admin": 2, "member": 1}
        
        if role_hierarchy.get(user_role, 0) < role_hierarchy.get(required_role, 999):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires {required_role} role"
            )
        
        return user
    
    return role_checker