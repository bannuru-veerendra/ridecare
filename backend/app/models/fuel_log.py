import uuid

from sqlalchemy import Column, Date, Float, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.mixins import TimestampMixin


class FuelLog(Base, TimestampMixin):
    """Fuel log model"""
    __tablename__ = "fuel_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey("vehicles.id"), nullable=False)
    date = Column(Date, nullable=False)
    odometer = Column(Integer, nullable=False)
    liters = Column(Float, nullable=False)
    price_per_liter = Column(Float, nullable=False)
    total_cost = Column(Float, nullable=False)
    mileage = Column(Float, nullable=True)
    notes = Column(String, nullable=True)

    vehicle = relationship("Vehicle", back_populates="fuel_logs")

    __table_args__ = (
        Index("idx_fuel_logs_vehicle_id_date_id", "vehicle_id", "date", "id"),
    )
