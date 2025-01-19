# ReverseImageSearchResult


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**data_url** | **str** |  | [optional] 
**source** | **str** |  | [optional] 
**csim** | **float** |  | [optional] 
**title** | **str** |  | [optional] 
**link** | **str** |  | [optional] 
**filename** | **str** |  | [optional] 

## Example

```python
from fd_api_client.models.reverse_image_search_result import ReverseImageSearchResult

# TODO update the JSON string below
json = "{}"
# create an instance of ReverseImageSearchResult from a JSON string
reverse_image_search_result_instance = ReverseImageSearchResult.from_json(json)
# print the JSON string representation of the object
print(ReverseImageSearchResult.to_json())

# convert the object into a dict
reverse_image_search_result_dict = reverse_image_search_result_instance.to_dict()
# create an instance of ReverseImageSearchResult from a dict
reverse_image_search_result_from_dict = ReverseImageSearchResult.from_dict(reverse_image_search_result_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


