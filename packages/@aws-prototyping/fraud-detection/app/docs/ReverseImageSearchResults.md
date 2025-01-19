# ReverseImageSearchResults


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**results** | [**List[ReverseImageSearchResult]**](ReverseImageSearchResult.md) |  | 

## Example

```python
from api_client.models.reverse_image_search_results import ReverseImageSearchResults

# TODO update the JSON string below
json = "{}"
# create an instance of ReverseImageSearchResults from a JSON string
reverse_image_search_results_instance = ReverseImageSearchResults.from_json(json)
# print the JSON string representation of the object
print(ReverseImageSearchResults.to_json())

# convert the object into a dict
reverse_image_search_results_dict = reverse_image_search_results_instance.to_dict()
# create an instance of ReverseImageSearchResults from a dict
reverse_image_search_results_from_dict = ReverseImageSearchResults.from_dict(reverse_image_search_results_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


