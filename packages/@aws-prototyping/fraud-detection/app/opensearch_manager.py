import os
import sys
import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
import requests
from urllib.parse import urlparse
from schemas.schemas import EmbeddingsSearchResult

sys.path.append(os.path.dirname(os.path.abspath(__file__)))


class ImageEmbeddingManager:

    def __init__(self, endpoint, index_name):
        session = boto3.Session()
        credentials = session.get_credentials()
        auth = AWSV4SignerAuth(credentials,session.region_name, 'aoss')
        
        host = endpoint.replace("https://", "")
        
        self._host = host
        self.client = OpenSearch(
            hosts=[{'host': host, 'port': 443}],
            http_auth=auth,
            pool_maxsize=20,
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection
        )

        self._imageindex_name = index_name

    def add_embedding(self,  embedding) -> str:
        """
        Adds an embedding to the OpenSearch index.

        Args:
            embedding (numpy.ndarray): The embedding to be added.

        Returns:
            str: The ID of the added document.

        Raises:
            Exception: If there is an error adding the embedding to the index.
        """

        doc = {
            'embedding': embedding.tolist()
        }
        try:

            resp = self.client.index(index=self._imageindex_name, body=doc)
            print(
                f"Successfully added embedding - response {resp}")
            return resp["_id"]
        except Exception as e:
            print(f"Error adding embedding: {e}")

    def remove_embedding(self, image_id: str):
        """
        Removes an embedding from the OpenSearch index based on the provided image ID.

        Args:
            image_id (str): The ID of the image whose embedding is to be removed.

        Raises:
            Exception: If there is an error during the removal process.

        This method sends a DELETE request to the OpenSearch service to remove the document
        associated with the given image ID. It uses AWS SigV4 for request signing.
        """
        try:

            session = boto3.Session()
            credentials = session.get_credentials()

            # Prepare the request
            method = 'DELETE'

            url = f"https://{self._host}/{self._imageindex_name}/_doc/{image_id}"
            parsed_url = urlparse(url)
            print(parsed_url)
            headers = {}  # Initialize an empty headers dictionary

            # Create the request object
            request = AWSRequest(method=method, url=url, headers=headers)

            # Sign the request
            SigV4Auth(credentials, 'aoss', parsed_url.netloc.split(
                '.')[1]).add_auth(request)

            # Send the request
            response = requests.request(method,
                                        url,
                                        headers=dict(request.headers),
                                        verify=True, timeout=5)

            # Check the response
            if response.status_code in [200, 204]:
                print(f"Successfully removed embedding for {image_id}")

            else:
                print(
                    f"Failed to delete index. Status code: {response.status_code}")
                print(f"Response: {response.text}")

        except Exception as e:
            print(f"Error removing embedding for {image_id}: {e}")

    def search_embeddings(self, query_embedding, n_results=10) -> list[EmbeddingsSearchResult]:
        """
        Searches for embeddings in the OpenSearch index based on a given query embedding.

        Args:
            query_embedding (ndarray): The query embedding to search for.
            n_results (int, optional): The number of results to return. Defaults to 10.

        Returns:
            list: A list of image paths corresponding to the search results.

        Raises:
            Exception: If an error occurs while searching for embeddings.
        """
        script_query = {
            "knn": {
                "embedding": {
                    "vector": query_embedding,
                    "k": 10,
                }
            }
        }

        try:
            res = self.client.search(
                index=self._imageindex_name,
                body={
                    "_source": {"excludes": ["embedding"]},
                    "size": n_results,
                    "query": script_query,
                    "sort": [
                        {
                            "_score": {
                                "order": "desc"
                            }
                        }
                    ]
                }
            )

            results = []
            for hit in res['hits']['hits']:
                result = EmbeddingsSearchResult(
                    id=hit['_id'], score=hit['_score'])
                results.append(result)

            return results
        except Exception as e:
            print(f"Error searching for embeddings: {e}")
            return []
