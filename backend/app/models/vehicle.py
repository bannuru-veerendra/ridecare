import uuid

from sqlalchemy import Column, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.mixins import TimestampMixin


class Vehicle(Base, TimestampMixin):
    """Vehicle model"""
    __tablename__ = "vehicles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    brand = Column(String, nullable=False)
    vehicle_name = Column(String, nullable=False)
    year = Column(Integer, nullable=False)
    registration_number = Column(String, nullable=False)
    current_odometer = Column(Integer, nullable=False, default=0)

    owner = relationship("User", back_populates="vehicles")
    fuel_logs = relationship("FuelLog", back_populates="vehicle", cascade="all, delete-orphan")
    service_logs = relationship("ServiceLog", back_populates="vehicle", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="vehicle", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_vehicles_owner_id_created_at_id", "owner_id", "created_at", "id"),
        Index("idx_vehicles_registration_number", "registration_number", unique=True),
    )
