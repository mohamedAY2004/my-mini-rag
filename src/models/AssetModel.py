from .BaseDataModel import BaseDataModel
from .db_schemes import Asset
from .enums.DataBaseEnum import DataBaseEnum
from bson.objectid import ObjectId
from uuid import UUID
from sqlalchemy import select
class AssetModel(BaseDataModel):
    def __init__(self,db_client: object):
        super().__init__(db_client=db_client)
    @classmethod
    async def create_instance(cls,db_client: object):
        instance=cls(db_client=db_client)
        return instance
    async def create_asset(self,asset: Asset):
        async with self.db_client() as session:
            async with session.begin():
                session.add(asset)
                await session.flush()
                await session.refresh(asset)
        return asset
        
    async def get_asset_by_id(self,id: UUID):
        async with self.db_client() as session:
                stmt = select(Asset).where(Asset.asset_uuid)
                res = await session.execute(stmt)
                asset = res.scalar_one_or_none()
                return asset

    async def get_all_project_assets(self,project_uuid: UUID,asset_type: str):
        async with self.db_client() as session:
            stmt = select(Asset).where(Asset.asset_project_uuid == project_uuid)
            res = await session.execute(stmt)
            assets = res.scalars().all()
            return assets
    
    async def get_asset_record(self,asset_name: str,project_uuid: UUID):
            async with self.db_client() as session:
                stmt = select(Asset).where((Asset.asset_project_uuid == project_uuid) & (Asset.asset_name == asset_name))
                res = await session.execute(stmt)
                asset = res.scalar_one_or_none()
                return asset