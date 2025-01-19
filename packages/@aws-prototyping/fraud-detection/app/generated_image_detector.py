import ast
import io
import os

import PIL
import boto3
from dotenv import load_dotenv
import numpy as np
from paths import is_running_on_ecs
from PIL.Image import Image

if not is_running_on_ecs():
    load_dotenv(".env")
    
SM_ENDPOINT_NAME_SSM_PARAMETER = os.getenv(
    "SM_ENDPOINT_NAME_SSM_PARAMETER", "fraud-detection-endpoint")  # The name of the SageMaker endpoint

print('Using endpoint:', SM_ENDPOINT_NAME_SSM_PARAMETER)

def does_endpoint_exist()->bool:
    """
    Checks if the SageMaker endpoint exists.

    Returns:
        bool: True if the endpoint exists, False otherwise.
    """
    
    if not SM_ENDPOINT_NAME_SSM_PARAMETER:
        return False
    
    # Get the value of the SageMaker endpoint name from the parameter store
    ssm = boto3.client('ssm')
    ssm_response = ssm.get_parameter(Name=SM_ENDPOINT_NAME_SSM_PARAMETER)
    SAGEMAKER_ENDPOINT_NAME = ssm_response['Parameter']['Value']
    
    client = boto3.client('sagemaker')
    try:
        response = client.describe_endpoint(
            EndpointName=SAGEMAKER_ENDPOINT_NAME
        )
        return True
    except client.exceptions.ClientError as e:
        if "Could not find endpoint" in str(e):
            return False
    except:
            return False
    return False
        

def train_model():
    """
    Trains the model for fraud detection.

    This function performs the training of the fraud detection model. It can be customized
    to include specific training algorithms, data preprocessing steps, and model evaluation
    techniques.

    Parameters:
        None

    Returns:
        None
    """
    pass


def detect_generated_image(img: PIL.Image):
    """
    Detects whether an image is generated or real using a machine learning model.

    Args:
        img (PIL.Image): The input image to be classified.

    Returns:
        dict: A dictionary containing the prediction and confidence level.
            - 'prediction' (str): The predicted class label ('FAKE' or 'REAL').
            - 'confidence' (float): The confidence level of the prediction.
    """
    
    if not does_endpoint_exist():
        raise Exception("The SageMaker endpoint does not exist.")
    
    client = boto3.client('runtime.sagemaker')

    buffer = io.BytesIO()
    img = img.resize((32, 32), PIL.Image.LANCZOS)
    img = img.convert('RGB')
    img.save(buffer, format="JPEG")
    image_bytes = buffer.getvalue()

    # Read the endpoint name from the parameter store
    ssm = boto3.client('ssm')
    ssm_response = ssm.get_parameter(Name=SM_ENDPOINT_NAME_SSM_PARAMETER)

    response = client.invoke_endpoint(
        EndpointName=ssm_response['Parameter']['Value'],
        Body=image_bytes,
        # Adjust if your endpoint expects a different format
        ContentType='application/x-image',
    )

    result = response['Body'].read().decode('utf-8')
    print(result)
    prediction_result = ast.literal_eval(result)
    predicted_class = np.argmax(prediction_result)

    labels = ['FAKE', 'REAL']
    return {"prediction": labels[predicted_class], "confidence": prediction_result[predicted_class]}
