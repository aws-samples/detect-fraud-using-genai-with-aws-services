import imghdr
import os
import random
from pathlib import Path

import PIL

from exifdata import get_exif, get_exif_location
from generated_image_detector import detect_generated_image
from image_search import ImageLibrary, ImageChecker
from paths import get_paths
from websearch import reverse_image_search

TESTDATA_FOLDER, IMAGES_FOLDER, DATA_PATH = get_paths()

IMAGE_LIBRARY = ImageLibrary(IMAGES_FOLDER, 'images.db', 'images.ann', load_existing=True)


def detect_duplicates():
    imageChecker = ImageChecker(IMAGE_LIBRARY)
    img_path = Path.joinpath(DATA_PATH, "Duplicates", "DUPLICATES")
    print(f'Scanning duplicates directory {img_path}')
    file_count = 0
    duplicate_count = 0

    for filename in os.listdir(img_path):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
            file_count += 1
            # Construct the full file path
            image_path = os.path.join(img_path, filename)
            img = PIL.Image.open(image_path)
            result = imageChecker.find_similar(img, ["existing", "external"], 0.8)

            if result.size > 0:
                duplicate_count += 1

    print(
        f'{file_count} files scanned, {duplicate_count} duplicates found. {duplicate_count / file_count * 100}% duplicates found.')


def get_img_count(directory):
    count = 0
    # Walk through all directories and files in the given directory
    for root, dirs, files in os.walk(directory):
        for file in files:
            # Construct the full path to the file
            path = os.path.join(root, file)
            # Check if the file is an image
            if imghdr.what(path) is not None:
                count += 1
    return count


def get_generated_image_metrics():
    image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.bmp')

    img_path = Path.joinpath(TESTDATA_FOLDER, "generated")

    files = os.listdir(img_path)
    images = [file for file in files if file.lower().endswith(image_extensions)]

    count = 0
    true_positives = 0

    for filename in images:
        print(f'Checking {filename}')

        count += 1
        image_path = os.path.join(img_path, filename)
        img = PIL.Image.open(image_path)
        resp = detect_generated_image(img)
        print(resp)
        if resp["confidence"] > 0.8 and resp["prediction"] == 'FAKE':
            true_positives += 1

    print(f'Successfully classified {true_positives} out of {count} as AI generated. ({true_positives / count * 100}%)')

    img_path = Path.joinpath(TESTDATA_FOLDER, "IAG", "DUPLICATES")

    files = os.listdir(img_path)
    images = [file for file in files if file.lower().endswith(image_extensions)]

    count = 0
    true_negatives = 0

    for filename in images:
        print(f'Checking {filename}')

        count += 1
        image_path = os.path.join(img_path, filename)
        img = PIL.Image.open(image_path)
        resp = detect_generated_image(img)
        print(resp)
        if resp["confidence"] > 0.8 and resp["prediction"] == 'REAL':
            true_negatives += 1

    print(
        f'Successfully classified {true_negatives} out of {count} as not AI generated. {true_negatives / count * 100}%')


def get_reverse_image_search_metrics():
    image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.bmp')

    on_web_count = 0
    count = 0
    img_path = Path.joinpath(DATA_PATH, "Web", "on_web")
    files = os.listdir(img_path)
    images = [file for file in files if file.lower().endswith(image_extensions)]
    images = random.sample(images, 10)

    for filename in images:
        print(f'Checking {filename}')
        try:
            if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
                count += 1
                image_path = os.path.join(img_path, filename)
                img = PIL.Image.open(image_path)
                reverse_search_result = reverse_image_search(img, filename, 0)

                reverse_match_count = (reverse_search_result["csim"] > 0.85).sum()

                if reverse_match_count > 0:
                    on_web_count += 1
        except:
            print(f"An error occurred")

    print(f'On web count: {count}, actual on web: {on_web_count}, {on_web_count / count * 100}%')


def get_exif_count():
    img_path = Path.joinpath(DATA_PATH, "EXIF")
    count = 0
    exif_count = 0

    print(f'Scanning exif directory {img_path}')

    for filename in os.listdir(img_path):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
            count += 1
            # Construct the full path to the file
            image_path = os.path.join(img_path, filename)
            img = PIL.Image.open(image_path)
            exif_data = get_exif(img)
            if exif_data:
                exif_count += 1

    print(f'Expected EXIF file count: {count}, EXIF files with data count {exif_count}, {exif_count / count * 100}%')

    img_path = Path.joinpath(DATA_PATH, "EXIF", "GEO")
    count = 0
    exif_count = 0

    print(f'Scanning exif GEO directory {img_path}')

    for filename in os.listdir(img_path):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
            count += 1
            # Construct the full path to the file
            image_path = os.path.join(img_path, filename)
            img = PIL.Image.open(image_path)
            exif_data = get_exif(img)
            if exif_data:
                exif_geo_data = get_exif_location(exif_data)
                if exif_geo_data:
                    exif_count += 1

    print(
        f'Expected EXIF Geo file count: {count}, EXIF Geo files with data count {exif_count}, {exif_count / count * 100}%')


def detect_non_duplicates():
    imageChecker = ImageChecker(LOGO_LIBRARY)
    img_path = Path.joinpath(DATA_PATH, "Duplicates", "EXISTING CATALOGUE")
    print(f'Scanning non-duplicates directory {img_path}')
    file_count = 0
    duplicate_count = 0

    for filename in os.listdir(img_path):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
            file_count += 1
            # Construct the full file path
            image_path = os.path.join(img_path, filename)
            img = PIL.Image.open(image_path)
            result = imageChecker.find_similar(img, ["existing", "external"], 0.8)

            if result.size > 0:
                duplicate_count += 1

    print(
        f'{file_count} non-duplicate files scanned, {duplicate_count} duplicates found. {duplicate_count / file_count * 100}% duplicates found.')


def execute_metrics():
    # detect_duplicates()
    # detect_non_duplicates()
    # get_exif_count()
    # get_generated_image_metrics()
    get_reverse_image_search_metrics()


execute_metrics()
