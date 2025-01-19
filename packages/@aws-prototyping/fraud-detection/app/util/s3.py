import base64
from io import BytesIO
import io
import os
import uuid
import boto3
import PIL
import requests


def upload_image_to_s3(bucket_name: str, image: PIL.Image, filename):
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


def make_data_url(img: PIL.Image, fmt: str = None):
    """ """

    if fmt is None:
        fmt = img.format

    buf = io.BytesIO()
    img.thumbnail((500, 500), PIL.Image.LANCZOS)
    img.save(buf, format=fmt)
    bytes_str = base64.b64encode(buf.getvalue()).decode()
    data_url = f"data:image/{fmt.lower()};base64,{bytes_str}"

    return data_url


def url_to_base64(url):
    try:
        # Fetch the content from the URL
        response = requests.get(url)
        response.raise_for_status()

        # Open the content as an image
        img = PIL.Image.open(BytesIO(response.content))
        return make_data_url(img)

    except (requests.RequestException, PIL.Image.UnidentifiedImageError):
        # Return None if there's any error (e.g., URL is not accessible or not an image)
        return None


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
