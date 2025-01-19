from datetime import datetime
from pydantic import BaseModel
from typing import List, Optional


class LibraryImage(BaseModel):
    """
    Represents an image in the library.
    Attributes:
        id (str): The unique identifier of the image.
        image_s3_key (str): The S3 key of the image.
        thumbnail_s3_key (str): The S3 key of the thumbnail image.
        filename (str): The name of the image file.
        created_timestamp (str): The timestamp when the image was created.
        size (int): The size of the image in bytes.
    """

    id: str
    image_s3_key: str
    thumbnail_s3_key: str
    filename: str
    created_timestamp: str
    size: int
    
class DeductionResult(BaseModel):
    """
    Represents the result of a deduction calculation or decision.
    
    This class is used to store and validate the outcome of a deduction process.
    It inherits from Pydantic's BaseModel, ensuring that the data is properly
    validated and serialized.

    Attributes:
        deduction (str): A string representing the result of the claim deduction (whether fraud is detected and the confidence)
    """
    deduction: str


class LibraryImageWithScore(LibraryImage):

    """
    A data model representing a library image with its corresponding score.
    Attributes:
        image (LibraryImage): The library image.
        score (float): The score associated with the image.
    """

    score: float


class EmbeddingsSearchResult(BaseModel):
    """
    Represents a search result for embeddings.
    Attributes:
        id (str): The unique identifier of the image.
        score (float): The score of the search result.
    """

    id: str
    score: float

class ReverseImageSearchResult(BaseModel):
    data_url: Optional[str]=None
    source: Optional[str]=None
    csim: Optional[float]=None
    title: Optional[str]=None
    link: Optional[str]=None
    filename: Optional[str]=None

class ReverseImageSearchResults(BaseModel):
    results: List[ReverseImageSearchResult]
    
class ExifDataResult(BaseModel):
    """
    Represents GPS coordinates.
    Attributes:
        latitude (float): The latitude of the location.
        longitude (float): The longitude of the location.
        timestamp (datetime): The timestamp of the location data
    """

    latitude: Optional[float]=None
    longitude: Optional[float]=None
    timestamp: Optional[datetime]=None