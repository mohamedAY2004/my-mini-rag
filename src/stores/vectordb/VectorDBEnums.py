from enum import Enum

class VectorDBEnums(Enum):
    QDRANT = "QDRANT"
    PGVECTOR = "PGVECTOR"


class DistanceMethodEnum(Enum):
    COSINE = "cosine"
    DOT="dot"
    EUCLID = "euclid"
    MANHATTAN = "manhattan"

class PgVectorTableSchemeEnums(Enum):
    ID = "id"
    TEXT = "text"
    VECTOR = "vector"
    CHUNK_ID = "chunk_id"
    METADATA = "metadata"
    _PREFIX = "pgvector"

class PgVectorDistanceMethodEnums(Enum):
    COSINE = "vector_cosine_ops"
    DOT = "vector_ip_ops"
    EUCLID = "vector_l2_ops"
    MANHATTAN = "vector_l1_ops"

class PgVectorIndexTypeEnums(Enum):
    HNSW = "hnsw"
    IVFFLAT = "ivfflat"