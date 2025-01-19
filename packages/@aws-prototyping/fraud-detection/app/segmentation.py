import io
import json
import os

import cv2
import numpy as np
from PIL import Image
from sagemaker import Predictor


def find_images(directory):
    image_extensions = {".jpg", ".jpeg", ".png"}
    image_files = []

    for dirpath, dirnames, filenames in os.walk(directory):
        for filename in filenames:
            if os.path.splitext(filename)[1].lower() in image_extensions:
                image_files.append(os.path.join(dirpath, filename))

    return image_files


def query(model_predictor, image: Image):
    """Query the model predictor."""

    print('Querying model predictor')

    byte_stream = io.BytesIO()
    image.save(byte_stream, format='PNG')  # you can change 'PNG' to other formats, e.g., 'JPEG'
    image_bytes = byte_stream.getvalue()

    query_response = model_predictor.predict(
        image_bytes,
        {
            "ContentType": "application/x-image",
            "Accept": "application/json;verbose",
        },
    )
    return query_response


def getvocpalette(num_cls):
    """Get a color palette."""

    n = num_cls
    palette = [0] * (n * 3)
    for j in range(0, n):
        lab = j
        palette[j * 3 + 0] = 0
        palette[j * 3 + 1] = 0
        palette[j * 3 + 2] = 0
        i = 0
        while lab > 0:
            palette[j * 3 + 0] |= ((lab >> 0) & 1) << (7 - i)
            palette[j * 3 + 1] |= ((lab >> 1) & 1) << (7 - i)
            palette[j * 3 + 2] |= ((lab >> 2) & 1) << (7 - i)
            i = i + 1
            lab >>= 3
    return palette


def get_prediction_image(predictions):
    """Display predictions with each pixel subsituted by the color of the corresponding label."""

    palette = getvocpalette(256)
    npimg = np.array(predictions)
    npimg[npimg == -1] = 255
    mask = Image.fromarray(npimg.astype("uint8"))

    mask.putpalette(palette)
    mask = mask.convert('RGB')
    mask.save("mask.png", format="PNG")

    return mask
    # mask.save("Mask_putput.png")

    # mmask = mpimg.imread("Mask_putput.png")


def parse_response(query_response):
    """Parse response and return predictions as well as the set of all labels and object labels present in the image."""
    response_dict = json.loads(query_response)
    return response_dict["predictions"], response_dict["labels"], response_dict["image_labels"]


def resize_image_if_needed(image: Image.Image, max_size: int = 1000) -> Image.Image:
    """
    Resize the image while maintaining its aspect ratio.
    If neither width nor height exceeds max_size, the original image is returned.

    Args:
    - image (Image.Image): The input PIL image.
    - max_size (int): The maximum allowed width or height.

    Returns:
    - Image.Image: The resized PIL image.
    """

    # Check if the image width or height exceeds the maximum size
    print(f'Image width: {image.width}, height: {image.height}')
    if image.width > max_size or image.height > max_size:
        # Calculate the aspect ratio
        aspect_ratio = image.width / image.height

        if image.width > image.height:
            new_width = max_size
            new_height = int(new_width / aspect_ratio)
        else:
            new_height = max_size
            new_width = int(new_height * aspect_ratio)
        print('Image resizing')
        # Resize the image
        return image.resize((new_width, new_height), Image.LANCZOS)
    else:
        # If neither width nor height exceeds max_size, return the original image
        print('Image does not need resizing')
        return image


def get_no_bg_img(original: Image, mask_image: Image):
    print('Removing background using original and prediction mask images.')

    pixelMap1 = original.load()
    pixelMap2 = mask_image.load()
    width1, height1 = original.size
    width2, height2 = mask_image.size

    # Set the height and width to the largest image

    if width2 > width1:
        width = width2
    else:
        width = width1

    if height2 > height1:
        height = height2
    else:
        height = height1

    background_removed = False

    for i in range(width):  # for every col:
        for j in range(height):  # For every row
            R1, G1, B1 = pixelMap2[i, j]
            if R1 != 0 and G1 != 0 and B1 != 0:
                pixelMap2[i, j] = pixelMap1[i, j]
                background_removed = True
            else:
                pixelMap2[i, j] = (0, 0, 0)

    mask_image.save('mask-final.png', format="PNG")

    mask_image = Image.open('mask-final.png')

    return mask_image, background_removed


