# notification-service/app/models/notification.py
from sqlalchemy import Column, Integer, String, DateTime, JSON, Text
from sqlalchemy.sql import func


from app.db.postgresql import Base


# SQLAlchemy Models
class Notification(Base):
    """Database model for notifications."""
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    type = Column(String, nullable=False)  # "low_stock", etc.
    channel = Column(String, nullable=False, default="email")  
    
    # Recipients
    recipient_id = Column(String, nullable=True)  
    
    # Content
    subject = Column(String, nullable=True)
    content = Column(Text, nullable=False)
    
    # Delivery status
    status = Column(String, nullable=False, default="pending")  # "pending", "sent", "failed"
    error_message = Column(String, nullable=True)
    
    # Data used to generate the notification
    data = Column(JSON, nullable=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    sent_at = Column(DateTime(timezone=True), nullable=True)
