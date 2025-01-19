import logging
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import PIL
from dotenv import load_dotenv
from pandas import DataFrame
import uvicorn
from typing import Optional
from PIL import Image
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
from schemas.schemas import DeductionResult, ExifDataResult, LibraryImageWithScore, ReverseImageSearchResults
from claim_deduction import perform_deduction
from image_library import S3ImageLibrary
from websearch import reverse_image_search as internet_reverse_image_search
from exifdata import get_lat_lon_for_img, extract_exif_gps_timestamp
import io
import boto3

load_dotenv()
s3 = boto3.client('s3')

STORAGE_BUCKET = os.environ.get("STORAGE_BUCKET", "STORAGE_BUCKET")

logging.basicConfig(level=logging.INFO,
                    format="%(levelname)s:%(name)s - %(message)s")
logger = logging.getLogger(__name__)

# Add the directory containing the schemas module to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


# Initialize FastAPI app
app = FastAPI(
    title="Fraud Detection API",
    description="An API for providing fraud detection capabilities.",
    summary="",
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    version="0.0.1",
    terms_of_service="https://aws.amazon.com/asl/",
)


def get_origins():
    """
    Get the allowed CORS origins.

    Returns:
        list: A list of allowed CORS origins.
    """
    origins = os.getenv("CORS_ORIGINS", "").split(",")
    origins = [origin.strip() for origin in origins if origin.strip()]
    if "http://localhost:3000" not in origins:
        origins.append("http://localhost:3000")
    return origins


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


@app.get("/")
async def default_route():
    """
    Default route for the Fraud Detection API.

    Returns:
        dict: A dictionary containing a welcome message.
    """
    return {"message": "Welcome to the Fraud Detection API!"}

@app.post("/searchlibrary")
async def search_image_library(image_s3_key: str, sim_thresh: float = 0.9) -> list[LibraryImageWithScore]:
    """
    Searches for similar images in the image library stored in S3.
    Args:
        image_s3_key (str): The S3 key of the image to search for.
        sim_thresh (float, optional): The similarity threshold for filtering images. Defaults to 0.9.
    Returns:
        list[LibraryImageWithScore]: A list of images from the library that have a similarity score above the threshold.
    """
   
    
    # Download the file from S3
    response = s3.get_object(Bucket=STORAGE_BUCKET, Key=image_s3_key)
    file_content = response['Body'].read()

    # Create BytesIO object from the file content
    image_bytes = io.BytesIO(file_content)  
    image = Image.open(image_bytes)
    image = image.convert('RGB')
    
    image_library = S3ImageLibrary()

    lst_images = image_library.search_images(image)

    reverse_matches = [
        img for img in lst_images if img.score > sim_thresh]

    return reverse_matches

@app.post("/search/internet")
async def reverse_internet_search(image_s3_key:str, filename:str, sim_thresh: float = 0.9) -> ReverseImageSearchResults:
    """
    Performs a reverse image search using an image stored in an S3 bucket.
    Args:
        image_s3_key (str): The S3 key of the image to be searched.
        filename (str): The filename to be used in the search.
        sim_thresh (float, optional): The similarity threshold for the search. Defaults to 0.9.
    Returns:
        ReverseImageSearchResults: The results of the reverse image search.
    """
    
    
    # Download the file from S3
    response = s3.get_object(Bucket=STORAGE_BUCKET, Key=image_s3_key)
    file_content = response['Body'].read()

    # Create BytesIO object from the file content
    image_bytes = io.BytesIO(file_content)  
    image = Image.open(image_bytes)
    image = image.convert('RGB')
        
    return internet_reverse_image_search(image, filename, sim_thresh)

@app.post("/exifdata")
async def extract_exif_data(image_s3_key:str) -> ExifDataResult:
    """
    Extracts EXIF data from an image stored in an S3 bucket.
    Args:
        image_s3_key (str): The S3 key of the image file.
    Returns:
        ExifDataResult: An object containing the latitude, longitude, and timestamp extracted from the image's EXIF data.
    Raises:
        botocore.exceptions.ClientError: If there is an error downloading the file from S3.
        PIL.UnidentifiedImageError: If the image cannot be opened and identified.
        KeyError: If the required EXIF data is not found in the image.
    """
   
    # Download the file from S3
    response = s3.get_object(Bucket=STORAGE_BUCKET, Key=image_s3_key)
    file_content = response['Body'].read()

    # Create BytesIO object from the file content
    image_bytes = io.BytesIO(file_content)  
    image = Image.open(image_bytes)
    image = image.convert('RGB')
    
    lat, lon = get_lat_lon_for_img(image)

    img_date_time = extract_exif_gps_timestamp(image)

    return ExifDataResult(latitude=lat, longitude=lon, timestamp=img_date_time)

@app.post("/predict")
async def perform_claim_deduction(image_s3_key: str, image_filename: str, claim_report: str, claim_type: str, csim_threshold: float) -> DeductionResult:
    """
    Perform claim deduction based on the provided image and claim details.
    Args:
        image_s3_key (str): The S3 key of the image to be processed.
        image_filename (str): The filename of the image.
        claim_report (str): The report associated with the claim.
        claim_type (str): The type of the claim.
        csim_threshold (float): The threshold for the claim similarity.
    Returns:
        DeductionResult: The result of the deduction process.
    """
       
    # Download the file from S3
    response = s3.get_object(Bucket=STORAGE_BUCKET, Key=image_s3_key)
    file_content = response['Body'].read()

    # Create BytesIO object from the file content
    image_bytes = io.BytesIO(file_content)  
    image = Image.open(image_bytes)
    image = image.convert('RGB')
    
    # Call the deduction method
    deduction = perform_deduction(
        image, 
        filename=image_filename, 
        claim_report=claim_report, 
        claim_type=claim_type, 
        csim_threshold=csim_threshold
    )
    
    return DeductionResult(deduction=deduction)


@app.get("/healthcheck")
async def healthcheck():
    """
    Endpoint for healthcheck.

    Returns:
        dict: A dictionary with a message indicating the health status.
    """
    return {"message": "OK"}

handler = Mangum(app)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
