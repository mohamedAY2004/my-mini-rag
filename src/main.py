from fastapi import FastAPI
from routes import base,data
from motor.motor_asyncio import AsyncIOMotorClient
from helpers.config import get_settings
from stores.llm import LLMProviderFactory
app = FastAPI()

async def startup():
    app_settings = get_settings()
    app.mongo_conn=AsyncIOMotorClient(app_settings.MONGODB_URL)
    app.db_client=app.mongo_conn[app_settings.MONGODB_DATABASE]

    llm_provider_factory = LLMProviderFactory(app_settings)

    #generation client
    app.generation_client = llm_provider_factory.create(app_settings.GENERATION_BACKEND)
    app.generation_client.set_generation_model(app_settings.GENERATION_MODEL_ID)
    
    #embedding client
    app.embedding_client = llm_provider_factory.create(app_settings.EMBEDDING_BACKEND)
    app.embedding_client.set_embedding_model(app_settings.EMBEDDING_MODEL_ID, app_settings.EMBEDDING_SIZE)

async def shutdown():
    app.mongo_conn.close()

app.router.lifespan.on_startup.append(startup)
app.router.lifespan.on_shutdown.append(shutdown)

app.include_router(base.base_router)
app.include_router(data.data_router)
