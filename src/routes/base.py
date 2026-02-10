from fastapi import FastAPI, APIRouter
import os
base_router = APIRouter(
    prefix="/api/v1",
# tags is for the documentation
    tags=["base"]
)
@base_router.get("/")
async def welcome():
    return {"message": f"Welcome to  {os.getenv('APP_NAME')} version {os.getenv('APP_VERSION')} by {os.getenv('APP_AUTHOR')}"}