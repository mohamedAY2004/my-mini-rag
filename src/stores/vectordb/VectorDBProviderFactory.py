from .providers import QdrantDBProvider
from .VectorDBEnums import VectorDBEnums
from helpers.config import Settings
from controllers.BaseController import BaseController
class VectorDBProviderFactory:
    def __init__(self, config: Settings) :
        self.config=config
        self.base_controller=BaseController()
    
    def create(self, provider: str):
        if provider ==VectorDBEnums.QDRANT.value:
            return QdrantDBProvider(
                db_path= self.base_controller.get_database_dir(database_name =self.config.VECTOR_DB_PATH),
                distance_method= self.config.VECTOR_DB_DISTANCE_METHOD
                )
        return None
            