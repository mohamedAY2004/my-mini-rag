from fastapi import FastAPI
from routes.base import base_router
import dotenv
dotenv.load_dotenv(".env")
app = FastAPI()
app.include_router(base_router)