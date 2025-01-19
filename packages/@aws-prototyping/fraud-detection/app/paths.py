import os
import shutil
from pathlib import Path


def is_running_on_ecs():
    return 'AWS_EXECUTION_ENV' in os.environ and 'FARGATE' in os.environ['AWS_EXECUTION_ENV']


def is_running_on_lambda():
    return 'AWS_LAMBDA_FUNCTION_NAME' in os.environ


def get_paths():
    if is_running_on_ecs():
        TESTDATA_FOLDER = Path("/app/data").resolve()

        if not TESTDATA_FOLDER.exists():
            os.makedirs(TESTDATA_FOLDER)

        IMAGES_FOLDER = Path("/mnt/efs/data/dataset").resolve()
        if not IMAGES_FOLDER.exists():
            os.makedirs(IMAGES_FOLDER)
            # Copy files across
            LOCAL_DATA_FOLDER = Path("/app/data/dataset").resolve()
            shutil.copytree(LOCAL_DATA_FOLDER, IMAGES_FOLDER,
                            dirs_exist_ok=True)
            print(
                f'Copied image files from {LOCAL_DATA_FOLDER} to {IMAGES_FOLDER}')

        DATA_PATH = Path("/app/originaldata").resolve()

        if not DATA_PATH.exists():
            os.makedirs(DATA_PATH)
    
    elif is_running_on_lambda():
        TESTDATA_FOLDER = Path("/tmp/app/data").resolve()

        if not TESTDATA_FOLDER.exists():
            os.makedirs(TESTDATA_FOLDER)

        IMAGES_FOLDER = Path("/tmp/data/dataset").resolve()
        if not IMAGES_FOLDER.exists():
            os.makedirs(IMAGES_FOLDER)
            # Copy files across
            LOCAL_DATA_FOLDER = Path("/tmp/data/dataset").resolve()
            shutil.copytree(LOCAL_DATA_FOLDER, IMAGES_FOLDER,
                            dirs_exist_ok=True)
            print(
                f'Copied image files from {LOCAL_DATA_FOLDER} to {IMAGES_FOLDER}')

        DATA_PATH = Path("/tmp/originaldata").resolve()

        if not DATA_PATH.exists():
            os.makedirs(DATA_PATH)
    else:
        IMAGE_PATH = Path(__file__).parent.resolve()

        TESTDATA_FOLDER = IMAGE_PATH.parent.joinpath(
            "app", "testdata").resolve()

        if not TESTDATA_FOLDER.exists():
            os.makedirs(TESTDATA_FOLDER)

        IMAGES_FOLDER = IMAGE_PATH.parent.joinpath(
            "app", "data", "dataset").resolve()
        if not IMAGES_FOLDER.exists():
            os.makedirs(IMAGES_FOLDER)

        DATA_PATH = IMAGE_PATH.parent.joinpath("app", "originaldata").resolve()

        if not DATA_PATH.exists():
            os.makedirs(DATA_PATH)

    print(f'Test data folder: {TESTDATA_FOLDER}')
    print(f'Images folder: {IMAGES_FOLDER}')
    print(f'Data folder: {DATA_PATH}')

    return TESTDATA_FOLDER, IMAGES_FOLDER, DATA_PATH
