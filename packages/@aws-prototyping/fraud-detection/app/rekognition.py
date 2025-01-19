import io

import PIL
import boto3
from PIL import ImageDraw
from PIL import ImageFont
from PIL.Image import Image

from paths import is_running_on_ecs


def detect_labels_in_image(img, confidence_threshold=90):
    # Initialize Rekognition client
    rekognition = boto3.client('rekognition')

    # Convert the image to bytes
    img_byte_array = io.BytesIO()
    img.save(img_byte_array, format=img.format)
    image_bytes = img_byte_array.getvalue()

    # Use Rekognition to detect labels
    response = rekognition.detect_labels(Features=["GENERAL_LABELS"], Image={'Bytes': image_bytes})
    print(f'Rekognition response: {response}')
    return response


def display_labels_in_image(image: PIL.Image.Image, response, confidence_thresh=80):
    # Ready image to draw bounding boxes on it.
    imgWidth, imgHeight = image.size
    draw = ImageDraw.Draw(image)

    for label in response['Labels']:

        for label_instance in label["Instances"]:
            if label["Confidence"] < confidence_thresh:
                continue
            box = label_instance['BoundingBox']
            print(f'bbox: {box}')
            left = imgWidth * box['Left']
            top = imgHeight * box['Top']
            width = imgWidth * box['Width']
            height = imgHeight * box['Height']

            fnt = ImageFont.load_default()
            draw.text((left, top), label['Name'], fill='#00d400', font=fnt)

            print('Left: ' + '{0:.0f}'.format(left))
            print('Top: ' + '{0:.0f}'.format(top))
            print('Label Width: ' + "{0:.0f}".format(width))
            print('Label Height: ' + "{0:.0f}".format(height))

            points = (
                (left, top),
                (left + width, top),
                (left + width, top + height),
                (left, top + height),
                (left, top))
            draw.line(points, fill='#00d400', width=5)

    return image
