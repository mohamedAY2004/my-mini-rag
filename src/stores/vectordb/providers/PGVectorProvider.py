from ..VectorDBInterface import VectorDBInterface
from ..VectorDBEnums import PgVectorTableSchemeEnums, DistanceMethodEnum, PgVectorDistanceMethodEnums, PgVectorIndexTypeEnums

from typing import List
import logging
from models.db_schemes import RetrievedChunk
import json
from sqlalchemy.sql import text as sql_text
import re
class PGVectorProvider(VectorDBInterface):
    def __init__(self, db_client,default_vector_size:int ,distance_method: str, index_threshold: int=100):
        self.logger = logging.getLogger("uvicorn")
        self.db_client=db_client
        self.default_vector_size=default_vector_size
        # Map each supported distance method to (opclass for the ANN index, distance operator).
        # score_mode controls how the raw distance is turned into a "higher = closer" score:
        #   - "similarity": cosine similarity = 1 - distance (bounded in [-1, 1])
        #   - "distance":   negated distance so a smaller distance yields a larger score.
        #                   For DOT, pgvector's <#> returns the *negative* inner product, so
        #                   negating it recovers the actual inner product.
        distance_method = (distance_method or "").strip().lower()
        if distance_method == DistanceMethodEnum.COSINE.value:
            self.distance_method=PgVectorDistanceMethodEnums.COSINE.value
            self.distance_op="<=>"
            self.score_mode="similarity"
        elif distance_method == DistanceMethodEnum.DOT.value:
            self.distance_method = PgVectorDistanceMethodEnums.DOT.value
            self.distance_op = "<#>"
            self.score_mode="distance"
        elif distance_method == DistanceMethodEnum.EUCLID.value:
            self.distance_method = PgVectorDistanceMethodEnums.EUCLID.value
            self.distance_op = "<->"
            self.score_mode="distance"
        elif distance_method == DistanceMethodEnum.MANHATTAN.value:
            self.distance_method = PgVectorDistanceMethodEnums.MANHATTAN.value
            self.distance_op = "<+>"
            self.score_mode="distance"
        else:
            raise ValueError(f"Unsupported distance method for pgvector DB: {distance_method!r}")

        self.pgvector_table_prefix= PgVectorTableSchemeEnums._PREFIX.value

        self.get_default_index_name = lambda collection_name: f"{self._table_name(collection_name)}_vector_idx"

        self.index_threshold=index_threshold

    @staticmethod
    def _validate_collection_name(collection_name: str):
        # Identifiers cannot be passed as bind params, so guard every name that is
        # interpolated into raw SQL to prevent injection.
        if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", collection_name):
            raise ValueError(f"Invalid collection name: {collection_name!r}")

    def _table_name(self, collection_name: str) -> str:
        self._validate_collection_name(collection_name)
        return f"{self.pgvector_table_prefix}_{collection_name}"

    async def connect(self):
        async with self.db_client() as session:
            async with session.begin():
                await session.execute(
                    sql_text(
                        "CREATE EXTENSION IF NOT EXISTS vector"
                    )
                )

    
    async def disconnect(self):
        pass

    
    async def is_collection_exists(self, collection_name: str) -> bool:
        async with self.db_client() as session:
            # LIMIT 1 + first() avoids MultipleResultsFound when the same table name
            # exists in more than one schema.
            stmt =sql_text("SELECT 1 FROM pg_tables WHERE tablename = :collection_name LIMIT 1")
            record = await session.execute(stmt,{"collection_name": f"{self.pgvector_table_prefix}_{collection_name}"} )
            return record.first() is not None

    
    async def list_all_collections(self) -> List:
        async with self.db_client() as session:
            stmt =sql_text("SELECT tablename FROM pg_tables WHERE tablename LIKE :prefix")
            records = await session.execute(stmt,{"prefix":self.pgvector_table_prefix+"%"})
            return records.scalars().all()

    async def get_collection_info(self, collection_name: str) -> dict:
        async with self.db_client() as session:
            table_info_stmt = sql_text(
                "SELECT schemaname, tablename, tableowner, tablespace, hasindexes FROM pg_tables WHERE tablename= :collection_name"
            )
            table_info = await session.execute(table_info_stmt,{"collection_name": f"{self.pgvector_table_prefix}_{collection_name}"})
            table_data = table_info.fetchone()
            if not table_data:
                return None
            # Only count once we know the table exists, otherwise the COUNT would raise.
            count_stmt = sql_text(f"SELECT COUNT(*) FROM {self._table_name(collection_name)}")
            count = await session.execute(count_stmt)
            record_count = count.scalar_one()
        # hasindexes is true even with only the PK index, so report the ANN index explicitly.
        vector_index_exists = await self.is_index_exists(collection_name=collection_name)
        return {
                "table_info": {
                    "schemaname": table_data[0],
                    "tablename":  table_data[1],
                    "tableowner": table_data[2],
                    "tablespace": table_data[3],
                    "hasindexes": table_data[4],
                },
                "record_count": record_count,
                "vector_index_name": self.get_default_index_name(collection_name=collection_name),
                "vector_index": vector_index_exists,
            }

    
    async def delete_collection(self, collection_name: str):
        table_name = self._table_name(collection_name)
        async with self.db_client() as session:
            async with session.begin():
                delete_stmt = sql_text(f'DROP TABLE IF EXISTS "{table_name}"')
                await session.execute(delete_stmt)
                self.logger.info(f"DROPPED collection: {table_name}")

    
    async def create_collection(self, collection_name: str, 
                                embedding_size: int,
                                do_reset: bool = False):
        if do_reset:
            await self.delete_collection(collection_name=collection_name)
        table_name = self._table_name(collection_name)
        collection_exists = await self.is_collection_exists(collection_name=collection_name)
        if not collection_exists:
            self.logger.info(f"Creating collection: {table_name}")
            async with self.db_client() as session:
                async with session.begin():
                    create_stmt= sql_text(f"CREATE TABLE {table_name} ("
                                          f"{PgVectorTableSchemeEnums.ID.value} bigserial PRIMARY KEY, "
                                          f"{PgVectorTableSchemeEnums.TEXT.value} text, "
                                          f"{PgVectorTableSchemeEnums.VECTOR.value} vector({embedding_size}), "
                                          f"{PgVectorTableSchemeEnums.METADATA.value} jsonb DEFAULT '{{}}', "
                                          f"{PgVectorTableSchemeEnums.CHUNK_ID.value} UUID, "
                                          f"FOREIGN KEY ({PgVectorTableSchemeEnums.CHUNK_ID.value}) REFERENCES datachunks(datachunk_uuid)"
                                          ")"
                                          )
                    await session.execute(create_stmt)
            return True
        return False     
        
        
    async def is_index_exists(self, collection_name:str)->bool:
        idx_name=self.get_default_index_name(collection_name=collection_name)
        async with self.db_client() as session:
            check_stmt = sql_text("SELECT 1 FROM pg_indexes WHERE tablename = :collection_name AND indexname = :index_name")
            result = await session.execute(check_stmt,{"collection_name":f"{self.pgvector_table_prefix}_{collection_name}","index_name":idx_name})
            return bool(result.scalar_one_or_none())
        
        
        
    async def create_vector_index(self, collection_name:str, index_type:str=PgVectorIndexTypeEnums.HNSW.value) -> bool:
        table_name = self._table_name(collection_name)
        exists=await self.is_index_exists(collection_name)
        if exists:
            return False
        # Read the count in its own (read-only) session; executing here autobegins a
        # transaction, so we must not open another session.begin() on the same session.
        async with self.db_client() as session:
            count_stmt=sql_text(f"SELECT COUNT({PgVectorTableSchemeEnums.ID.value}) FROM {table_name}")
            result = await session.execute(count_stmt)
            records_count = result.scalar_one()

        if records_count < self.index_threshold:
            return False
        async with self.db_client() as session:
            async with session.begin():
                self.logger.info(f"START: Creating vector index for collection: {table_name}")
                idx_name=self.get_default_index_name(collection_name=collection_name)
                create_idx_stmt = sql_text(f"CREATE INDEX {idx_name} ON {table_name} "
                                           f"USING {index_type} ({PgVectorTableSchemeEnums.VECTOR.value} {self.distance_method})")
                await session.execute(create_idx_stmt)
                self.logger.info(f"END: Created vector index for collection: {table_name}")
        return True

    async def reset_vector_index(self, collection_name,index_type: str=PgVectorIndexTypeEnums.HNSW.value)->bool:
        idx_name= self.get_default_index_name(collection_name=collection_name)
        async with self.db_client() as session:
            async with session.begin():
                drop_stmt=sql_text(f"DROP INDEX IF EXISTS {idx_name}")
                await session.execute(drop_stmt)
        return await self.create_vector_index(collection_name=collection_name,index_type=index_type)
                
    async def insert_one(self, collection_name: str, text: str, vector: list,
                         metadata: dict = None, 
                         record_id: str = None):
        table_name = self._table_name(collection_name)
        collection_exists = await self.is_collection_exists(collection_name=collection_name)
        if not collection_exists:
            self.logger.error(f"Cannot insert new record to non-existed collection: {table_name}")
            return False
        if not record_id:
            self.logger.error(f"Cannot insert new record without chunk_id: {table_name}")
            return False

        # By default SQL DB will validate refrential integrity of the record_id
        async with self.db_client() as session:
            async with session.begin():
                insert_stmt = sql_text(f"INSERT INTO {table_name}"
                                       f"({PgVectorTableSchemeEnums.TEXT.value},{PgVectorTableSchemeEnums.VECTOR.value},{PgVectorTableSchemeEnums.METADATA.value},{PgVectorTableSchemeEnums.CHUNK_ID.value})"
                                       f"VALUES (:text,CAST(:vector AS vector),:metadata,:chunk_id)"
                                       )
                metadata_json = json.dumps(metadata, ensure_ascii=False) if metadata is not None else "{}"
                await session.execute(insert_stmt,{
                    "text":text,
                    "vector":"["+",".join([str(v) for v in vector])+"]", # Postgress wait for the vector in string format so we parse to string before sending it
                    "metadata":metadata_json,
                    "chunk_id":record_id
                })

        return True

        

    
    async def insert_many(self, collection_name: str, texts: list, 
                          vectors: list, metadata: list = None, 
                          record_ids: list = None, batch_size: int = 50):
        table_name = self._table_name(collection_name)
        collection_exists = await self.is_collection_exists(collection_name=collection_name)
        if not collection_exists:
            self.logger.error(f"Cannot insert new records to non-existed collection: {table_name}")
            return False
        if record_ids is None:
            self.logger.error(f"Cannot insert new records without record_ids: {table_name}")
            return False
        if not (len(texts) == len(vectors) == len(record_ids)):
            self.logger.error(f"Count of texts, vectors, record_ids mismatch for collection: {table_name}")
            return False
        if len(vectors) == 0 or len(record_ids) == 0:
            self.logger.error(f"Count of vectors or record_ids cannot be zero: {table_name}")
            return False

        if not metadata or len(metadata) == 0:
            metadata = [None]*len(texts)
        elif len(metadata) != len(texts):
            self.logger.error(f"Count of metadata and texts mismatch for collection: {table_name}")
            return False
        async with self.db_client() as session:
            async with session.begin():
                for i in range(0,len(texts),batch_size):
                    batch_texts = texts[i:i+batch_size]
                    batch_vectors = vectors[i:i+batch_size]
                    batch_metadata = metadata[i:i+batch_size]
                    batch_record_ids = record_ids[i:i+batch_size]
                    values = []
                    
                    for _text,_vector,_metadata,_record_id in zip(batch_texts,batch_vectors,batch_metadata,batch_record_ids):
                        metadata_json = json.dumps(_metadata, ensure_ascii=False) if _metadata is not None else "{}"
                        values.append({
                        "text":_text,
                        "vector":"["+",".join([str(v) for v in _vector])+"]", # Postgress wait for the vector in string format so we parse to string before sending it
                        "metadata":metadata_json,
                        "chunk_id":_record_id
                        })
                    batch_insert_stmt = sql_text(f"INSERT INTO {table_name}"
                                       f"({PgVectorTableSchemeEnums.TEXT.value},{PgVectorTableSchemeEnums.VECTOR.value},{PgVectorTableSchemeEnums.METADATA.value},{PgVectorTableSchemeEnums.CHUNK_ID.value})"
                                       f"VALUES (:text,CAST(:vector AS vector),:metadata,:chunk_id)"
                                       )
                    await session.execute(batch_insert_stmt,values)
        # Build the ANN index once the collection grows past the threshold (no-op if it already exists or is still small)
        await self.create_vector_index(collection_name=collection_name)
        return True


    async def search_by_vector(self, collection_name: str, vector: list, limit: int,threshold: float)->List[RetrievedChunk]:
        collection_exists = await self.is_collection_exists(collection_name=collection_name)
        if not collection_exists:
            self.logger.error(f"Cannot search for records in a non-existed collection: {self.pgvector_table_prefix}_{collection_name}")
            return []
        table_name = self._table_name(collection_name)
        _vector= "["+",".join([str(v) for v in vector])+"]"

        distance_expr = f"{PgVectorTableSchemeEnums.VECTOR.value} {self.distance_op} CAST(:vector AS vector)"
        # score is defined so higher = closer regardless of metric (see __init__).
        if self.score_mode == "similarity":
            score_expr = f"1 - ({distance_expr})"
        else:
            score_expr = f"-({distance_expr})"

        async with self.db_client() as session:
            # Run the ANN scan (ORDER BY raw distance ASC + LIMIT) in an inner query so the
            # index is used, then filter by threshold in the outer query. Putting the
            # distance in the inner WHERE would defeat the ANN index.
            search_stmt = sql_text(
                f"SELECT text, metadata, score FROM ("
                f"SELECT {PgVectorTableSchemeEnums.TEXT.value} as text, "
                f"{PgVectorTableSchemeEnums.METADATA.value} as metadata, "
                f"{score_expr} as score "
                f"FROM {table_name} "
                f"ORDER BY {distance_expr} ASC "
                f"LIMIT :limit"
                f") sub WHERE score >= :threshold"
            )
            result = await session.execute(search_stmt,{"vector": _vector, "threshold": threshold, "limit": limit})
            records = result.fetchall()

            retrieved = []
            for record in records:
                record_metadata = record.metadata
                if isinstance(record_metadata, str):
                    record_metadata = json.loads(record_metadata) if record_metadata else {}
                elif record_metadata is None:
                    record_metadata = {}
                retrieved.append(
                    RetrievedChunk(
                        chunk_text=record.text,
                        score=record.score,
                        chunk_metadata=record_metadata
                    )
                )
            return retrieved