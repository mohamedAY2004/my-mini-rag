from .minirag_base import SQLAlchemyBase
from sqlalchemy import Column, String, Integer, DateTime, Boolean, Text, ForeignKey, func, Index
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
from sqlalchemy.orm import relationship
class Project(SQLAlchemyBase):
    __tablename__ = "projects"
    # project_id = Column(Integer, primary_key=True, autoincrement=True)
    #UUID is used for any user to not get info from the project id like if the id is auto incremented the user can get the info from the id and know the number of projects and the last project id and so on.
    project_uuid = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True,nullable=False)

    project_name = Column(String(255), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    datachunks=relationship("DataChunk",back_populates="project")

    __table_args__ =(
        Index("ix_project_name",project_name),
    )