# https://www.freedomvc.com/index.php/2022/01/17/basic-background-remover-with-opencv/
def bgremove(myimage: Image):
    open_cv_image = np.array(myimage)
    # First Convert to Grayscale
    myimage_grey = cv2.cvtColor(open_cv_image, cv2.COLOR_BGR2GRAY)

    ret, baseline = cv2.threshold(myimage_grey, 127, 255, cv2.THRESH_TRUNC)

    ret, background = cv2.threshold(baseline, 126, 255, cv2.THRESH_BINARY)

    ret, foreground = cv2.threshold(baseline, 126, 255, cv2.THRESH_BINARY_INV)

    foreground = cv2.bitwise_and(open_cv_image, open_cv_image,
                                 mask=foreground)  # Update foreground with bitwise_and to extract real foreground

    # Convert black and white back into 3 channel greyscale
    background = cv2.cvtColor(background, cv2.COLOR_GRAY2BGR)

    # Combine the background and foreground to obtain our final image
    finalimage = foreground  # background + foreground
    return Image.fromarray(finalimage)


def make_same_size(img1: Image.Image, img2: Image.Image) -> (Image.Image, Image.Image):
    """
    Resize two PIL images to have the same dimensions, which will be
    the dimensions of the larger image.

    Args:
    - img1 (Image.Image): The first image.
    - img2 (Image.Image): The second image.

    Returns:
    - (Image.Image, Image.Image): A tuple of the (potentially) resized images.
    """

    # If images are already of the same size, return them as they are
    if img1.size == img2.size:
        return img1, img2

    # Identify the larger dimensions
    max_width = max(img1.width, img2.width)
    max_height = max(img1.height, img2.height)

    # Resize the images to the larger dimensions
    img1_resized = img1.resize((max_width, max_height), Image.LANCZOS)
    img2_resized = img2.resize((max_width, max_height), Image.LANCZOS)

    return img1_resized, img2_resized


def modify_filename(path: str, suffix="_no_bg") -> str:
    """
    Modify the filename in the given absolute path by adding "_no_bg" to the end,
    and then return only the filename and extension.

    Args:
    - path (str): The absolute path to the file.

    Returns:
    - str: The modified filename with extension.
    """

    # Extract filename and extension
    base_name = os.path.basename(path)
    file_name, file_extension = os.path.splitext(base_name)

    # Modify the filename
    new_file_name = f"{file_name}{suffix}{file_extension}"

    return new_file_name


def build_bg_removed_dataset():
    image_files = find_images('./data/dataset/existing') + find_images('./data/dataset/external')
    # image_files = find_images('./data/test')

    print(f'Found {len(image_files)} images in directory.')
    predictor = Predictor(endpoint_name="jumpstart-example-infer-mxnet-semseg-fc-2023-10-11-23-00-51-349")

    for image_file in image_files:
        print(f'Processing {image_file}')
        img = Image.open(image_file)
        img = img.convert("RGB")
        # no_bg_img = bgremove(img)
        img = resize_image_if_needed(img)
        query_response = query(predictor, img)
        predictions, labels, image_labels = parse_response(query_response)
        print("Objects present in the picture:", image_labels)
        mask_image = get_prediction_image(predictions)
        img, mask_image = make_same_size(img, mask_image)
        no_bg_img, background_removed = get_no_bg_img(img, mask_image)
        if background_removed:
            new_path = os.path.join('data/dataset/bg_removed', modify_filename(image_file))
            no_bg_img.save(new_path, format="PNG")


build_bg_removed_dataset()
