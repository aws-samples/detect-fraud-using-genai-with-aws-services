import base64
import io
import os
import string
from itertools import combinations
from pathlib import Path

import PIL
import boto3
import numpy as np
import pandas as pd
import timm
import torch
import torch.nn.functional as F
from PIL import Image, ImageDraw, ImageFont
from annoy import AnnoyIndex
from loguru import logger
from scipy.spatial.distance import cosine
from sqlitedict import SqliteDict
from timm.data import resolve_data_config
from timm.data.transforms_factory import create_transform
from torchvision.datasets import ImageFolder
from torchvision.ops import box_iou
from tqdm.auto import tqdm
import cv2
import numpy as np

PWD = os.path.dirname(os.path.realpath(__file__))

def draw_bboxes(
        img: PIL.Image,
        bboxes: list[tuple],
        labels: list[str] = None,
        colour="magenta",
        width=2,
        font_size=14,
):
    """Draw the bounding boxes on an image.

    Parameters
    ----------
    img : PIL.Image
        The source image.
    bboxes : list[tuple]
        A list-like container of <xmin, ymin, xmax, ymax> tuples.
    labels : list[str], default=None
    colour : str, default="magenta"
    width : int, default=2
    font_size : int, default=14

    Returns
    -------
    PIL.Image

    """

    font = ImageFont.load_default()
    draw = ImageDraw.Draw(img)

    for i, (x0, y0, x1, y1) in enumerate(bboxes):
        xy = (x0, y0), (x1, y1)

        if labels is not None:
            if len(labels) == len(bboxes):
                draw.text(xy[0], labels[i], fill=colour,
                          font=font, anchor="ls")
            else:
                raise NotImplementedError

        draw.rectangle(xy, outline=colour, width=width)

    return img


def apply_bg_alpha_blend(img: PIL.Image, colour=(230, 230, 230)):
    """Convert RGBA png file to RGB and replace the background with a given
    RGB colour.

    Parameters
    ----------
    img : PIL.Image
    colour : tuple[int], default=(230, 230, 230)
        RGB values of the colour used to replace the background in the alpha
        channel.

    Returns
    -------
    PIL.Image

    """

    if img.mode == "RGBA":
        logger.warning("RGBA image detected...")
        bg_img = Image.new("RGBA", img.size, colour)
        img = Image.alpha_composite(bg_img, img).convert("RGB")
        img.format = "PNG"

    return img


def convert_bbox_coords(img_w: int, img_h: int, bbox_dict: dict):
    """Convert the Rekognition "BoundingBox" axis-aligned coarse bounding box
    representation to a conventional (xmin, ymin, xmax, ymax) co-ordinates

    Parameters
    ----------
    img_w : int
    img_h : int
    bbox_dict : dict

    Returns
    -------
    numpy.ndarray
        4-tuple of [xmin, ymin, xmax, ymax] values

    """

    xmin = img_w * bbox_dict["Left"]
    ymin = img_h * bbox_dict["Top"]
    xmax = xmin + img_w * bbox_dict["Width"]
    ymax = ymin + img_h * bbox_dict["Height"]

    bbox = np.array([xmin, ymin, xmax, ymax])

    return bbox


def get_bbox_coords(df: pd.DataFrame):
    """
    Returns a list of bounding box coordinates from the given DataFrame.

    Parameters:
    df (pd.DataFrame): The DataFrame containing bounding box coordinates.

    Returns:
    list: A list of tuples representing the bounding box coordinates in the format (x1, y1, x2, y2).
    """
    return [(r["bb.x1"], r["bb.y1"], r["bb.x2"], r["bb.y2"]) for _, r in df.iterrows()]


def img_to_bytes(img: PIL.Image, fmt: str = "PNG"):
    """Convert a PIL image to bytes, typically for sending to a Rekognition
    endpoint.

    Parameters
    ----------
    img : PIL.Image
    fmt : str

    Returns
    -------
    bytes

    """

    if img.format is not None:
        fmt = img.format

    if fmt not in ("PNG", "JPEG"):
        logger.warning(f"Unusual format detected: {fmt}")

    buf = io.BytesIO()
    img.convert("RGB").save(buf, format=fmt)

    return buf.getvalue()


