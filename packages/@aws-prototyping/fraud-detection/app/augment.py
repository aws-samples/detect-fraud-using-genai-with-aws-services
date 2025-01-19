import os
from pathlib import Path

import albumentations as A
import cv2
from PIL import Image

AUGMENTATIONS_PER_IMAGE = 10
IMAGE_EXTENSIONS = [".png", ".jpg", ".jpeg"]


def get_all_files_in_directory(root_dir):
    for dirpath, dirnames, filenames in os.walk(root_dir):
        for filename in filenames:
            yield os.path.join(dirpath, filename)


def perform_augmentations(path):
    # Declare an augmentation pipeline
    transform = A.Compose([
        A.RandomRotate90(),
        A.Flip(),
        A.Transpose(),
        A.GaussNoise(p=0.2),
        A.OneOf([
            A.MotionBlur(p=.2),
            A.MedianBlur(blur_limit=3, p=0.1),
            A.Blur(blur_limit=3, p=0.1),
        ], p=0.2),
        A.ShiftScaleRotate(shift_limit=0.0625, scale_limit=0.2, rotate_limit=45, p=0.2),
        A.OneOf([
            A.OpticalDistortion(p=0.3),
            A.GridDistortion(p=.1),
            A.PiecewiseAffine(p=0.3),
        ], p=0.2),
        A.OneOf([
            A.CLAHE(clip_limit=2),
            A.Sharpen(),
            A.Emboss(),
            A.RandomBrightnessContrast(),
        ], p=0.3),
        A.HueSaturationValue(p=0.3),
    ])

    for imagepath in get_all_files_in_directory(path):

        if not Path(imagepath).suffix in IMAGE_EXTENSIONS:
            continue

        print(f'Augmenting {imagepath}')
        source_image = cv2.imread(imagepath)

        for x in range(AUGMENTATIONS_PER_IMAGE):
            transformed = transform(image=source_image)
            transformed_image = transformed["image"]

            imgToSave = Image.fromarray(transformed_image)

            file_name_with_extension = os.path.basename(imagepath)
            file_name_without_extension = os.path.splitext(file_name_with_extension)[0]

            new_filename = f'{file_name_without_extension}_transformed_{x}.png'

            new_path = os.path.join('./data/augmented', new_filename)

            imgToSave.save(new_path)

            print(f'Augmented {new_path}')


if __name__ == "__main__":
    perform_augmentations('data/dataset')
