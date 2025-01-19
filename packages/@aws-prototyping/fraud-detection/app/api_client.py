import requests
from typing import Optional, List
from PIL import Image
import io
import os
from requests_auth_aws_sigv4 import AWSSigV4
from fd_api_client.models.deduction_result import DeductionResult
from fd_api_client.models.exif_data_result import ExifDataResult
from fd_api_client.models.reverse_image_search_result import ReverseImageSearchResult
from fd_api_client.models.library_image_with_score import LibraryImageWithScore
from fd_api_client.models.reverse_image_search_results import ReverseImageSearchResults
import boto3
from dotenv import load_dotenv
import uuid
load_dotenv()
s3 = boto3.client('s3')

STORAGE_BUCKET = os.environ.get("STORAGE_BUCKET", "STORAGE_BUCKET")

REQUEST_HEADERS = {
    'accept': '*/*',
    'content-type': 'application/json',
}

class FraudDetectionAPIClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        if base_url:
            self.base_url = base_url
        else:
            self.base_url = os.getenv("API_ENDPOINT")

    def default_route(self) -> dict:
        """
        Call the default route of the API.

        Returns:
            dict: A dictionary containing the welcome message.
        """
        response = requests.get(f"{self.base_url}",headers=REQUEST_HEADERS,auth=AWSSigV4('execute-api'))
        response.raise_for_status()
        return response.json()

    def search_image_library(self, image: Image.Image, sim_thresh: float = 0.9) -> list[LibraryImageWithScore]:
       
        """
        Search the image library for similar images. 
        This method uploads the image to S3 rather than sending it in the HTTP request body to cope with larger files.

        Args:
            image (Image.Image): The image to search for.
            sim_thresh (float, optional): Similarity threshold. Defaults to 0.9.

        Returns:
            list: A list of LibraryImageWithScore objects.
        """
        

        
        # Convert the image to bytes
        image_bytes = io.BytesIO()
        image.save(image_bytes, format='PNG')  # Save the image to the BytesIO object
        image_bytes.seek(0)  # Reset the pointer to the beginning of the BytesIO object

        # Create a new UUID as the S3 key prefix, and add it to the filename to create the S3 key
        s3_key = f"temp/{uuid.uuid4()}/image.png"
        # Upload the image to S3
        s3.put_object(Bucket=STORAGE_BUCKET, Key=s3_key, Body=image_bytes, ContentType='image/png')

        params = {'sim_thresh': sim_thresh,'image_s3_key': s3_key}
        
        response = requests.post(f"{self.base_url}searchlibrary", params=params,auth=AWSSigV4('execute-api'))
        response.raise_for_status()
        response_obj = response.json()
        lib_scores = [LibraryImageWithScore(**img) for img in response_obj]
        
        # Delete the temp item from S3
        s3.delete_object(Bucket=STORAGE_BUCKET, Key=s3_key)
        
        return lib_scores

    def reverse_internet_search(self, image: Image.Image, sim_thresh: float = 0.9) -> ReverseImageSearchResults:
        """
        Perform a reverse internet search using the provided image.
        This method uploads the image to S3 rather than sending it in the HTTP request body to cope with larger files.
        
        Args:
            image (Image.Image): The image to search for.
            sim_thresh (float, optional): Similarity threshold. Defaults to 0.9.

        Returns:
            ReverseImageSearchResults: An object containing the results of the reverse image search.
            To access the list of results, use the 'results' attribute of this object.
        """
        
        # Convert the image to bytes
        image_bytes = io.BytesIO()
        image.save(image_bytes, format='PNG')  # Save the image to the BytesIO object
        image_bytes.seek(0)  # Reset the pointer to the beginning of the BytesIO object

        # Create a new UUID as the S3 key prefix, and add it to the filename to create the S3 key
        s3_key = f"temp/{uuid.uuid4()}/image.png"
        # Upload the image to S3
        s3.put_object(Bucket=STORAGE_BUCKET, Key=s3_key, Body=image_bytes, ContentType='image/png')

        params = {'sim_thresh': sim_thresh,'image_s3_key': s3_key,'filename': image.filename}
        
        response = requests.post(f"{self.base_url}search/internet", params=params,auth=AWSSigV4('execute-api'),timeout=60)
        response.raise_for_status()
        reponse_obj =  ReverseImageSearchResults(**response.json())
        # Delete the temp item from S3
        s3.delete_object(Bucket=STORAGE_BUCKET, Key=s3_key)
        return reponse_obj

    def extract_exif_data(self, image: Image.Image) -> ExifDataResult:
        """
        Extract EXIF data from the provided image.
        This method uploads the image to S3 rather than sending it in the HTTP request body to cope with larger files.

        Args:
            image (Image.Image): The image to extract EXIF data from.

        Returns:
            dict: The extracted EXIF data.
        """
        # Convert the image to bytes
        image_bytes = io.BytesIO()
        image.save(image_bytes, format='PNG')  # Save the image to the BytesIO object
        image_bytes.seek(0)  # Reset the pointer to the beginning of the BytesIO object

        # Create a new UUID as the S3 key prefix, and add it to the filename to create the S3 key
        s3_key = f"temp/{uuid.uuid4()}/image.png"
        # Upload the image to S3
        s3.put_object(Bucket=STORAGE_BUCKET, Key=s3_key, Body=image_bytes, ContentType='image/png')
        
        params = {'image_s3_key': s3_key}
        
        response = requests.post(f"{self.base_url}exifdata", params=params,auth=AWSSigV4('execute-api'))
        response.raise_for_status()
      
        response_obj =  ExifDataResult(**response.json())
        
        # Delete the temp item from S3
        s3.delete_object(Bucket=STORAGE_BUCKET, Key=s3_key)
        
        return response_obj

    def perform_claim_deduction(self, image: Image.Image, claim_report: str, claim_type: str, csim_threshold: float) -> DeductionResult:
        """
        Perform claim deduction based on the provided image and claim details.
        This method uploads the image to S3 rather than sending it in the HTTP request body to cope with larger files.

        Args:
            image (Image.Image): The image related to the claim.
            claim_report (str): The claim report text.
            claim_type (str): The type of claim.
            csim_threshold (float): The similarity threshold for claim deduction.

        Returns:
            dict: The result of the claim deduction.
        """
         # Convert the image to bytes
        image_bytes = io.BytesIO()
        image.save(image_bytes, format='PNG')  # Save the image to the BytesIO object
        image_bytes.seek(0)  # Reset the pointer to the beginning of the BytesIO object

        # Create a new UUID as the S3 key prefix, and add it to the filename to create the S3 key
        s3_key = f"temp/{uuid.uuid4()}/image.png"
        # Upload the image to S3
        s3.put_object(Bucket=STORAGE_BUCKET, Key=s3_key, Body=image_bytes, ContentType='image/png')
        
        params = {'image_s3_key': s3_key,'claim_report': claim_report,'claim_type': claim_type,'csim_threshold': csim_threshold,'image_filename': image.filename}

        try:
            response = requests.post(
                f"{self.base_url}predict", 
                params=params,
                auth=AWSSigV4('execute-api')
            )
            response.raise_for_status()
            det_result = DeductionResult(**response.json())
            # Delete the temp item from S3
            s3.delete_object(Bucket=STORAGE_BUCKET, Key=s3_key)
            return det_result
        except requests.exceptions.RequestException as e:
            raise Exception(f"Request failed: {str(e)}")

    def healthcheck(self) -> dict:
        """
        Perform a healthcheck on the API.

        Returns:
            dict: The health status of the API.
        """
        response = requests.get(f"{self.base_url}healthcheck",auth=AWSSigV4('execute-api'))
        response.raise_for_status()
        return response.json()

# Example usage:
# client = FraudDetectionAPIClient()
# welcome_message = client.default_route()
# print(welcome_message)
