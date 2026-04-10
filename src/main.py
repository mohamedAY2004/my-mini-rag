from fastapi import FastAPI
from routes import base,data,nlp
from motor.motor_asyncio import AsyncIOMotorClient
from helpers.config import get_settings
from stores.llm import LLMProviderFactory
from stores.vectordb import VectorDBProviderFactory
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

    #vector db client
    vector_db_provider_factory = VectorDBProviderFactory(app_settings)
    app.vectordb_client = vector_db_provider_factory.create(provider=app_settings.VECTOR_DB_BACKEND)
    await app.vectordb_client.connect()
    


async def shutdown():
    app.mongo_conn.close()
    await app.vectordb_client.disconnect()

app.add_event_handler("startup", startup)
app.add_event_handler("shutdown", shutdown)

app.include_router(base.base_router)
app.include_router(data.data_router)
app.include_router(nlp.nlp_router)
