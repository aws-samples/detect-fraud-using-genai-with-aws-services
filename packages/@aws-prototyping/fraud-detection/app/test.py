from dynamo import DynamoDBHandler

if __name__ == "__main__":
    handler = DynamoDBHandler("IndexedFiles")
    items = handler.list_items()
    for item in items:
        print(item)
    print(len(items), "items found.")