def img_from_bytes(img_bytes: bytes):
    return Image.open(io.BytesIO(img_bytes))


def img_to_b64str(img: PIL.Image, fmt: str = "PNG"):
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    b64str = base64.b64encode(buf.getvalue()).decode()
    return b64str


def img_from_b64str(b64str: str):
    return Image.open(io.BytesIO(base64.decodebytes(bytes(b64str, "utf-8"))))


def is_bbox_overlap(bbox1: np.ndarray, bbox2: np.ndarray):
    """Determine if two bounding-box rectangles overlap.

    Parameters
    ----------
    bbox1 : np.ndarray
    bbox2 : np.ndarray

    Returns
    -------
    bool

    """

    xmin1, ymin1, xmax1, ymax1 = bbox1
    xmin2, ymin2, xmax2, ymax2 = bbox2

    is_overlap = xmax1 >= xmin2 and xmax2 >= xmin1 and ymax1 >= ymin2 and ymax2 >= ymin1

    return is_overlap


def make_data_url_from_path(path: string, fmt: str = None):
    """ """

    return make_data_url(path, fmt)


def make_data_url(img: PIL.Image, fmt: str = None):
    """ """

    if fmt is None:
        fmt = img.format

    buf = io.BytesIO()
    img.thumbnail((500, 500), PIL.Image.LANCZOS)
    img.save(buf, format=fmt)
    bytes_str = base64.b64encode(buf.getvalue()).decode()
    data_url = f"data:image/{fmt.lower()};base64,{bytes_str}"

    return data_url


def calc_iou(bbox1: np.ndarray, bbox2: np.ndarray):
    """
    Calculate the Intersection over Union (IoU) of two bounding boxes.

    Parameters:
    bbox1 (np.ndarray): The first bounding box, expected to be a numpy array.
    bbox2 (np.ndarray): The second bounding box, expected to be a numpy array.

    Returns:
    float: The IoU of the two bounding boxes as a float.
    """
    bbox1 = torch.from_numpy(np.array(bbox1)).unsqueeze(0)
    bbox2 = torch.from_numpy(np.array(bbox2)).unsqueeze(0)

    return float(box_iou(bbox1, bbox2).squeeze().numpy())


class ImageEncoder:
    """Use this class to encode images into image embeddings. For simplicity,
    this class will only use models available from huggingface.co.

    """

    def __init__(self, model_name: str = "vit_base_patch16_224_miil.in21k"):
        """Constructor.

        Parameters
        ----------
        model_name : str, default="vit_base_patch16_224_miil.in21k"

        """
        self._model = timm.create_model(
            model_name, pretrained=True, num_classes=0)
        self._model.eval()
        self._config = resolve_data_config({}, model=self._model)
        self._tfms = create_transform(**self._config)
        return

    def encode(self, img: PIL.Image):
        """

        Parameters
        ---------
        img :
            TODO: allow img to be a list[PIL.Image]

        Returns
        -------
        np.ndarray

        """

        with torch.no_grad():
            inputs = torch.stack([self._tfms(img)])
            features = self._model(inputs)
            X_emb = features.squeeze().cpu().numpy()

        return X_emb


