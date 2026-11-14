from PIL import Image

from src.food11.data import (
    CLASSES,
    category_from_filename,
    resize_image,
)


def test_category_from_filename():
    assert category_from_filename("0_12.jpg") == "Bread"
    assert category_from_filename("10_3.jpg") == "Vegetable-Fruit"
    assert category_from_filename("3_120.jpg") == "Egg"


def test_resize_image_shape_and_mode():
    img = Image.new("L", (512, 384))

    out = resize_image(img)

    assert out.size == (128, 128)
    assert out.mode == "RGB"


def test_eleven_classes():
    assert len(CLASSES) == 11


def test_preprocessing_keeps_full_data_and_prevents_mini_leakage(tmp_path, monkeypatch):
    from src.food11 import data

    monkeypatch.setattr(data, "RAW_DIR", tmp_path / "raw")
    monkeypatch.setattr(data, "PROCESSED_DIR", tmp_path / "processed")
    monkeypatch.setattr(data, "MINI_DIR", tmp_path / "mini")
    for split in ("training", "evaluation", "validation"):
        folder = data.RAW_DIR / split
        folder.mkdir(parents=True)
        Image.new("RGB", (30, 40), "red").save(folder / "0_1.jpg")
    Image.new("RGB", (30, 40), "blue").save(data.RAW_DIR / "evaluation/0_2.jpg")
    Image.new("RGB", (30, 40), "green").save(data.RAW_DIR / "validation/0_3.jpg")
    data.main()
    for split in ("training", "evaluation", "validation"):
        assert (data.PROCESSED_DIR / split / "Bread/0_1.jpg").is_file()
    assert (data.MINI_DIR / "training/Bread/0_1.jpg").is_file()
    assert not (data.MINI_DIR / "evaluation/Bread/0_1.jpg").exists()
    assert not (data.MINI_DIR / "validation/Bread/0_1.jpg").exists()
    assert (data.MINI_DIR / "evaluation/Bread/0_2.jpg").is_file()
    assert (data.MINI_DIR / "validation/Bread/0_3.jpg").is_file()
