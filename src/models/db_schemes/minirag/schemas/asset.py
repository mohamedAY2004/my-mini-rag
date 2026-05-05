from .minirag_base import SQLAlchemyBase
from sqlalchemy import Column, String, Integer, DateTime, Boolean, Text, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID,JSONB
from sqlalchemy.orm import relationship
from sqlalchemy import Index
import uuid
class Asset(SQLAlchemyBase):

    __tablename__ = "assets"

    asset_uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True,nullable=False)


    asset_name = Column(String(255), nullable=False)
    asset_type = Column(String(255), nullable=False)
    asset_size = Column(Integer, nullable=False)

    # We use JSON Binary (JSONB) for heavy read Use case , it is light for reading  but heavy for writing.
    asset_config = Column(JSONB, nullable=False)
    
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    asset_project_uuid = Column(UUID, ForeignKey("projects.project_uuid"),nullable=False)


    project = relationship("Project",back_populates="assets")
    datachunks=relationship("DataChunk",back_populates="asset")


    __table_args__ =(
        Index("ix_asset_project_uuid",asset_project_uuid),
        Index("ix_asset_type",asset_type)
    )