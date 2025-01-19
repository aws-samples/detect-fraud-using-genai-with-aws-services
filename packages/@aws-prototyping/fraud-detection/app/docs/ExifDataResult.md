# ExifDataResult

Represents GPS coordinates. Attributes:     latitude (float): The latitude of the location.     longitude (float): The longitude of the location.     timestamp (datetime): The timestamp of the location data

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**latitude** | **float** |  | [optional] 
**longitude** | **float** |  | [optional] 
**timestamp** | **datetime** |  | [optional] 

## Example

```python
from api_client.models.exif_data_result import ExifDataResult

# TODO update the JSON string below
json = "{}"
# create an instance of ExifDataResult from a JSON string
exif_data_result_instance = ExifDataResult.from_json(json)
# print the JSON string representation of the object
print(ExifDataResult.to_json())

# convert the object into a dict
exif_data_result_dict = exif_data_result_instance.to_dict()
# create an instance of ExifDataResult from a dict
exif_data_result_from_dict = ExifDataResult.from_dict(exif_data_result_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


