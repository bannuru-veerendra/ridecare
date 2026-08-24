import enum
import uuid

from sqlalchemy import Column, Date, Enum, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.mixins import TimestampMixin


class DocumentType(str, enum.Enum):
    """Document type enum"""
    INSURANCE = "insurance"
    DRIVING_LICENSE = "driving_license"
    REGISTRATION_CERTIFICATE = "registration_certificate"


class Document(Base, TimestampMixin):
    """Document model"""
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey("vehicles.id"), nullable=False)
    document_type = Column(Enum(DocumentType), nullable=False)
    storage_path = Column(String, nullable=False)
    original_filename = Column(String, nullable=False)
    expiry_date = Column(Date, nullable=True)
    notes = Column(String, nullable=True)

    vehicle = relationship("Vehicle", back_populates="documents")

    __table_args__ = (
        Index("idx_documents_vehicle_id_created_at_id", "vehicle_id", "created_at", "id"),
        Index("idx_documents_vehicle_id_expiry_date", "vehicle_id", "expiry_date"),
    )
