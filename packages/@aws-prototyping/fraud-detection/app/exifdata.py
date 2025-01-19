import os
from datetime import datetime
from pathlib import Path

import PIL
from PIL import ExifTags
from PIL import Image
from PIL.ExifTags import TAGS
from geopy.distance import geodesic as GD

from augment import get_all_files_in_directory, IMAGE_EXTENSIONS
from image_search import make_data_url_from_path

codec = 'ISO-8859-1'  # or latin-1

GPSINFO_TAG = next(
    tag for tag, name in TAGS.items() if name == "GPSInfo"
)


def get_distances(imagePath, lat: float, lon: float):
    """
    Calculate distances from a given latitude and longitude to GPS data extracted from an image.

    Args:
        imagePath (str): The file path to the image from which GPS data will be extracted.
        lat (float): The latitude to compare against the extracted GPS data.
        lon (float): The longitude to compare against the extracted GPS data.

    Returns:
        list: A list of dictionaries containing GPS data and calculated distances. Each dictionary
              includes the keys 'lat', 'lon', 'distance', and optionally 'data_url' if 'filepath' is present.
    """
    df_gps_data = get_gps_data(imagePath)

    for item in df_gps_data:
        df_lat = item["lat"]
        df_lon = item["lon"]
        if not df_lat or not df_lon:
            continue
        distance = GD((lat, lon), (df_lat, df_lon))
        item["distance"] = distance
        if "filepath" in df_gps_data:
            item["data_url"] = item['filepath'].apply(make_data_url_from_path)

    return df_gps_data


def decimal_coords(coords, ref):
    """
    Converts GPS coordinates in degrees, minutes, and seconds to decimal degrees.

    Args:
        coords (tuple): A tuple containing three elements (degrees, minutes, seconds).
        ref (str): A string indicating the reference direction ('N', 'S', 'E', 'W').

    Returns:
        float: The decimal representation of the GPS coordinates.
    """
    decimal_degrees = coords[0] + coords[1] / 60 + coords[2] / 3600
    if ref == 'S' or ref == 'W':
        decimal_degrees = -decimal_degrees
    return decimal_degrees


def get_lat_lon_for_img(img: PIL.Image):
    """
    Extracts the latitude and longitude from the EXIF data of an image.

    Args:
        img (PIL.Image): The image from which to extract the EXIF data.

    Returns:
        tuple: A tuple containing the latitude and longitude as floats.
    """
    exif_data = get_exif(img)

    lat, lon = get_exif_location(exif_data)
    return lat, lon


def get_exif_data_for_image(imageFilePath):
    file_name_with_extension = os.path.basename(imageFilePath)

    img = PIL.Image.open(imageFilePath)

    exif_data = get_exif(img)

    lat, lon = get_exif_location(exif_data)

    gps_data_item = {"filepath": imageFilePath, "filename": file_name_with_extension, "exif": exif_data, "lat": lat,
                     "lon": lon}

    return gps_data_item


def get_gps_data(imagePath):
    gps_data = []

    for imageFilePath in get_all_files_in_directory(imagePath):
        if not Path(imageFilePath).suffix in IMAGE_EXTENSIONS:
            continue

        gps_data.append(get_exif_data_for_image(imageFilePath))

    return gps_data


def _get_if_exist(data, key):
    if key in data:
        return data[key]

    return None


def _convert_to_degress(value):
    """
    Helper function to convert the GPS coordinates stored in the EXIF to degress in float format
    :param value:
    :type value: exifread.utils.Ratio
    :rtype: float
    """
    d = float(value[0])
    m = float(value[1])
    s = float(value[2])

    return d + (m / 60.0) + (s / 3600.0)


def get_exif_location(exif_data):
    """
    Returns the latitude and longitude, if available, from the provided exif_data (obtained through get_exif_data above)
    """
    lat = None
    lon = None

    gps_latitude = _get_if_exist(exif_data, 'GPSLatitude')
    gps_latitude_ref = _get_if_exist(exif_data, 'GPSLatitudeRef')
    gps_longitude = _get_if_exist(exif_data, 'GPSLongitude')
    gps_longitude_ref = _get_if_exist(exif_data, 'GPSLongitudeRef')

    if gps_latitude and gps_latitude_ref and gps_longitude and gps_longitude_ref:
        lat = _convert_to_degress(gps_latitude)
        if gps_latitude_ref != 'N':
            lat = 0 - lat

        lon = _convert_to_degress(gps_longitude)
        if gps_longitude_ref != 'E':
            lon = 0 - lon

    return lat, lon


def extract_exif_gps_timestamp(img: PIL.Image):
    """
    Extracts the GPS timestamp and datestamp from the EXIF data of an image.

    Args:
        img (PIL.Image): The image from which to extract EXIF data.

    Returns:
        datetime.datetime or None: A datetime object representing the GPS timestamp and datestamp if available,
                                   otherwise None.
    """
    exif_data = get_exif(img)
    # Assuming exif_data is a dictionary containing the EXIF tags and values

    # Extract the GPS timestamp and datestamp
    gps_timestamp = exif_data.get('GPSTimeStamp', None)
    gps_datestamp = exif_data.get('GPSDateStamp', None)

    print(f'timestamp {gps_timestamp}')

    # If the timestamp isn't available, return None or handle accordingly
    if not gps_datestamp or not gps_timestamp:
        return None

    # Extract hours, minutes, and seconds from the timestamp
    # The format is usually like ((h,1),(m,1),(s,1))
    h, m, s = map(int, gps_timestamp)

    # If the datestamp is available, extract year, month, and day
    if gps_datestamp:
        y, mo, d = map(int, gps_datestamp.split(':'))
        return datetime(y, mo, d, h, m, s)


def get_exif(image):
    """
    Extracts EXIF (Exchangeable Image File Format) data from an image.

    This function retrieves basic EXIF data such as camera make/model, GPS information, 
    and other metadata from the provided image object.

    Args:
        image (PIL.Image.Image): The image object from which to extract EXIF data.

    Returns:
        dict: A dictionary containing the extracted EXIF data. The keys are the EXIF tag names 
              and the values are the corresponding tag values.
    """
    data = dict()
    exif = image.getexif()
    if exif:
        # Basic exif (camera make/model, etc)
        for key, val in exif.items():
            if key in ExifTags.TAGS:
                data[ExifTags.TAGS[key]] = val

        # Aperture, shutter, flash, lens, tz offset, etc
        # ifd = exif.get_ifd(0x8769)
        # for key, val in ifd.items():
        #     data[ExifTags.TAGS[key]] = val

        # GPS Info
        ifd = exif.get_ifd(0x8825)
        for key, val in ifd.items():
            if key in ExifTags.GPSTAGS:
                data[ExifTags.GPSTAGS[key]] = val

    return data
