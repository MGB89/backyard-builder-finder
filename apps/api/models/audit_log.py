"""
Audit log model for tracking user actions and system events
"""

from sqlalchemy import Column, String, DateTime, ForeignKey, Text, JSON, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
from core.database import Base


class AuditLog(Base):
    """Audit log model for security and compliance tracking"""
    
    __tablename__ = "audit_logs"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4(), index=True)
    
    # Multi-tenant
    org_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True)
    
    # User relationship (nullable for system events)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    
    # Event identification
    event_type = Column(String(100), nullable=False, index=True)  # login, logout, create, update, delete, etc.
    event_category = Column(String(50), nullable=False, index=True)  # auth, data, admin, system
    action = Column(String(200), nullable=False)  # Specific action performed
    
    # Target resource
    resource_type = Column(String(100), nullable=True, index=True)  # parcel, user, organization, etc.
    resource_id = Column(String(100), nullable=True, index=True)  # ID of affected resource
    resource_name = Column(String(200), nullable=True)  # Name/description of resource
    
    # Request information
    ip_address = Column(String(45), nullable=True)  # IPv6 support
    user_agent = Column(Text, nullable=True)
    request_method = Column(String(10), nullable=True)  # GET, POST, PUT, DELETE
    request_url = Column(String(500), nullable=True)
    
    # Event details
    description = Column(Text, nullable=True)
    old_values = Column(JSON, nullable=True)  # Previous values for updates
    new_values = Column(JSON, nullable=True)  # New values for updates
    
    # Status and result
    status = Column(String(50), nullable=False, index=True)  # success, failure, error
    status_code = Column(Integer, nullable=True)  # HTTP status code
    error_message = Column(Text, nullable=True)
    
    # Session information
    session_id = Column(String(255), nullable=True, index=True)
    correlation_id = Column(String(255), nullable=True, index=True)  # For tracking related events
    
    # Geographic information
    country = Column(String(2), nullable=True)  # ISO country code
    region = Column(String(100), nullable=True)
    city = Column(String(100), nullable=True)
    
    # Device information
    device_type = Column(String(50), nullable=True)  # desktop, mobile, tablet
    browser = Column(String(100), nullable=True)
    operating_system = Column(String(100), nullable=True)
    
    # Risk assessment
    risk_score = Column(Integer, nullable=True)  # 0-100 risk score
    anomaly_detected = Column(String(50), nullable=True)  # none, low, medium, high
    
    # Additional metadata
    metadata = Column(JSON, nullable=True, default={})
    
    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    
    # Relationships
    organization = relationship("Organization", back_populates="audit_logs")
    user = relationship("User", back_populates="audit_logs")
    
    def __repr__(self):
        return f"<AuditLog(id={self.id}, event_type='{self.event_type}', user_id={self.user_id})>"
    
    @classmethod
    def log_event(
        cls,
        event_type: str,
        event_category: str,
        action: str,
        org_id: str,
        user_id: str = None,
        resource_type: str = None,
        resource_id: str = None,
        resource_name: str = None,
        description: str = None,
        old_values: dict = None,
        new_values: dict = None,
        status: str = "success",
        ip_address: str = None,
        user_agent: str = None,
        request_method: str = None,
        request_url: str = None,
        session_id: str = None,
        metadata: dict = None
    ):
        """
        Create a new audit log entry
        
        Args:
            event_type: Type of event (login, create, update, etc.)
            event_category: Category of event (auth, data, admin, system)
            action: Specific action performed
            user_id: ID of user performing action (optional)
            resource_type: Type of resource affected (optional)
            resource_id: ID of resource affected (optional)
            resource_name: Name of resource affected (optional)
            description: Human-readable description (optional)
            old_values: Previous values for updates (optional)
            new_values: New values for updates (optional)
            status: Event status (success, failure, error)
            ip_address: IP address of requester (optional)
            user_agent: User agent string (optional)
            request_method: HTTP method (optional)
            request_url: Request URL (optional)
            session_id: Session ID (optional)
            metadata: Additional metadata (optional)
            
        Returns:
            AuditLog: Created audit log entry
        """
        return cls(
            event_type=event_type,
            event_category=event_category,
            action=action,
            org_id=org_id,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id else None,
            resource_name=resource_name,
            description=description,
            old_values=old_values,
            new_values=new_values,
            status=status,
            ip_address=ip_address,
            user_agent=user_agent,
            request_method=request_method,
            request_url=request_url,
            session_id=session_id,
            metadata=metadata or {}
        )
    
    @property
    def is_security_event(self):
        """Check if this is a security-related event"""
        security_events = [
            "login_failed", "login_success", "logout", "password_change",
            "account_locked", "permission_denied", "suspicious_activity"
        ]
        return self.event_type in security_events
    
    @property
    def is_data_event(self):
        """Check if this is a data modification event"""
        data_events = ["create", "update", "delete", "export", "import"]
        return self.event_type in data_events
    
    @property
    def formatted_timestamp(self):
        """Get formatted timestamp"""
        return self.created_at.strftime("%Y-%m-%d %H:%M:%S UTC")