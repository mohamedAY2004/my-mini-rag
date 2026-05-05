from .minirag_base import SQLAlchemyBase
from sqlalchemy import Column, String, Integer, DateTime, Boolean, Text, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID,JSONB
from sqlalchemy.orm import relationship
from sqlalchemy import Index
import uuid
from pydantic import BaseModel
class DataChunk(SQLAlchemyBase):

    __tablename__="datachunks"

    datachunk_uuid = Column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4,unique=True, nullable=False)
    
    
    datachunk_text = Column(String(2048),nullable=False)
    datachunk_metadata = Column(JSONB,nullable=False)
    datachunk_order =Column(Integer)
    
    
    chunk_project_uuid =Column(UUID(as_uuid=True),ForeignKey("projects.project_uuid"))
    chunk_asset_uuid= Column(UUID(as_uuid=True),ForeignKey("assets.asset_uuid"))

    project= relationship("Project", back_populates="datachunks",uselist=False)
    asset = relationship("Asset",back_populates="datachunks",uselist=False)

    __table_args__ =(
        Index("ix_datachunk_project_uuid",chunk_project_uuid),
        Index("ix_datachunk_asset_uuid",chunk_asset_uuid)
    )

class RetrievedChunk(BaseModel):
    chunk_text: str
    score: float
    chunk_metadata: dict