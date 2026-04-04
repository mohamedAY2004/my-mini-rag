from enum import Enum

class VectorDBEnums(Enum):
    QDRANT = "QDRANT"


class DistanceMethodEnum(Enum):
    COSINE = "cosine"
    DOT="dot"
    EUCLID = "euclid"
    MANHATTAN = "manhattan"