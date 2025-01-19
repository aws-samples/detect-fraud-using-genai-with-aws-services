from datetime import datetime
import io
import os
import sys
from typing import List
import uuid
import timm
import pandas as pd
import torch
from torchvision import transforms
from timm.data import resolve_data_config
from timm.data.transforms_factory import create_transform
import PIL
import PIL.Image
from schemas.schemas import LibraryImage
from dotenv import load_dotenv
import boto3
from opensearch_manager import ImageEmbeddingManager
from schemas.schemas import LibraryImageWithScore
from util.s3 import url_to_base64, make_data_url, generate_presigned_url, upload_image_to_s3
from util.file import format_file_size
from concurrent.futures import ThreadPoolExecutor
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

dynamodb = boto3.resource('dynamodb')

OPENSEARCH_ENDPOINT = os.environ.get("OPENSEARCH_DOMAIN", "OPENSEARCH_DOMAIN")
STORAGE_BUCKET = os.environ.get("STORAGE_BUCKET", "STORAGE_BUCKET")
LIBRARY_FILES_TABLE = os.environ.get(
    "LIBRARY_FILES_TABLE", "LIBRARY_FILES_TABLE")
VECTOR_INDEX_NAME = os.environ.get("VECTOR_INDEX_NAME", "VECTOR_INDEX_NAME")
table = dynamodb.Table(LIBRARY_FILES_TABLE)
model_name = "hf_hub:timm/vit_base_patch16_224_miil.in21k"


