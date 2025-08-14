"""
Authentication router for user management and JWT tokens
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import logging

from core.database import get_db
from core.security import security_manager, get_current_user, get_current_active_user
from models.user import User, UserSession
from models.organization import Organization
from models.audit_log import AuditLog
from schemas.auth import (
    LoginRequest, LoginResponse, TokenRefresh, PasswordChange,
    PasswordReset, PasswordResetConfirm, UserCreate, UserResponse,
    UserUpdate, UserProfile, LogoutRequest, AccountVerification,
    OrganizationCreate, OrganizationResponse
)

logger = logging.getLogger(__name__)

router = APIRouter()
security = HTTPBearer()


@router.post("/login", response_model=LoginResponse)
async def login(
    login_data: LoginRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """Authenticate user and return access tokens"""
    try:
        # Find user by username or email
        user = db.query(User).filter(
            (User.username == login_data.username) | 
            (User.email == login_data.username)
        ).first()
        
        if not user:
            # Log failed login attempt
            AuditLog.log_event(
                event_type="login_failed",
                event_category="auth",
                action="User login attempt with invalid username",
                description=f"Failed login attempt for username: {login_data.username}",
                ip_address=request.client.host,
                user_agent=request.headers.get("user-agent"),
                status="failure"
            )
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )
        
        # Verify password
        if not security_manager.verify_password(login_data.password, user.hashed_password):
            # Increment failed login attempts
            user.failed_login_attempts += 1
            db.commit()
            
            # Log failed login
            AuditLog.log_event(
                event_type="login_failed",
                event_category="auth",
                action="User login attempt with invalid password",
                user_id=user.id,
                description=f"Failed login attempt for user: {user.username}",
                ip_address=request.client.host,
                user_agent=request.headers.get("user-agent"),
                status="failure"
            )
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )
        
        # Check if user is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is inactive"
            )
        
        # Reset failed login attempts and update last login
        user.failed_login_attempts = 0
        user.last_login_at = datetime.utcnow()
        
        # Create access and refresh tokens
        access_token = security_manager.create_access_token(
            data={"sub": user.username, "user_id": user.id}
        )
        refresh_token = security_manager.create_refresh_token(
            data={"sub": user.username, "user_id": user.id}
        )
        
        # Create user session record
        session = UserSession(
            user_id=user.id,
            session_token=access_token[:50],  # Store truncated token for reference
            refresh_token=refresh_token[:50],
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent"),
            expires_at=datetime.utcnow() + timedelta(minutes=30)
        )
        db.add(session)
        db.commit()
        
        # Log successful login
        AuditLog.log_event(
            event_type="login_success",
            event_category="auth",
            action="User logged in successfully",
            user_id=user.id,
            description=f"Successful login for user: {user.username}",
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent"),
            session_id=str(session.id),
            status="success"
        )
        
        return LoginResponse(
            user=UserProfile.from_orm(user),
            token={
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "expires_in": 1800  # 30 minutes
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@router.post("/refresh")
async def refresh_token(
    token_data: TokenRefresh,
    db: Session = Depends(get_db)
):
    """Refresh access token using refresh token"""
    try:
        # Verify refresh token
        token_info = security_manager.verify_token(token_data.refresh_token, "refresh")
        
        if not token_info:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        # Find user
        user = db.query(User).filter(User.username == token_info.username).first()
        
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        # Create new access token
        access_token = security_manager.create_access_token(
            data={"sub": user.username, "user_id": user.id}
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": 1800
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )


@router.post("/logout")
async def logout(
    logout_data: LogoutRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Logout user and invalidate session"""
    try:
        # Find and deactivate user sessions
        sessions = db.query(UserSession).filter(
            UserSession.user_id == current_user.id,
            UserSession.is_active == True
        ).all()
        
        for session in sessions:
            session.is_active = False
            session.ended_at = datetime.utcnow()
        
        db.commit()
        
        # Log logout
        AuditLog.log_event(
            event_type="logout",
            event_category="auth",
            action="User logged out",
            user_id=current_user.id,
            description=f"User {current_user.username} logged out",
            status="success"
        )
        
        return {"message": "Successfully logged out"}
    
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )


@router.get("/me", response_model=UserProfile)
async def get_current_user_profile(
    current_user: User = Depends(get_current_active_user)
):
    """Get current user profile"""
    return UserProfile.from_orm(current_user)


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update current user profile"""
    try:
        # Store old values for audit
        old_values = {
            "first_name": current_user.first_name,
            "last_name": current_user.last_name,
            "phone": current_user.phone
        }
        
        # Update user fields
        for field, value in user_update.dict(exclude_unset=True).items():
            if hasattr(current_user, field):
                setattr(current_user, field, value)
        
        current_user.updated_at = datetime.utcnow()
        db.commit()
        
        # Log profile update
        AuditLog.log_event(
            event_type="update",
            event_category="data",
            action="User profile updated",
            user_id=current_user.id,
            resource_type="user",
            resource_id=str(current_user.id),
            old_values=old_values,
            new_values=user_update.dict(exclude_unset=True),
            status="success"
        )
        
        return UserResponse.from_orm(current_user)
    
    except Exception as e:
        logger.error(f"User update error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User update failed"
        )


@router.post("/change-password")
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Change user password"""
    try:
        # Verify current password
        if not security_manager.verify_password(password_data.current_password, current_user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        # Hash new password
        new_hashed_password = security_manager.get_password_hash(password_data.new_password)
        
        # Update password
        current_user.hashed_password = new_hashed_password
        current_user.password_changed_at = datetime.utcnow()
        current_user.updated_at = datetime.utcnow()
        db.commit()
        
        # Invalidate all user sessions (force re-login)
        sessions = db.query(UserSession).filter(
            UserSession.user_id == current_user.id,
            UserSession.is_active == True
        ).all()
        
        for session in sessions:
            session.is_active = False
            session.ended_at = datetime.utcnow()
        
        db.commit()
        
        # Log password change
        AuditLog.log_event(
            event_type="password_change",
            event_category="auth",
            action="User changed password",
            user_id=current_user.id,
            description=f"Password changed for user: {current_user.username}",
            status="success"
        )
        
        return {"message": "Password changed successfully. Please log in again."}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password change error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password change failed"
        )


