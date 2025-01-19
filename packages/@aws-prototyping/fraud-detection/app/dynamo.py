import boto3


class DynamoDBHandler:
    """
    A class that provides methods to interact with a DynamoDB table.

    Attributes:
        table_name (str): The name of the DynamoDB table.

    Methods:
        save_item(item): Save item to DynamoDB table.
        get_item(primary_key): Get item from DynamoDB table based on primary key.
        list_items(): List all items from DynamoDB table.
        delete_item(primary_key): Delete item from DynamoDB table based on primary key.
    """

    def __init__(self, table_name):
        self.dynamodb = boto3.resource('dynamodb')
        self.table = self.dynamodb.Table(table_name)

    def save_item(self, item):
        """Save item to DynamoDB table."""
        try:
            response = self.table.put_item(Item=item)
            return response
        except Exception as e:
            print(f"Error saving item: {e}")
            return None

    def get_item(self, primary_key):
        """Get item from DynamoDB table based on primary key."""
        try:
            response = self.table.get_item(Key=primary_key)
            return response.get('Item', None)
        except Exception as e:
            print(f"Error getting item: {e}")
            return None

    def list_items(self):
        """List all items from DynamoDB table."""
        try:
            response = self.table.scan()
            return response.get('Items', [])
        except Exception as e:
            print(f"Error listing items: {e}")
            return []

    def delete_item(self, primary_key):
        """Delete item from DynamoDB table based on primary key."""
        try:
            response = self.table.delete_item(Key=primary_key)
            return response
        except Exception as e:
            print(f"Error deleting item: {e}")
            return None
