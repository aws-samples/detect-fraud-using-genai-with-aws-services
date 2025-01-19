# LibraryImageWithScore

A data model representing a library image with its corresponding score. Attributes:     image (LibraryImage): The library image.     score (float): The score associated with the image.

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**id** | **str** |  | 
**image_s3_key** | **str** |  | 
**thumbnail_s3_key** | **str** |  | 
**filename** | **str** |  | 
**created_timestamp** | **str** |  | 
**size** | **int** |  | 
**score** | **float** |  | 

## Example

```python
from fd_api_client.models.library_image_with_score import LibraryImageWithScore

# TODO update the JSON string below
json = "{}"
# create an instance of LibraryImageWithScore from a JSON string
library_image_with_score_instance = LibraryImageWithScore.from_json(json)
# print the JSON string representation of the object
print(LibraryImageWithScore.to_json())

# convert the object into a dict
library_image_with_score_dict = library_image_with_score_instance.to_dict()
# create an instance of LibraryImageWithScore from a dict
library_image_with_score_from_dict = LibraryImageWithScore.from_dict(library_image_with_score_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


