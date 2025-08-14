"""
Admin router for administrative functions and system management
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, List
import logging
from datetime import datetime, timedelta

from core.database import get_db
from core.security import get_current_active_user, require_admin
from models.user import User, UserSession
from models.organization import Organization
from models.parcel import Parcel
from models.property_assessment import PropertyAssessment
from models.audit_log import AuditLog
from schemas.auth import UserCreate, UserResponse, UserUpdate, OrganizationCreate, OrganizationResponse, OrganizationUpdate

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/dashboard")
async def get_admin_dashboard(
    current_user: User = Depends(require_admin()),
    db: Session = Depends(get_db)
):
    """
    Get admin dashboard statistics
    """
    try:
        # Get system statistics
        total_organizations = db.query(Organization).filter(Organization.is_active == True).count()
        total_users = db.query(User).filter(User.is_active == True).count()
        total_parcels = db.query(Parcel).filter(Parcel.is_active == True).count()
        total_assessments = db.query(PropertyAssessment).count()
        
        # Get recent activity (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        
        recent_users = db.query(User).filter(
            User.created_at >= thirty_days_ago,
            User.is_active == True
        ).count()
        
        recent_assessments = db.query(PropertyAssessment).filter(
            PropertyAssessment.created_at >= thirty_days_ago
        ).count()
        
        # Get active sessions
        active_sessions = db.query(UserSession).filter(
            UserSession.is_active == True,
            UserSession.expires_at > datetime.utcnow()
        ).count()
        
        # Get assessment status distribution
        assessment_status_counts = db.query(
            PropertyAssessment.status,
            func.count(PropertyAssessment.id)
        ).group_by(PropertyAssessment.status).all()
        
        assessment_status_stats = {status: count for status, count in assessment_status_counts}
        
        # Get organization sizes
        org_sizes = db.query(
            Organization.name,
            func.count(User.id).label('user_count'),
            func.count(Parcel.id).label('parcel_count')
        ).outerjoin(User).outerjoin(Parcel).group_by(Organization.id, Organization.name).all()
        
        organization_stats = [
            {
                "name": name,
                "user_count": user_count,
                "parcel_count": parcel_count
            }
            for name, user_count, parcel_count in org_sizes
        ]
        
        return {
            "system_stats": {
                "total_organizations": total_organizations,
                "total_users": total_users,
                "total_parcels": total_parcels,
                "total_assessments": total_assessments,
                "active_sessions": active_sessions
            },
            "recent_activity": {
                "new_users_30_days": recent_users,
                "new_assessments_30_days": recent_assessments
            },
            "assessment_status_distribution": assessment_status_stats,
            "organization_stats": organization_stats
        }
    
    except Exception as e:
        logger.error(f"Admin dashboard error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to load admin dashboard"
        )


@router.get("/users", response_model=List[UserResponse])
async def list_all_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    organization_id: Optional[int] = Query(None),
    is_active: Optional[bool] = Query(None),
    role: Optional[str] = Query(None),
    current_user: User = Depends(require_admin()),
    db: Session = Depends(get_db)
):
    """
    List all users (admin only)
    """
    try:
        query = db.query(User)
        
        # Apply filters
        if organization_id:
            query = query.filter(User.organization_id == organization_id)
        
        if is_active is not None:
            query = query.filter(User.is_active == is_active)
        
        if role:
            query = query.filter(User.role == role)
        
        # Get users with pagination
        users = query.order_by(User.created_at.desc()).offset(skip).limit(limit).all()
        
        return [UserResponse.from_orm(user) for user in users]
    
    except Exception as e:
        logger.error(f"List users error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to list users"
        )


@router.post("/users", response_model=UserResponse)
async def create_user_admin(
    user_data: UserCreate,
    current_user: User = Depends(require_admin()),
    db: Session = Depends(get_db)
):
    """
    Create user (admin only)
    """
    try:
        # Check if username/email already exists
        existing_user = db.query(User).filter(
            (User.username == user_data.username) | 
            (User.email == user_data.email)
        ).first()
        
        if existing_user:
            raise HTTPException(
                status_code=400,
                detail="Username or email already exists"
            )
        
        # Verify organization exists
        organization = db.query(Organization).filter(
            Organization.id == user_data.organization_id
        ).first()
        
        if not organization:
            raise HTTPException(
                status_code=400,
                detail="Invalid organization"
            )
        
        # Hash password
        from core.security import security_manager
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
            is_active=True,
            is_verified=True  # Admin-created users are pre-verified
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        # Log user creation
        AuditLog.log_event(
            event_type="create",
            event_category="admin",
            action="Admin created user",
            user_id=current_user.id,
            resource_type="user",
            resource_id=str(user.id),
            description=f"Admin {current_user.username} created user {user.username}",
            status="success"
        )
        
        return UserResponse.from_orm(user)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin user creation error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="User creation failed"
        )


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user_admin(
    user_id: int,
    user_update: UserUpdate,
    current_user: User = Depends(require_admin()),
    db: Session = Depends(get_db)
):
    """
    Update user (admin only)
    """
    try:
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )
        
        # Store old values for audit
        old_values = {
            "first_name": user.first_name,
            "last_name": user.last_name,
            "phone": user.phone,
            "role": user.role,
            "is_active": user.is_active
        }
        
        # Update user fields
        for field, value in user_update.dict(exclude_unset=True).items():
            if hasattr(user, field):
                setattr(user, field, value)
        
        user.updated_at = datetime.utcnow()
        db.commit()
        
        # Log user update
        AuditLog.log_event(
            event_type="update",
            event_category="admin",
            action="Admin updated user",
            user_id=current_user.id,
            resource_type="user",
            resource_id=str(user.id),
            old_values=old_values,
            new_values=user_update.dict(exclude_unset=True),
            description=f"Admin {current_user.username} updated user {user.username}",
            status="success"
        )
        
        return UserResponse.from_orm(user)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin user update error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="User update failed"
        )


@router.delete("/users/{user_id}")
async def delete_user_admin(
    user_id: int,
    current_user: User = Depends(require_admin()),
    db: Session = Depends(get_db)
):
    """
    Delete user (admin only)
    """
    try:
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )
        
        # Prevent admin from deleting themselves
        if user.id == current_user.id:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete your own account"
            )
        
        # Soft delete
        user.is_active = False
        user.updated_at = datetime.utcnow()
        
        # Deactivate user sessions
        sessions = db.query(UserSession).filter(
            UserSession.user_id == user.id,
            UserSession.is_active == True
        ).all()
        
        for session in sessions:
            session.is_active = False
            session.ended_at = datetime.utcnow()
        
        db.commit()
        
        # Log user deletion
        AuditLog.log_event(
            event_type="delete",
            event_category="admin",
            action="Admin deleted user",
            user_id=current_user.id,
            resource_type="user",
            resource_id=str(user.id),
            description=f"Admin {current_user.username} deleted user {user.username}",
            status="success"
        )
        
        return {"message": "User deleted successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin user deletion error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="User deletion failed"
        )


@router.get("/organizations", response_model=List[OrganizationResponse])
async def list_organizations(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    is_active: Optional[bool] = Query(None),
    current_user: User = Depends(require_admin()),
    db: Session = Depends(get_db)
):
    """
    List all organizations (admin only)
    """
    try:
        query = db.query(Organization)
        
        if is_active is not None:
            query = query.filter(Organization.is_active == is_active)
        
        organizations = query.order_by(Organization.created_at.desc()).offset(skip).limit(limit).all()
        
        return [OrganizationResponse.from_orm(org) for org in organizations]
    
    except Exception as e:
        logger.error(f"List organizations error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to list organizations"
        )


@router.post("/organizations", response_model=OrganizationResponse)
async def create_organization_admin(
    org_data: OrganizationCreate,
    current_user: User = Depends(require_admin()),
    db: Session = Depends(get_db)
):
    """
    Create organization (admin only)
    """
    try:
        # Check if organization name already exists
        existing_org = db.query(Organization).filter(
            Organization.name == org_data.name
        ).first()
        
        if existing_org:
            raise HTTPException(
                status_code=400,
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
            event_category="admin",
            action="Admin created organization",
            user_id=current_user.id,
            resource_type="organization",
            resource_id=str(organization.id),
            description=f"Admin {current_user.username} created organization {organization.name}",
            status="success"
        )
        
        return OrganizationResponse.from_orm(organization)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin organization creation error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Organization creation failed"
        )


@router.put("/organizations/{org_id}", response_model=OrganizationResponse)
async def update_organization_admin(
    org_id: int,
    org_update: OrganizationUpdate,
    current_user: User = Depends(require_admin()),
    db: Session = Depends(get_db)
):
    """
    Update organization (admin only)
    """
    try:
        organization = db.query(Organization).filter(Organization.id == org_id).first()
        
        if not organization:
            raise HTTPException(
                status_code=404,
                detail="Organization not found"
            )
        
        # Store old values for audit
        old_values = {
            "name": organization.name,
            "display_name": organization.display_name,
            "is_active": organization.is_active
        }
        
        # Update organization fields
        for field, value in org_update.dict(exclude_unset=True).items():
            if hasattr(organization, field):
                setattr(organization, field, value)
        
        organization.updated_at = datetime.utcnow()
        db.commit()
        
        # Log organization update
        AuditLog.log_event(
            event_type="update",
            event_category="admin",
            action="Admin updated organization",
            user_id=current_user.id,
            resource_type="organization",
            resource_id=str(organization.id),
            old_values=old_values,
            new_values=org_update.dict(exclude_unset=True),
            description=f"Admin {current_user.username} updated organization {organization.name}",
            status="success"
        )
        
        return OrganizationResponse.from_orm(organization)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin organization update error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Organization update failed"
        )


@router.get("/audit-logs")
async def get_audit_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    event_type: Optional[str] = Query(None),
    event_category: Optional[str] = Query(None),
    user_id: Optional[int] = Query(None),
    resource_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    current_user: User = Depends(require_admin()),
    db: Session = Depends(get_db)
):
    """
    Get audit logs (admin only)
    """
    try:
        query = db.query(AuditLog)
        
        # Apply filters
        if event_type:
            query = query.filter(AuditLog.event_type == event_type)
        
        if event_category:
            query = query.filter(AuditLog.event_category == event_category)
        
        if user_id:
            query = query.filter(AuditLog.user_id == user_id)
        
        if resource_type:
            query = query.filter(AuditLog.resource_type == resource_type)
        
        if status:
            query = query.filter(AuditLog.status == status)
        
        if start_date:
            query = query.filter(AuditLog.created_at >= start_date)
        
        if end_date:
            query = query.filter(AuditLog.created_at <= end_date)
        
        # Get total count
        total = query.count()
        
        # Get logs with pagination
        logs = query.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit).all()
        
        log_data = []
        for log in logs:
            log_info = {
                "id": log.id,
                "event_type": log.event_type,
                "event_category": log.event_category,
                "action": log.action,
                "user_id": log.user_id,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "resource_name": log.resource_name,
                "description": log.description,
                "status": log.status,
                "ip_address": log.ip_address,
                "user_agent": log.user_agent,
                "created_at": log.created_at
            }
            log_data.append(log_info)
        
        return {
            "total": total,
            "skip": skip,
            "limit": limit,
            "logs": log_data
        }
    
    except Exception as e:
        logger.error(f"Get audit logs error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve audit logs"
        )


@router.get("/system/health")
async def system_health_check(
    current_user: User = Depends(require_admin()),
    db: Session = Depends(get_db)
):
    """
    System health check (admin only)
    """
    try:
        # Check database connection
        db_healthy = True
        try:
            db.execute("SELECT 1")
        except Exception:
            db_healthy = False
        
        # Check system metrics
        health_status = {
            "database": {
                "healthy": db_healthy,
                "status": "connected" if db_healthy else "disconnected"
            },
            "system": {
                "timestamp": datetime.utcnow().isoformat(),
                "uptime": "N/A",  # Would calculate actual uptime
                "version": "1.0.0"
            }
        }
        
        overall_healthy = all(
            component["healthy"] for component in health_status.values() 
            if isinstance(component, dict) and "healthy" in component
        )
        
        return {
            "healthy": overall_healthy,
            "components": health_status,
            "checked_at": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        logger.error(f"System health check error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Health check failed"
        )