from re import S
from .BaseDataModel import BaseDataModel
from .db_schemes import Project
from .enums.DataBaseEnum import DataBaseEnum
from sqlalchemy import select,func
class ProjectModel(BaseDataModel):
    def __init__(self,db_client: object):
        # in the case of the sqlalchemy the db_client is the the session_maker (Session Factory)
        super().__init__(db_client=db_client) 

    @classmethod
    async def create_instance(cls,db_client: object):
        instance=cls(db_client=db_client)
        return instance
    
    async def create_project(self,project: Project):
        async with self.db_client() as session:
            async with session.begin():
                session.add(project)
            await session.refresh(project) # To get the current state of the project at the database like the project_uuid
        return project

    
    async def get_project_or_create_one(self,project_name: str):
        async with self.db_client() as session:
            async with session.begin():
                stmt=select(Project).where(Project.project_name == project_name)
                res = await session.execute(stmt)
                project = res.scalar_one_or_none()
                if project is None:
                    project = Project(project_name=project_name)
                    session.add(project)
                    await session.flush()
                    await session.refresh(project)
                return project



    
    async def get_all_projects(self,page: int = 1,page_size: int = 10):
        async with self.db_client() as session:
            async with session.begin():
                #count the total number of records
                stmt=select(func.count(Project.project_uuid))
                res = await session.execute(stmt)
                total_records=res.scalar_one()
                
                #calculate the total number of pages
                total_pages=(total_records+page_size-1)//page_size

                stmt = select(Project).offset((page-1)*page_size).limit(page_size)
                res = await session.execute(stmt)
                projects = res.scalars().all()
                return projects,total_pages