# fd_api_client.DefaultApi

All URIs are relative to *http://localhost*

Method | HTTP request | Description
------------- | ------------- | -------------
[**default_route_get**](DefaultApi.md#default_route_get) | **GET** / | Default Route
[**extract_exif_data_exifdata_post**](DefaultApi.md#extract_exif_data_exifdata_post) | **POST** /exifdata | Extract Exif Data
[**healthcheck_healthcheck_get**](DefaultApi.md#healthcheck_healthcheck_get) | **GET** /healthcheck | Healthcheck
[**perform_claim_deduction_predict_post**](DefaultApi.md#perform_claim_deduction_predict_post) | **POST** /predict | Perform Claim Deduction
[**reverse_internet_search_search_internet_post**](DefaultApi.md#reverse_internet_search_search_internet_post) | **POST** /search/internet | Reverse Internet Search
[**search_image_library_searchlibrary_post**](DefaultApi.md#search_image_library_searchlibrary_post) | **POST** /searchlibrary | Search Image Library


# **default_route_get**
> object default_route_get()

Default Route

Default route for the Fraud Detection API.  Returns:     dict: A dictionary containing a welcome message.

### Example


```python
import fd_api_client
from fd_api_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = fd_api_client.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with fd_api_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = fd_api_client.DefaultApi(api_client)

    try:
        # Default Route
        api_response = api_instance.default_route_get()
        print("The response of DefaultApi->default_route_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DefaultApi->default_route_get: %s\n" % e)
```



### Parameters

This endpoint does not need any parameter.

### Return type

**object**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **extract_exif_data_exifdata_post**
> ExifDataResult extract_exif_data_exifdata_post(image_file)

Extract Exif Data

Endpoint for making predictions.  Returns:     dict: A dictionary with a message indicating the prediction status.

### Example


```python
import fd_api_client
from fd_api_client.models.exif_data_result import ExifDataResult
from fd_api_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = fd_api_client.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with fd_api_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = fd_api_client.DefaultApi(api_client)
    image_file = None # bytearray | 

    try:
        # Extract Exif Data
        api_response = api_instance.extract_exif_data_exifdata_post(image_file)
        print("The response of DefaultApi->extract_exif_data_exifdata_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DefaultApi->extract_exif_data_exifdata_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **image_file** | **bytearray**|  | 

### Return type

[**ExifDataResult**](ExifDataResult.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: multipart/form-data
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **healthcheck_healthcheck_get**
> object healthcheck_healthcheck_get()

Healthcheck

Endpoint for healthcheck.  Returns:     dict: A dictionary with a message indicating the health status.

### Example


```python
import fd_api_client
from fd_api_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = fd_api_client.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with fd_api_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = fd_api_client.DefaultApi(api_client)

    try:
        # Healthcheck
        api_response = api_instance.healthcheck_healthcheck_get()
        print("The response of DefaultApi->healthcheck_healthcheck_get:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DefaultApi->healthcheck_healthcheck_get: %s\n" % e)
```



### Parameters

This endpoint does not need any parameter.

### Return type

**object**

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: Not defined
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **perform_claim_deduction_predict_post**
> DeductionResult perform_claim_deduction_predict_post(claim_report, claim_type, csim_threshold, image_file)

Perform Claim Deduction

Endpoint for making predictions.  Returns:     dict: A dictionary with a message indicating the prediction status.

### Example


```python
import fd_api_client
from fd_api_client.models.deduction_result import DeductionResult
from fd_api_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = fd_api_client.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with fd_api_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = fd_api_client.DefaultApi(api_client)
    claim_report = 'claim_report_example' # str | 
    claim_type = 'claim_type_example' # str | 
    csim_threshold = 3.4 # float | 
    image_file = None # bytearray | 

    try:
        # Perform Claim Deduction
        api_response = api_instance.perform_claim_deduction_predict_post(claim_report, claim_type, csim_threshold, image_file)
        print("The response of DefaultApi->perform_claim_deduction_predict_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DefaultApi->perform_claim_deduction_predict_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **claim_report** | **str**|  | 
 **claim_type** | **str**|  | 
 **csim_threshold** | **float**|  | 
 **image_file** | **bytearray**|  | 

### Return type

[**DeductionResult**](DeductionResult.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: multipart/form-data
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **reverse_internet_search_search_internet_post**
> ReverseImageSearchResults reverse_internet_search_search_internet_post(image_file, sim_thresh=sim_thresh)

Reverse Internet Search

Performs a reverse internet search using an uploaded image file. Args:     image_file (UploadFile): The uploaded image file to be searched.     sim_thresh (float, optional): The similarity threshold for the search. Defaults to 0.9. Returns:     ReverseImageSearchResults: The results of the reverse image search.

### Example


```python
import fd_api_client
from fd_api_client.models.reverse_image_search_results import ReverseImageSearchResults
from fd_api_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = fd_api_client.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with fd_api_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = fd_api_client.DefaultApi(api_client)
    image_file = None # bytearray | 
    sim_thresh = 0.9 # float |  (optional) (default to 0.9)

    try:
        # Reverse Internet Search
        api_response = api_instance.reverse_internet_search_search_internet_post(image_file, sim_thresh=sim_thresh)
        print("The response of DefaultApi->reverse_internet_search_search_internet_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DefaultApi->reverse_internet_search_search_internet_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **image_file** | **bytearray**|  | 
 **sim_thresh** | **float**|  | [optional] [default to 0.9]

### Return type

[**ReverseImageSearchResults**](ReverseImageSearchResults.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: multipart/form-data
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

# **search_image_library_searchlibrary_post**
> List[LibraryImageWithScore] search_image_library_searchlibrary_post(image_file, sim_thresh=sim_thresh)

Search Image Library

Searches the image library for images similar to the provided image file. Args:     image_file (UploadFile): The image file to search for similar images.     sim_thresh (float, optional): The similarity threshold for filtering images. Defaults to 0.9. Returns:     list[LibraryImageWithScore]: A list of images from the library that have a similarity score greater than the specified threshold.

### Example


```python
import fd_api_client
from fd_api_client.models.library_image_with_score import LibraryImageWithScore
from fd_api_client.rest import ApiException
from pprint import pprint

# Defining the host is optional and defaults to http://localhost
# See configuration.py for a list of all supported configuration parameters.
configuration = fd_api_client.Configuration(
    host = "http://localhost"
)


# Enter a context with an instance of the API client
with fd_api_client.ApiClient(configuration) as api_client:
    # Create an instance of the API class
    api_instance = fd_api_client.DefaultApi(api_client)
    image_file = None # bytearray | 
    sim_thresh = 0.9 # float |  (optional) (default to 0.9)

    try:
        # Search Image Library
        api_response = api_instance.search_image_library_searchlibrary_post(image_file, sim_thresh=sim_thresh)
        print("The response of DefaultApi->search_image_library_searchlibrary_post:\n")
        pprint(api_response)
    except Exception as e:
        print("Exception when calling DefaultApi->search_image_library_searchlibrary_post: %s\n" % e)
```



### Parameters


Name | Type | Description  | Notes
------------- | ------------- | ------------- | -------------
 **image_file** | **bytearray**|  | 
 **sim_thresh** | **float**|  | [optional] [default to 0.9]

### Return type

[**List[LibraryImageWithScore]**](LibraryImageWithScore.md)

### Authorization

No authorization required

### HTTP request headers

 - **Content-Type**: multipart/form-data
 - **Accept**: application/json

### HTTP response details

| Status code | Description | Response headers |
|-------------|-------------|------------------|
**200** | Successful Response |  -  |
**422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to Model list]](../README.md#documentation-for-models) [[Back to README]](../README.md)