@router.post("/register", response_model=UserResponse)
async def register_user(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """Register new user (public endpoint)"""
    try:
        # Check if username already exists
        existing_user = db.query(User).filter(
            (User.username == user_data.username) | 
            (User.email == user_data.email)
        ).first()
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username or email already registered"
            )
        
        # Check if organization exists
        organization = db.query(Organization).filter(
            Organization.id == user_data.organization_id
        ).first()
        
        if not organization:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid organization"
            )
        
        # Hash password
        hashed_password = security_manager.get_password_hash(user_data.password)
        
        # Create user
        user = User(
            username=user_data.username,
            email=user_data.email,
            hashed_password=hashed_password,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            phone=user_data.phone,
            role=user_data.role,
            organization_id=user_data.organization_id,
            is_active=True,  # Or False if email verification required
            is_verified=False
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        # Log user registration
        AuditLog.log_event(
            event_type="create",
            event_category="data",
            action="User registered",
            user_id=user.id,
            resource_type="user",
            resource_id=str(user.id),
            description=f"New user registered: {user.username}",
            status="success"
        )
        
        return UserResponse.from_orm(user)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"User registration error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User registration failed"
        )


@router.post("/organizations", response_model=OrganizationResponse)
async def create_organization(
    org_data: OrganizationCreate,
    db: Session = Depends(get_db)
):
    """Create new organization (public endpoint)"""
    try:
        # Check if organization name already exists
        existing_org = db.query(Organization).filter(
            Organization.name == org_data.name
        ).first()
        
        if existing_org:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Organization name already exists"
            )
        
        # Create organization
        organization = Organization(**org_data.dict())
        
        db.add(organization)
        db.commit()
        db.refresh(organization)
        
        # Log organization creation
        AuditLog.log_event(
            event_type="create",
            event_category="data",
            action="Organization created",
            resource_type="organization",
            resource_id=str(organization.id),
            description=f"New organization created: {organization.name}",
            status="success"
        )
        
        return OrganizationResponse.from_orm(organization)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Organization creation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Organization creation failed"
        )


@router.post("/reset-password")
async def request_password_reset(
    reset_data: PasswordReset,
    db: Session = Depends(get_db)
):
    """Request password reset (send reset email)"""
    try:
        # Find user by email
        user = db.query(User).filter(User.email == reset_data.email).first()
        
        if not user:
            # Don't reveal if email exists or not
            return {"message": "If the email exists, a reset link has been sent"}
        
        # Generate reset token (simplified - in production, use secure token)
        import secrets
        reset_token = secrets.token_urlsafe(32)
        
        # Store reset token
        user.reset_token = reset_token
        user.reset_token_expires = datetime.utcnow() + timedelta(hours=1)
        db.commit()
        
        # Log password reset request
        AuditLog.log_event(
            event_type="password_reset_request",
            event_category="auth",
            action="Password reset requested",
            user_id=user.id,
            description=f"Password reset requested for user: {user.username}",
            status="success"
        )
        
        # TODO: Send email with reset link
        # For now, just return success message
        return {"message": "If the email exists, a reset link has been sent"}
    
    except Exception as e:
        logger.error(f"Password reset request error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password reset request failed"
        )


@router.post("/reset-password/confirm")
async def confirm_password_reset(
    reset_data: PasswordResetConfirm,
    db: Session = Depends(get_db)
):
    """Confirm password reset with token"""
    try:
        # Find user with valid reset token
        user = db.query(User).filter(
            User.reset_token == reset_data.token,
            User.reset_token_expires > datetime.utcnow()
        ).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token"
            )
        
        # Hash new password
        new_hashed_password = security_manager.get_password_hash(reset_data.new_password)
        
        # Update password and clear reset token
        user.hashed_password = new_hashed_password
        user.password_changed_at = datetime.utcnow()
        user.reset_token = None
        user.reset_token_expires = None
        user.updated_at = datetime.utcnow()
        
        # Invalidate all user sessions
        sessions = db.query(UserSession).filter(
            UserSession.user_id == user.id,
            UserSession.is_active == True
        ).all()
        
        for session in sessions:
            session.is_active = False
            session.ended_at = datetime.utcnow()
        
        db.commit()
        
        # Log password reset completion
        AuditLog.log_event(
            event_type="password_reset_complete",
            event_category="auth",
            action="Password reset completed",
            user_id=user.id,
            description=f"Password reset completed for user: {user.username}",
            status="success"
        )
        
        return {"message": "Password reset successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password reset confirmation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password reset confirmation failed"
        )


@router.get("/sessions")
async def get_user_sessions(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get user's active sessions"""
    try:
        sessions = db.query(UserSession).filter(
            UserSession.user_id == current_user.id,
            UserSession.is_active == True
        ).order_by(UserSession.created_at.desc()).all()
        
        session_data = []
        for session in sessions:
            session_data.append({
                "id": session.id,
                "ip_address": session.ip_address,
                "user_agent": session.user_agent,
                "created_at": session.created_at,
                "last_activity": session.last_activity,
                "expires_at": session.expires_at
            })
        
        return {"sessions": session_data}
    
    except Exception as e:
        logger.error(f"Get sessions error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve sessions"
        )