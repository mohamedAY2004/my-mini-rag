from stores.vectordb.providers import PGVectorProvider

from .providers import QdrantDBProvider
from .VectorDBEnums import VectorDBEnums
from helpers.config import Settings
from controllers.BaseController import BaseController
from sqlalchemy.orm import sessionmaker
class VectorDBProviderFactory:
    def __init__(self, config: Settings,db_client: sessionmaker=None)  -> None:
        self.config=config
        self.base_controller=BaseController()
        self.db_client=db_client
    
    def create(self, provider: str) -> QdrantDBProvider | PGVectorProvider | None:
        if provider ==VectorDBEnums.QDRANT.value:
            return QdrantDBProvider(
                db_path= self.base_controller.get_database_dir(database_name =self.config.VECTOR_DB_PATH),
                distance_method= self.config.VECTOR_DB_DISTANCE_METHOD
                )
        elif provider == VectorDBEnums.PGVECTOR.value:
            if self.db_client == None : return None
            return PGVectorProvider(db_client=self.db_client,
                                    default_vector_size=self.config.EMBEDDING_SIZE,
                                    distance_method=self.config.VECTOR_DB_DISTANCE_METHOD,index_threshold=self.config.VECTOR_DB_PGVEC_INDEX_THRESHOLD)
        return None
            