class ImageLibrary:
    """This class represents the "library" of known images.

    """

    _valid_extensions = {".jpg", ".png", ".jpeg"}
    _pil_png_bg_rgb = (240, 240, 240)
    _ann_seed = 12345
    _ann_metric = "angular"
    _ann_n_trees = 100

    def __init__(
            self,
            root: str,
            db_fn: str,
            ann_fn: str,
            model_name: str = "vit_base_patch16_224_miil.in21k",
            ann_vec_size: int = None,
            load_existing=True
    ):
        """Constructor

        Parameters
        ----------
        root : str
        db_fn : str
        ann_fn : str
        model_name : str, default="vit_base_patch16_224_miil.in21k"
            Name of the (pretrained) model to use for generating the image
            embeddings, i.e. image encoding. A list of available pretrained
            model names are available by running `timm.list_pretrained(...)`.
        ann_vec_size : int, default=None
            This is the dimensionality of the image embedding vectors. This is
            optional, this will be attempted to be automatically set if `model_name`
            is in a pre-approved list (see the if-statement in the constructor source
            code).

        """

        if model_name == "vit_base_patch16_224_miil.in21k":
            ann_vec_size = 768
        else:
            if ann_vec_size is None:
                raise NotImplementedError(
                    f"Please specify `ann_vec_size` for model_name='{model_name}'"
                )

        self._root = Path(root).absolute().as_posix()
        self._db_fn = Path(db_fn).absolute().as_posix()
        self._ann_fn = Path(ann_fn).absolute().as_posix()
        self._ann_vec_size = ann_vec_size
        self._model_name = model_name
        self._model = ImageEncoder(model_name=self._model_name)
        self._dataset = ImageFolder(
            self._root, is_valid_file=self._is_valid_file)
        self._build_ann_index(load_existing)
        self._build_db(load_existing)

        return

    def _is_valid_file(self, fn: str):
        """

        Parameters
        ----------
        fn : str

        Returns
        -------
        Path

        """

        return Path(fn).suffix.lower() in self._valid_extensions

    def _iter_images(self):
        """Iterate through all the images in the dataset, pre-processing along
        the way. A (PIL.Image, str, int) object is yielded at each iteration.

        """

        for fn, label_idx in self._dataset.samples:
            fn = Path(fn).resolve()
            img = Image.open(fn)

            # when converting png files w/ alpha channel, set the background
            # to a very light grey (as opposed to the default transparency)
            if fn.suffix == ".png" and img.mode == "RGBA":
                img = apply_bg_alpha_blend(img, colour=self._pil_png_bg_rgb)
            elif img.mode == "RGB":
                pass
            else:
                img = img.convert("RGB")

            yield img, fn.as_posix(), label_idx

        return

    def _build_ann_index(self, load_existing=True):
        """Encode the images of the dataset into a disk-based vector db using
        the `annoy` library

        """

        self._ann_index = AnnoyIndex(self._ann_vec_size, self._ann_metric)

        if Path(self._ann_fn).exists():
            if load_existing:
                self._ann_index.load(self._ann_fn)
                return self._ann_index
            else:
                logger.warning(f"{self._ann_fn} exists, deleting...")
                os.remove(self._ann_fn)

        logger.info(f"Building {self._ann_fn}")

        model = self._model

        for i, (img, _, _) in tqdm(
                enumerate(self._iter_images()), total=len(self._dataset)
        ):
            # encode the image tensor to a 1D embedding vector
            x_emb = model.encode(img)

            # index the vector
            self._ann_index.add_item(i, x_emb)

        self._ann_index.build(self._ann_n_trees)
        self._ann_index.save(self._ann_fn)

        return self._ann_index

    def _build_db(self, load_existing=True):
        """Build the image database"""

        if Path(self._db_fn).exists():
            if load_existing:
                self._db = SqliteDict(self._db_fn)
                return self._db
            else:
                logger.warning(f"{self._db_fn} exists, deleting...")
                os.remove(self._db_fn)

        self._db = SqliteDict(self._db_fn)

        logger.info(f"Building {self._db_fn}")

        dataset = self._dataset

        for i, (img, fn, label_idx) in tqdm(
                enumerate(self._iter_images()), total=len(dataset)
        ):
            self._db[i] = {
                "x_emb": self._ann_index.get_item_vector(i),
                "label": dataset.classes[label_idx],
                "fn": Path(fn).resolve().as_posix(),
            }

        self._db.commit()

        return self._db

    def get_count(self):
        print(f'Images in dataset: {len(self._dataset)}')
        return len(self._dataset)

    def query(self, img: PIL.Image, thresh: float, labels: list[str] = None, n: int = 5, ):
        """Query the library for similar images.

        Parameters
        ----------
        img : PIL.Image
            The image to query.
        labels : list[str], default=None
            List of labels to include in the results. Images w/ labels not in this
            list will be excluded.
        n : int, default=5
            Find at most `n` candidate similar images.

        Returns
        -------
        pd.DataFrame

        """

        self._ann_index.set_seed(self._ann_seed)

        # convert the query img to an embedding vector
        q_emb = self._model.encode(img.convert("RGB"))
        indices, dist = self._ann_index.get_nns_by_vector(
            q_emb, n=n + 1, include_distances=True
        )

        rows = []

        for i, dist in zip(indices, dist):
            db_rec = self._db[i]

            # calc. cosine similarity between the query and result for scale
            # invariant image similarity
            csim = 1 - cosine(q_emb, db_rec["x_emb"])

            print(
                f'Filename {db_rec["fn"]}: distance {dist} cosine similarity {csim}')

            if thresh == 0 or csim >= thresh:
                rows.append(
                    {
                        "i": i,
                        "dist": dist,
                        "csim": csim,
                        "label": db_rec["label"],
                        "x_emb": db_rec["x_emb"],
                        "fn": db_rec["fn"]
                    }
                )

        df_results = pd.DataFrame(rows)

        if labels is not None and "label" in df_results.columns:
            df_results = df_results[df_results["label"].isin(labels)]

        return q_emb, df_results


