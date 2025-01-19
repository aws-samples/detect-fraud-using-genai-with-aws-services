import PIL
from exifdata import get_lat_lon_for_img, extract_exif_gps_timestamp
from map import address_lookup
from generated_image_detector import detect_generated_image

def process_image(image: PIL.Image.Image):
    """
    Process the uploaded image and extract relevant information.
    
    Args:
        image (PIL.Image.Image): The uploaded image.
    
    Returns:
        dict: A dictionary containing extracted information from the image.
    """
    result = {}
    
    # Extract GPS coordinates
    lat, lon = get_lat_lon_for_img(image)
    if lat and lon:
        result['coordinates'] = (lat, lon)
        result['address'] = address_lookup(lat=lat, lon=lon)
    
    # Extract timestamp
    img_date_time = extract_exif_gps_timestamp(image)
    if img_date_time:
        result['timestamp'] = img_date_time
    
    # Detect if image is AI-generated
    detection_result = detect_generated_image(img=image)
    if detection_result["confidence"] >= 0.98 and detection_result["prediction"] == 'FAKE':
        result['ai_generated'] = {
            'confidence': detection_result["confidence"],
            'prediction': detection_result["prediction"]
        }
    
    return result
