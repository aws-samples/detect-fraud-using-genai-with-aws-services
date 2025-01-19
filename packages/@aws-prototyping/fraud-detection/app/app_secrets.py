import boto3
from botocore.exceptions import ClientError


def get_secret_value(secret_name):
    """
    Retrieve the value of a secret from AWS Secrets Manager.

    Args:
        secret_name (str): The name of the secret to retrieve.

    Returns:
        str: The secret value if found, otherwise None.

    Raises:
        Exception: If the secret is not found or has no string value.

    Error Handling:
        - Prints an error message if the secret is not found (ResourceNotFoundException).
        - Prints an error message if the request is invalid (InvalidRequestException).
        - Prints an error message if the request has invalid parameters (InvalidParameterException).
        - Prints an error message for any other unhandled errors.
    """
    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(service_name='secretsmanager')

    try:
        # Use the client to retrieve the secret
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)

        # Error handling to be sure the secret was actually found.
        if 'SecretString' in get_secret_value_response:
            secret = get_secret_value_response['SecretString']
        else:
            raise Exception("Secret not found or has no string value.")

        return secret
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            print(f"The requested secret {secret_name} was not found")
        elif e.response['Error']['Code'] == 'InvalidRequestException':
            print("The request was invalid due to:", e)
        elif e.response['Error']['Code'] == 'InvalidParameterException':
            print("The request had invalid params:", e)
        else:
            print(f"Unhandled error: {e}")
        return None
