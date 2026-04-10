from fastapi import FastAPI, APIRouter,status,Request
from fastapi.responses import JSONResponse
import logging
from models.db_schemes import asset
from schemas.nlp import PushRequest, SearchRequest
from models.ProjectModel import ProjectModel
from models.AssetModel import AssetModel
from models.ChunkModel import ChunkModel
from controllers import NLPController
from models import ResponseSignal
from models.enums.AssetTypeEnum import AssetTypeEnum
from stores.llm.LLMEnums import DocumentTypeEnum
logger=logging.getLogger('uvicorn.error')

nlp_router = APIRouter(
    prefix="/api/v1/nlp",
    tags=["api_v1","nlp"]
)


@nlp_router.post("/index/push/{project_id}")
async def index_project(request: Request,project_id: str, push_request: PushRequest):
    project_model = await ProjectModel.create_instance(db_client=request.app.db_client)
    chunk_model = await ChunkModel.create_instance(db_client=request.app.db_client)
    
    project = await project_model.get_project_or_create_one(project_id=project_id)
    if not project:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"signal": ResponseSignal.PROJECT_NOT_FOUND.value}
        )
    nlp_controller = NLPController(vectordb_client=request.app.vectordb_client, generation_client=request.app.generation_client, embedding_client=request.app.embedding_client)
    page = 1
    inserted_count = 0
    while True:
        page_chunks = await chunk_model.get_chunks_by_project_id(project_id=project.id, page=page, page_size=25)
        if len(page_chunks) == 0:
            break
        is_inserted = await nlp_controller.index_into_vectordb(project=project, chunks=page_chunks, do_reset=(push_request.do_reset if page==1 else 0))
        if not is_inserted:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"signal": ResponseSignal.INSET_INTO_VECTORDB_FAILED.value}
            )
        page+=1
        inserted_count += len(page_chunks)
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"signal": ResponseSignal.PROJECT_INDEXED_SUCCESSFULLY.value, "inserted_count": inserted_count,"page_count": page-1}
    )
@nlp_router.get("/index/info/{project_id}")
async def get_index_info(request: Request,project_id: str):
    project_model = await ProjectModel.create_instance(db_client=request.app.db_client)
    project = await project_model.get_project_or_create_one(project_id=project_id)
    nlp_controller = NLPController(vectordb_client=request.app.vectordb_client, generation_client=request.app.generation_client, embedding_client=request.app.embedding_client)
    collection_info = await nlp_controller.get_vectordb_collection_info(project=project)
    
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"signal": ResponseSignal.INDEX_INFO_FETCHED_SUCCESSFULLY.value, "collection_info": collection_info}
    )

@nlp_router.post("/search/{project_id}")
async def search_project(request: Request,project_id: str, search_request: SearchRequest):
    project_model = await ProjectModel.create_instance(db_client=request.app.db_client)
    project = await project_model.get_project_or_create_one(project_id=project_id)
    nlp_controller = NLPController(vectordb_client=request.app.vectordb_client, generation_client=request.app.generation_client, embedding_client=request.app.embedding_client)
    vector=request.app.embedding_client.embed_text(text=search_request.query,document_type=DocumentTypeEnum.QUERY.value)[0]
    search_results = await request.app.vectordb_client.search_by_vector(collection_name=nlp_controller.create_collection_name(project_id=project_id), vector=vector, limit=search_request.limit)
    search_results = [
         {"text":result.payload["text"],"score":result.score}
        for result in search_results
    ]
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"signal": ResponseSignal.SEARCH_COMPLETED_SUCCESSFULLY.value, "search_results": search_results}
    )