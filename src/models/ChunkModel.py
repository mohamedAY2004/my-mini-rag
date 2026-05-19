import select
from unittest import result

from models.db_schemes.minirag.schemas.project import Project
from .BaseDataModel import BaseDataModel
from .db_schemes import DataChunk
from .enums.DataBaseEnum import DataBaseEnum
from bson.objectid import ObjectId
from pymongo import InsertOne
from models.ProjectModel import ProjectModel
from uuid import UUID
from sqlalchemy import select, delete,func
class ChunkModel(BaseDataModel):
    def __init__(self,db_client: object):
        super().__init__(db_client=db_client)

    @classmethod
    async def create_instance(cls,db_client: object):
        instance=cls(db_client=db_client)
        return instance
    
    async def create_chunk(self,chunk: DataChunk):
        async with self.db_client() as session:
            async with session.begin():
                await session.add(chunk)
                await session.refresh(chunk)
        return chunk

    async def get_chunk_by_uuid(self,id: UUID):
        async with self.db_client() as session:
            stmt =select(DataChunk).where(DataChunk.datachunk_uuid==id)
            res =await session.execute(stmt)
            chunk = res.scalar_one_or_none()
            return chunk
    #batch write chunks
    async def insert_many_chunks(self,chunks: list[DataChunk],batch_size: int = 100):
        async with self.db_client() as session:
            async with session.begin():
                for i in range(1,len(chunks),batch_size):
                    session.add_all(chunks[i:i+batch_size])
        return len(chunks)
    
    async def delete_chunks_by_project_uuid(self,project_uuid: UUID):
        async with self.db_client() as session:
            async with session.begin():
                stmt = delete(DataChunk).where(DataChunk.chunk_project_uuid==project_uuid)
                results =await session.execute(stmt)
                return results.rowcount

    async def get_chunks_by_project_uuid(self,project_uuid: UUID, page: int = 1, page_size: int = 100):
        async with self.db_client() as session:
            async with session.begin():
                total_records= await session.execute(select(func.count(DataChunk.datachunk_uuid))).scalar_one()
                #calculate the total number of pages
                # total_pages=(total_records+page_size-1)//page_size
                res = await session.execute(select(DataChunk).offset((page-1)*page_size).limit(page_size))
                chunks = res.scalars().all()
                return chunks


    