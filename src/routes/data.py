from fastapi import FastAPI, APIRouter, Depends, UploadFile,status,Request
from helpers.config import get_settings, Settings
from controllers import DataController,ProjectController,ProcessController
from fastapi.responses import JSONResponse
from models import ResponseSignal
import os
import aiofiles
import logging
from schemas.data import ProcessRequest
from models.ProjectModel import ProjectModel
from models.db_schemes import DataChunk, Asset
from models.ChunkModel import ChunkModel
from models.AssetModel import AssetModel
from models.enums.AssetTypeEnum import AssetTypeEnum
logger=logging.getLogger('uvicorn.error')
data_router = APIRouter(
    prefix="/api/v1/data",
# tags is for the documentation
    tags=["api_v1","data"]
)
@data_router.post("/upload/{project_id}")
async def upload_data(request: Request,project_id: str, file: UploadFile,app_settings: Settings = Depends(get_settings)):
    project_model = await ProjectModel.create_instance(db_client=request.app.db_client)
    project = await project_model.get_project_or_create_one(project_id=project_id)
    #validate the file properties
    isvalid, result_signal = DataController().validate_file(file)
    if not isvalid:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
             content={"message": result_signal}
             )
    file_path,file_name = DataController().generate_unique_file_path(orig_file_name=file.filename, project_id=project_id)
    try:
        #async file upload with maxchunk size 512KB
        async with aiofiles.open(file_path, "wb") as f:
            while chunk := await file.read(app_settings.FILE_DEFAULT_CHUNK_SIZE):
                await f.write(chunk)
    except Exception as e:
        logger.error(f"File upload failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": ResponseSignal.FILE_UPLOAD_FAILED.value}
            )
    #store the asset in the database
    asset_model = await AssetModel.create_instance(db_client=request.app.db_client)
    asset_resource = Asset(
        asset_project_id=project.id,
        asset_type=AssetTypeEnum.FILE.value,
        asset_name=file_name,
        asset_size=file.size,
        asset_config={"file_path": file_path,"file_size": os.path.getsize(file_path)}
    )
    asset_record = await asset_model.create_asset(asset=asset_resource)
    return JSONResponse(
            status_code=status.HTTP_200_OK,
             content={"message": ResponseSignal.FILE_UPLOAD_SUCCESS.value,
             "file_name": asset_record.asset_name,
             "file_path": asset_record.asset_config["file_path"],
             "asset_id": str(asset_record.id),
            #  "project_id":str(project._id)
            }
             )
@data_router.post("/process/{project_id}")
async def process_endpoint(request: Request,project_id: str, process_request: ProcessRequest):
    file_id = process_request.file_id 
    chunk_size = process_request.chunk_size
    overlap_size = process_request.chunk_overlap
    do_reset = process_request.do_reset
    project_model = await ProjectModel.create_instance(db_client=request.app.db_client)
    project = await project_model.get_project_or_create_one(project_id=project_id)
    chunk_model = await ChunkModel.create_instance(db_client=request.app.db_client)
    if do_reset == 1:
        await chunk_model.delete_chunks_by_project_id(project_id=project.id)
    project_file_ids=[]
    process_controller = ProcessController(project_id=project_id)
    if file_id is not None:
        if not os.path.exists(os.path.join(process_controller.project_dir, file_id)):
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"message": ResponseSignal.FILE_NOT_FOUND.value}
                )
        project_file_ids.append(file_id)

    else:
        asset_model=await AssetModel.create_instance(db_client=request.app.db_client)
        assets = await asset_model.get_all_project_assets(project_id=project.id,asset_type=AssetTypeEnum.FILE.value)
        project_file_ids=[asset.asset_name for asset in assets]
    inserted_count=0
    if len(project_file_ids) == 0:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": ResponseSignal.NO_FILES_TO_PROCESS.value}
            )
    for file_id in project_file_ids:
        file_content = process_controller.get_file_content(file_id=file_id)
        file_chunks = process_controller.process_file_content(
            file_content=file_content,
            file_id=file_id, 
            chunk_size=chunk_size, 
            overlap_size=overlap_size)
        file_chunks_records=[
            DataChunk(
                chunk_text=chunk.page_content,
                chunk_metadata=chunk.metadata,  #type: ignore
                chunk_order=idx+1,    
                chunk_project_id=project.id
            )
            for idx,chunk in enumerate(file_chunks)
        ]
        inserted_count = inserted_count +await chunk_model.insert_many_chunks(chunks=file_chunks_records)
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": ResponseSignal.FILE_PROCESSING_SUCCESS.value,
        "inserted_count": inserted_count}
        )