class ImageChecker:
    def __init__(self, image_lib: ImageLibrary):
        self._image_lib = image_lib
        return

    def find_similar(self, img: PIL.Image, labels: list[str], thresh: float):
        """Query the image library for images that are similar to `img`.

        Parameters
        ----------
        img : PIL.Image
        labels : list[str]
        thresh : float

        Returns
        -------
        pd.DataFrame

        """
        
        print('Querying image library with threshold:', thresh, 'and labels:', labels,'image size:', img.size)
        
        x_emb, df_results = self._image_lib.query(img, thresh, labels, n=1000)
        
        print('Results from self._image_lib.query:', df_results)
        
        if "fn" in df_results.columns:
            images = df_results["fn"].apply(Image.open)
            df_results["image"] = images
            df_results["filename"] = [
                os.path.basename(fn) for fn in df_results["fn"]]

            df_results["data_url"] = [
                make_data_url(x) for x in images
            ]

        # df_results.drop(["fn"], axis=1, inplace=True)
        df_results["rank"] = list(range(1, df_results.shape[0] + 1))

        return df_results

    def detect_overlaps(self, bboxes: list[np.ndarray]):
        """Given a list of bbox coordinates, detect and report any overlaps
        between any two bboxes.

        Parameters
        ----------
        bboxes : list[np.ndarray]

        Returns
        -------
        list[tuple[int,int,float]]
            A list of (i, j, iou) tuples indicating the indices of the pairs of
            bboxes that overlap and their accompanying IOU scores.

        """

        overlaps = []

        for i, j in combinations(range(len(bboxes))):
            if is_bbox_overlap(bboxes[i], bboxes[j]):
                overlaps.append((i, j, 1.0))

        return overlaps

    def estimate_rotations(
            self,
            q_img: PIL.Image,
            r_img: PIL.Image,
            use_edges: bool = False,
            emb_method: str = None,
    ):
        """Estimate the rotation angle of a query image against a reference image.

        ? resize q_img to r_img size first

        1. q_emb <- generate embedding of `q_img`
        2. for each rotation of `r_img` -> `rot_img`:
            a. rot_emb <- generate embedding of `rot_img`
            a. d <- dist(q_emb, rot_emb)
        3. angle <- the rotation w/ the minimal distance

        Parameters
        ----------
        q_img : PIL.Image
            Query image.
        r_img : PIL.Image
        use_edges : bool, default=False
            Use edge-detection filters on both images prior to processing to
            minimise noise from differences in colour.
        emb_method : str, default=None

        Returns
        -------
        pd.DataFrame
            The cosine similarity scores of the estimated rotations.

        """

        if use_edges:
            raise NotImplementedError

        image_lib = self._image_lib

        rotated_images = [
            r_img.rotate(angle, expand=True, fillcolor="white").convert("RGB")
            for angle in range(360)
        ]

        q_emb = torch.from_numpy(image_lib._model.encode(q_img).reshape(1, -1))
        r_emb = []

        for img in tqdm(rotated_images):
            r_emb.append(image_lib._model.encode(img))

        r_emb = torch.from_numpy(np.stack(r_emb))

        sims = F.cosine_similarity(q_emb, r_emb).numpy()

        df_rotations = pd.DataFrame()
        df_rotations["score"] = sims

        return df_rotations


