from fastapi import FastAPI, APIRouter, Depends, UploadFile,status
from helpers.config import get_settings, Settings
from controllers import DataController,ProjectController
from fastapi.responses import JSONResponse
from models import ResponseSignal
import os
import aiofiles
import logging
logger=logging.getLogger('uvicorn.error')
data_router = APIRouter(
    prefix="/api/v1/data",
# tags is for the documentation
    tags=["api_v1","data"]
)
@data_router.post("/upload/{project_id}")
async def upload_data(project_id: str, file: UploadFile,app_settings: Settings = Depends(get_settings)):
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
    return JSONResponse(
            status_code=status.HTTP_200_OK,
             content={"message": ResponseSignal.FILE_UPLOAD_SUCCESS.value,
             "file_name": file_name,
             "file_path": file_path}
             )
