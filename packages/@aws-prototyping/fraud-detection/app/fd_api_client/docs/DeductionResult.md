# DeductionResult

Represents the result of a deduction calculation or decision.  This class is used to store and validate the outcome of a deduction process. It inherits from Pydantic's BaseModel, ensuring that the data is properly validated and serialized.  Attributes:     deduction (str): A string representing the result of the claim deduction (whether fraud is detected and the confidence)

## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**deduction** | **str** |  | 

## Example

```python
from fd_api_client.models.deduction_result import DeductionResult

# TODO update the JSON string below
json = "{}"
# create an instance of DeductionResult from a JSON string
deduction_result_instance = DeductionResult.from_json(json)
# print the JSON string representation of the object
print(DeductionResult.to_json())

# convert the object into a dict
deduction_result_dict = deduction_result_instance.to_dict()
# create an instance of DeductionResult from a dict
deduction_result_from_dict = DeductionResult.from_dict(deduction_result_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


