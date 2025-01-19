import boto3

client = boto3.client('location')


def get_coordinates_from_address(address):
    """
    Returns the latitude and longitude of a given address using Amazon Location Services.

    Args:
    - address (str): The street address.

    Returns:
    - (float, float): Tuple of latitude and longitude.
    """

    # Geocode the given address
    response = client.search_place_index_for_text(
        IndexName='claims-index',  # replace with your place index name
        Text=address,
        MaxResults=1
    )
    
    print('Response from search_place_index_for_text:', response)

    # Extract the coordinates from the response
    coordinates = response['Results'][0]['Place']['Geometry']['Point']

    return coordinates[1], coordinates[0]  # latitude, longitude


def address_lookup(lat: float, lon: float):
    lat = float(lat)
    lon = float(lon)
    
    print("Address lookup", lat, lon)
    
    # Ensure coordinates are within valid ranges (-180 to 180 for longitude, -90 to 90 for latitude)
    lon = max(min(lon, 180), -180)  # Clamp longitude
    lat = max(min(lat, 90), -90)    # Clamp latitude
    response = client.search_place_index_for_position(
            IndexName='claims-index',
            Position=[lon, lat]  # Note the order is [longitude, latitude]
        )
    print('Location response:', response)
    address = response['Results'][0]['Place']['Label']
    return address
