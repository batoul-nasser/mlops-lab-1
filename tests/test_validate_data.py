import shutil

import pytest
from PIL import Image

from src.food11.data import CLASSES
from src.food11.validate_data import SPLITS, validate_dataset


@pytest.fixture
def dataset(tmp_path):
    for split_index, split in enumerate(SPLITS):
        for class_index, category in enumerate(CLASSES):
            folder = tmp_path / split / category
            folder.mkdir(parents=True)
            Image.new("RGB", (128, 128), (split_index * 70, class_index * 20, 0)).save(folder / "image.png")
    return tmp_path


def test_valid_contract(dataset):
    assert not any(validate_dataset(dataset, min_per_class=1).values())


def test_renamed_cross_split_duplicate(dataset):
    shutil.copyfile(dataset / "training/Bread/image.png", dataset / "evaluation/Bread/renamed.png")
    assert validate_dataset(dataset, 1)["split leakage"]


@pytest.mark.parametrize("problem", ["missing", "extra", "grayscale", "size", "corrupt", "minimum", "balance"])
def test_contract_failures(dataset, problem):
    path = dataset / "training/Bread/image.png"
    expected = "image format"
    if problem == "missing":
        path.unlink()
        path.parent.rmdir()
        expected = "class folders"
    elif problem == "extra":
        (dataset / "training/Unexpected").mkdir()
        expected = "class folders"
    elif problem == "grayscale":
        Image.new("L", (128, 128)).save(path)
    elif problem == "size":
        Image.new("RGB", (5, 6)).save(path)
    elif problem == "corrupt":
        path.write_bytes(b"not an image")
    elif problem == "minimum":
        path.unlink()
        expected = "minimum counts"
    else:
        for index in range(10):
            Image.new("RGB", (128, 128), (index, 5, 9)).save(path.parent / f"extra{index}.png")
        expected = "class balance"
    assert validate_dataset(dataset, 1)[expected]


def test_missing_dataset(tmp_path):
    errors = validate_dataset(tmp_path / "absent", 1)
    assert errors["class folders"]
    assert errors["minimum counts"]
    assert errors["class balance"]
