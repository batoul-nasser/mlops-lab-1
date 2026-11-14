import hashlib
import shutil
from pathlib import Path

from PIL import Image

RAW_DIR = Path("data/food11_raw")
PROCESSED_DIR = Path("data/food11_processed")
MINI_DIR = Path("data/food11_processed_mini")

IMAGE_SIZE = (128, 128)
MINI_LIMIT = 100

CLASSES = [
    "Bread",
    "Dairy product",
    "Dessert",
    "Egg",
    "Fried food",
    "Meat",
    "Noodles-Pasta",
    "Rice",
    "Seafood",
    "Soup",
    "Vegetable-Fruit",
]

CATEGORIES = {
    str(index): category
    for index, category in enumerate(CLASSES)
}


def category_from_filename(filename: str) -> str:
    category_id = filename.split("_")[0]
    return CATEGORIES[category_id]


def get_category(filename: str):
    category_id = filename.split("_")[0]
    return CATEGORIES.get(category_id)


def resize_image(img: Image.Image, size: int = 128) -> Image.Image:
    return img.convert("RGB").resize((size, size))


def prepare_directories():
    if PROCESSED_DIR.exists():
        shutil.rmtree(PROCESSED_DIR)

    if MINI_DIR.exists():
        shutil.rmtree(MINI_DIR)

    for split in ["training", "evaluation", "validation"]:
        for category in CLASSES:
            (PROCESSED_DIR / split / category).mkdir(
                parents=True,
                exist_ok=True,
            )
            (MINI_DIR / split / category).mkdir(
                parents=True,
                exist_ok=True,
            )


def process_dataset():
    mini_hash_splits = {}
    for split in ["training", "evaluation", "validation"]:
        input_folder = RAW_DIR / split

        mini_counts = {
            category: 0
            for category in CLASSES
        }

        print(f"Processing {split}...")

        for image_path in input_folder.iterdir():
            if not image_path.is_file():
                continue

            category = get_category(image_path.name)

            if category is None:
                continue

            try:
                with Image.open(image_path) as image:
                    image = resize_image(
                        image,
                        size=IMAGE_SIZE[0],
                    )

                    output_path = (
                        PROCESSED_DIR
                        / split
                        / category
                        / image_path.name
                    )

                    image.save(output_path)

                    if mini_counts[category] < MINI_LIMIT:
                        digest = hashlib.md5(output_path.read_bytes()).hexdigest()
                        if digest in mini_hash_splits and mini_hash_splits[digest] != split:
                            continue
                        mini_path = (
                            MINI_DIR
                            / split
                            / category
                            / image_path.name
                        )

                        image.save(mini_path)
                        mini_hash_splits[digest] = split
                        mini_counts[category] += 1

            except (OSError, ValueError, Image.DecompressionBombError) as e:
                print(
                    f"Error processing "
                    f"{image_path}: {e}"
                )


def main():
    if not RAW_DIR.exists():
        raise FileNotFoundError(
            f"Raw dataset not found at {RAW_DIR}"
        )

    prepare_directories()
    process_dataset()

    print("Done!")


if __name__ == "__main__":
    main()
