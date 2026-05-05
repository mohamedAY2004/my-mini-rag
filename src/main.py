from fastapi import FastAPI
from routes import base,data,nlp
from helpers.config import get_settings
from stores.llm import LLMProviderFactory
from stores.vectordb import VectorDBProviderFactory
from stores.llm.templates.TemplateParser import TemplateParser
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
app = FastAPI()

async def startup():
    app_settings = get_settings()

    #====================PostgreSQL Connection====================
    postgres_url = f"postgresql+asyncpg://{app_settings.POSTGRES_USERNAME}:{app_settings.POSTGRES_PASSWORD}@{app_settings.POSTGRES_HOST}:{app_settings.POSTGRES_PORT}/{app_settings.POSTGRES_MAIN_DATABASE}"
    app.db_engine=create_async_engine(postgres_url)
    app.db_client=sessionmaker(app.db_engine, class_=AsyncSession, expire_on_commit=False)
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
    app.template_parser = TemplateParser(language=app_settings.DEFAULT_LANGUAGE)


async def shutdown():
    await app.db_engine.dispose()
    await app.db_client.close()
    await app.vectordb_client.disconnect()

app.add_event_handler("startup", startup)
app.add_event_handler("shutdown", shutdown)

app.include_router(base.base_router)
app.include_router(data.data_router)
app.include_router(nlp.nlp_router)
