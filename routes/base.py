from fastapi import FastAPI, APIRouter
base_router = APIRouter(
    prefix="/api/v1",
# tags is for the documentation
    tags=["base"]
)
@base_router.get("/")
def welcome():
    return {"message": "Welcome to the API, i just changed the message"}