class RekognitionExtractor():
    def __init__(self, rek_proj_version_arn: str = None):
        """Constructor.

        Parameters
        ----------
        rek_proj_version_arn : str
            The Rekognition Project Version ARN.

        """

        self._client = boto3.client(
            "rekognition", region_name='ap-southeast-2')
        self._rek_proj_version_arn = rek_proj_version_arn

        return

    def extract_cmod(self, img: PIL.Image, min_conf: int = 25):
        """Run content moderation checks on the image.

        Parameters
        ----------
        img : PIL.Image
        min_conf : int, default=25
            Specifies the minimum confidence level for the labels to return.
            Amazon Rekognition doesn't return any labels with a confidence level
            lower than this specified value.

        Returns
        -------
        pd.DataFrame or None
            Returns `None` if there are no content moderation labels detected.

        """

        response = self._client.detect_moderation_labels(
            Image={"Bytes": img_to_bytes(img.convert("RGB"))}, MinConfidence=min_conf
        )

        if "ModerationLabels" not in response:
            return None

        if len(response["ModerationLabels"]) == 0:
            return None

        df_cmod = pd.json_normalize(response["ModerationLabels"])
        df_cmod["ParentName"] = df_cmod["ParentName"].apply(
            lambda x: None if x.strip() == "" else x
        )
        df_cmod.rename(
            {"Name": "label", "Confidence": "conf", "ParentName": "parent_label"},
            axis=1,
            inplace=True,
        )

        df_cmod.insert(0, "id", [f"cmod-{i:02d}" for i in range(len(df_cmod))])

        return df_cmod

    def extract_ppl(self, img: PIL.Image):
        """

        Returns
        -------
        pd.DataFrame or None
            Returns `None` if no people were detected.

        """

        response = self._client.detect_faces(
            Image={"Bytes": img_to_bytes(img.convert("RGB"))}, Attributes=["ALL"]
        )

        if "FaceDetails" not in response:
            raise NotImplementedError

        if len(response["FaceDetails"]) == 0:
            return None

        bboxes = []

        for r in response["FaceDetails"]:
            bbox_dict = r["BoundingBox"]
            bboxes.append(convert_bbox_coords(*img.size, bbox_dict))

        df_ppl = pd.json_normalize(response["FaceDetails"])

        rename_cols = {
            "Confidence": "conf",
            "BoundingBox.Width": "bb.width.frac",
            "BoundingBox.Height": "bb.height.frac",
            "BoundingBox.Left": "bb.left.frac",
            "BoundingBox.Top": "bb.top.frac",
            "Gender.Value": "gender.value",
            "Gender.Confidence": "gender.conf",
            "AgeRange.Low": "age.low",
            "AgeRange.High": "age.high",
        }

        # rename and keep certain columns
        df_ppl = df_ppl.rename(rename_cols, axis=1)[list(rename_cols.values())]
        df_ppl.sort_values(by="conf", ascending=False, inplace=True)
        df_ppl.insert(0, "id", [f"ppl-{i:02d}" for i in range(len(df_ppl))])
        df_ppl.insert(3, "bbox", bboxes)

        # create bbox <x1, x2, y1, y2> columns
        df_ppl[["bb.x1", "bb.y1", "bb.x2", "bb.y2"]
               ] = df_ppl["bbox"].apply(pd.Series)

        df_ppl.drop(["bbox"], axis=1, inplace=True)

        return df_ppl
