import os
import shutil
import string
import uuid
from hashlib import md5
from io import BytesIO
from urllib.parse import quote_plus

import PIL
import boto3
import pandas as pd
import requests
from PIL import Image
from dotenv import load_dotenv

from app_secrets import get_secret_value
from image_search import make_data_url, ImageLibrary, ImageChecker
from pydantic import BaseModel
from typing import List, Optional
from schemas.schemas import ReverseImageSearchResult, ReverseImageSearchResults

load_dotenv()
bucket_name = os.environ.get("STORAGE_BUCKET")
serp_api_key = get_secret_value(os.environ.get("SERP_API_KEY_SECRET"))
temp_opensearch_endpoint = os.environ.get("TEMP_OPENSEARCH_ENDPOINT")


def url_to_base64(url):
    try:
        # Fetch the content from the URL
        response = requests.get(url)
        response.raise_for_status()

        # Open the content as an image
        img = Image.open(BytesIO(response.content))
        return make_data_url(img)

    except (requests.RequestException, Image.UnidentifiedImageError):
        # Return None if there's any error (e.g., URL is not accessible or not an image)
        return None


def sanitize_title(title):
    return "".join([c for c in title if c.isalpha() or c.isdigit() or c == ' ']).rstrip().replace(" ", "_")




def reverse_image_search(image: PIL.Image, filename: str, sim_thresh: float) -> ReverseImageSearchResults:
    """
    Perform reverse image search using Google Lens API.

    Args:
        image (PIL.Image): The image to be searched.
        filename (str): The filename of the image.
        sim_thresh (float): The similarity threshold for image matching.

    Returns:
        ReverseImageSearchResults: A Pydantic model containing the search results.
    """
    s3key = upload_image_to_s3(image, filename)
    presigned_url = generate_presigned_url(bucket_name, s3key)

    encoded_url = quote_plus(presigned_url)

    params = {
        'api_key': serp_api_key,
        'engine': 'google_lens',
        'url': encoded_url,
        'hl': 'en',
    }

    response = requests.get("https://serpapi.com/search", params=params)
    response.raise_for_status()

    resp_json = response.json()
    print(f'Google Lens Response: {resp_json}')

    if "visual_matches" in resp_json:
        df_results = pd.DataFrame(resp_json["visual_matches"])

        if "thumbnail" in df_results.columns:
            df_results["data_url"] = df_results['thumbnail'].apply(
                url_to_base64)

        # create new logo library to check

        search_id = uuid.uuid4()

        if not os.path.exists(f'./searches/{search_id}/data/class1'):
            os.makedirs(f'./searches/{search_id}/data/class1')

        for idx, row in df_results.iterrows():
            response = requests.get(row['thumbnail'], stream=True)
            response.raise_for_status()

            # Construct unique filename using sanitized title and a short hash of the URL
            filename_base = str(idx)  # sanitize_title(row['title'])
            filename_hash = md5(row['thumbnail'].encode()).hexdigest()[:6]
            filename_ext = ".png"  # os.path.splitext(row['thumbnail'])[-1]
            unique_filename = f"{filename_base}_{filename_hash}{filename_ext}"

            df_results.at[idx, "uniquefilename"] = unique_filename

            with open(os.path.join(f'./searches/{search_id}/data/class1', unique_filename), 'wb') as file:
                for chunk in response.iter_content(chunk_size=8192):
                    file.write(chunk)

            print(f'Wrote file {unique_filename}')

        IMAGE_LIBRARY = ImageLibrary(f'./searches/{search_id}/data', f'./searches/{search_id}/images.db',
                                    f'./searches/{search_id}/images.ann', load_existing=False)

        imageChecker = ImageChecker(IMAGE_LIBRARY)

        similarity_results = imageChecker.find_similar(
            image, ["class1"], sim_thresh)

        if not similarity_results.empty:
            df_results = pd.merge(df_results, similarity_results, how='left',
                      left_on='uniquefilename', right_on='filename')
            df_results = df_results.rename(columns={'data_url_x': 'data_url'})
            
            df_results = df_results[['data_url', 'source', "csim", 'title', 'link']].sort_values(by="csim",
                                                                                             ascending=False)
        

        shutil.rmtree(f'./searches/{search_id}')
    else:
        df_results = pd.DataFrame()

    # Convert DataFrame to list of SearchResult objects
    search_results = [ReverseImageSearchResult(**row) for row in df_results.to_dict(orient="records")]

    return ReverseImageSearchResults(results=search_results)


def upload_image_to_s3(image: PIL.Image, filename):
    """
    Upload a PIL image to Amazon S3.

    Args:
    - image (PIL.Image.Image): The PIL image to upload.
    - bucket_name (str): The name of the bucket to upload to.
    - object_name (str): The name of the object to create in the bucket.

    Returns:
    str: The S3 URL of the uploaded image.
    """

    # Initialize S3 client
    s3 = boto3.client('s3')

    # Convert PIL image to bytes
    buffer = BytesIO()
    # You can change "JPEG" to whatever format your image is in, like "PNG".
    image.save(buffer, format="PNG")
    buffer.seek(0)
    base_name, _ = os.path.splitext(filename)
    s3key = f'{uuid.uuid4()}/{base_name}.png'

    # Upload the image
    s3.put_object(Bucket=bucket_name, Key=s3key,
                  Body=buffer, ContentType='image/png')

    return s3key


def generate_presigned_url(bucket_name, object_name, expiration=3600):
    """
    Generate a presigned URL to get the uploaded image.

    Args:
    - bucket_name (str): The name of the bucket.
    - object_name (str): The name of the object.
    - expiration (int): The time in seconds for which the presigned URL is valid.

    Returns:
    str: Presigned URL.
    """

    s3 = boto3.client('s3')
    presigned_url = s3.generate_presigned_url(
        'get_object',
        Params={'Bucket': bucket_name, 'Key': object_name},
        ExpiresIn=expiration
    )

    return presigned_url