class S3ImageLibrary:
    '''
    S3ImageLibrary is a class that manages an image library stored in S3, with image embeddings indexed in OpenSearch. 
    It provides functionalities to add, retrieve, delete, and search images within the library.
    '''

    def __init__(self, opensearch_host=OPENSEARCH_ENDPOINT) -> None:
        """
        Initializes the S3ImageLibrary with a Vision Transformer (ViT) model and an ImageEmbeddingManager.

        Args:
            opensearch_host (str, optional): The OpenSearch endpoint. Defaults to OPENSEARCH_ENDPOINT.

        Attributes:
            _model: The Vision Transformer (ViT) model loaded from timm.
            _config: The data configuration resolved for the model.
            _tfms: The transformation pipeline created based on the model configuration.
            _embeddings_manager: The manager for handling image embeddings with OpenSearch.
        """
        # Load the ViT model from timm
        self._model = timm.create_model(
            model_name, pretrained=True, num_classes=0)
        self._model.eval()

        self._config = resolve_data_config({}, model=self._model)
        self._tfms = create_transform(**self._config)
        self._embeddings_manager = ImageEmbeddingManager(
            endpoint=opensearch_host, index_name=VECTOR_INDEX_NAME)

        print(
            f'Initialized S3ImageLibrary with Opensearch host {opensearch_host}')

    def get_image(self, image_id: str) -> LibraryImage | None:
        """
        Retrieves an image from the library based on the given image ID.

        Parameters:
            image_id (str): The ID of the image to retrieve.

        Returns:
            LibraryImage | None: The retrieved image if found, None otherwise.
        """
        response = table.get_item(Key={'id': image_id})
        item = response.get('Item', None)
        if item:
            return LibraryImage(**item)
        return None

    def format_df(self, df_results: pd.DataFrame) -> pd.DataFrame:
        """
        Formats the given DataFrame by adding missing columns and populating the 'thumbnail' and 'filesize' columns.

        Args:
            df_results (pandas.DataFrame): The DataFrame to be formatted.

        Returns:
            pandas.DataFrame: The formatted DataFrame with added columns and populated 'thumbnail' and 'filesize' columns.
        """

        columns = ['id', 'filename', 'filesize', 'thumbnail']

        for col in columns:
            if col not in df_results.columns:
                df_results[col] = ''

        if 'similarity' not in df_results.columns:
            df_results['similarity'] = 0.0

        for idx, row in df_results.iterrows():
            if "thumbnail_s3_key" in row and row["thumbnail_s3_key"]:
                base_64_image = url_to_base64(generate_presigned_url(
                    STORAGE_BUCKET, row['thumbnail_s3_key']))
                df_results.at[idx, "thumbnail"] = base_64_image
                df_results.at[idx, "filesize"] = format_file_size(row["size"])

        df_results = df_results[['filename', 'filesize', 'thumbnail', 'similarity']].sort_values(by="filename",
                                                                                                 ascending=False)

        return df_results

    def to_dataframe(self) -> pd.DataFrame:
        """
        Converts a list of LibraryImage objects into a pandas DataFrame.

        Parameters:
            images (List[LibraryImage]): The list of LibraryImage objects to convert.

        Returns:
            pd.DataFrame: The DataFrame containing the image data.
        """
        data = [image.model_dump() for image in self.get_images()]
        df_results = pd.DataFrame(data)
        df_results = self.format_df(df_results)
        return df_results

    def get_images(self) -> List[LibraryImage]:
        """
        Retrieves all images from the library.

        Returns:
            List[LibraryImage]: A list of all images in the library.
        """
        response = table.scan()
        items = response.get('Items', [])
        images = [LibraryImage(**item) for item in items]

        # Check if there are more items to fetch
        while 'LastEvaluatedKey' in response:
            last_key = response['LastEvaluatedKey']
            response = table.scan(ExclusiveStartKey=last_key)
            items = response.get('Items', [])
            images.extend([LibraryImage(**item) for item in items])

        return images

    def _extract_image_features(self, image: PIL.Image.Image) -> List[float]:
        """
        Extracts features from an image using a pre-trained model.

        Args:
            image (PIL.Image.Image): The input image to extract features from.

        Returns:
            List[float]: A list of extracted features as a numpy array.
        """
        # Load and preprocess the image
        with torch.no_grad():
            # Apply the transformation pipeline to the image and stack it into a batch of size 1
            inputs = torch.stack([self._tfms(image)])
            # Extract features from the image using the pre-trained model
            features = self._model(inputs)
            # Squeeze the features tensor to remove unnecessary dimensions and convert it to a numpy array
            X_emb = features.squeeze().cpu().numpy()

        return X_emb

    def clear_library(self) -> None:
        """
        Clears all images from the library. WARNING: This operation is irreversible.
        """
        images = self.get_images()
        with ThreadPoolExecutor() as executor:
            executor.map(self.delete_image, (image.id for image in images))

    def add_image(self, image: PIL.Image.Image, filename: str) -> LibraryImage:
        """
        Adds an image to the library by uploading it to S3, creating a thumbnail, extracting image features, 
        and indexing the features in OpenSearch.

        Args:
            image (PIL.Image.Image): The image to be added.
            filename (str): The filename of the image.

        Returns:
            LibraryImage: An object containing metadata about the added image, including S3 keys, 
                          creation timestamp, size, and OpenSearch ID.
        """
        image_obj = {}
        temp_id = str(uuid.uuid4())
        image_obj["image_s3_key"] = f"images/{temp_id}.png"
        image_obj["created_timestamp"] = str(datetime.now())
        image_obj["filename"] = filename
       # Upload the image to S3
        buffer = io.BytesIO()
        image.save(buffer, 'PNG')
        buffer.seek(0)

        s3 = boto3.client('s3')
        s3.put_object(Bucket=STORAGE_BUCKET, Key=image_obj["image_s3_key"],
                      Body=buffer, ContentType='image/png')

        image_obj["size"] = buffer.getbuffer().nbytes

        # upload the thumbnail
        thumbnail = image.copy()
        thumbnail.thumbnail((256, 256))
        thumbnail_s3_key = f"thumbnails/{temp_id}.png"
        buffer = io.BytesIO()
        thumbnail.save(buffer, 'PNG')
        buffer.seek(0)
        s3.put_object(Bucket=STORAGE_BUCKET, Key=thumbnail_s3_key,
                      Body=buffer, ContentType='image/png')
        image_obj["thumbnail_s3_key"] = thumbnail_s3_key

        # Get the image features
        embeddings = self._extract_image_features(image)

        # Index the image features
        opensearch_id = self._embeddings_manager.add_embedding(embeddings)
        image_obj["id"] = opensearch_id
        table.put_item(Item=image_obj)

        return LibraryImage(**image_obj)

    def delete_image(self, image_id: str) -> None:
        img = self.get_image(image_id)
        s3 = boto3.client('s3')

        # download the image from S3 and load into memory

        response = s3.get_object(Bucket=STORAGE_BUCKET, Key=img.image_s3_key)
        

        self._embeddings_manager.remove_embedding(image_id=image_id)
        table.delete_item(Key={'id': image_id})
        s3.delete_object(Bucket=STORAGE_BUCKET, Key=img.image_s3_key)

    def search_images(self, image: PIL.Image.Image) -> List[LibraryImageWithScore]:
        # Load and preprocess the query image

        query_features = self._extract_image_features(image)

        # Search for similar images in the OpenSearch index
        similar_images = self._embeddings_manager.search_embeddings(
            query_features, n_results=100)

        # Retrieve the similar images from the library
        similar_images_with_score = []
        for similar_image in similar_images:
            lib_image = self.get_image(similar_image.id)

            if lib_image:
                similar_image_with_score = LibraryImageWithScore(
                    **lib_image.model_dump(), score=similar_image.score)
                similar_images_with_score.append(similar_image_with_score)
                print('Looking for image', similar_image_with_score.filename,
                      "score:", similar_image_with_score)

        return similar_images_with_score

    def search_images_return_dataframe(self, image: PIL.Image.Image) -> pd.DataFrame:
        """
        Converts a list of LibraryImage objects into a pandas DataFrame.

        Parameters:
            images (List[LibraryImage]): The list of LibraryImage objects to convert.

        Returns:
            pd.DataFrame: The DataFrame containing the image data.
        """
        search_results = self.search_images(image)
        df_results = pd.DataFrame(search_results)
        df_results = self.format_df(df_results)
        print("Image search results:", df_results.to_string())
        return df_results
