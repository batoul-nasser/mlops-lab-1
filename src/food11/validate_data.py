"""Validate the processed Food-11 contract without downloading DVC data."""

import argparse
import hashlib
import math
from pathlib import Path

from PIL import Image

if __package__:
    from .data import CLASSES
else:
    from data import CLASSES

SPLITS = ("training", "validation", "evaluation")


def validate_dataset(root: Path, min_per_class: int = 50, tau: float = 0.05):
    """Return errors grouped by contract category; inspect every class file."""
    errors = {name: [] for name in (
        "class folders", "image format", "minimum counts", "split leakage", "class balance"
    )}
    counts = {split: dict.fromkeys(CLASSES, 0) for split in SPLITS}
    seen = {}
    for split in SPLITS:
        split_dir = root / split
        actual = {p.name for p in split_dir.iterdir() if p.is_dir()} if split_dir.is_dir() else set()
        if actual != set(CLASSES):
            errors["class folders"].append(
                f"{split}: missing={sorted(set(CLASSES) - actual)}, extra={sorted(actual - set(CLASSES))}"
            )
        # Inspect extra folders too: an unexpected folder cannot hide a bad image.
        for category in sorted(actual | set(CLASSES)):
            folder = split_dir / category
            files = sorted(p for p in folder.rglob("*") if p.is_file()) if folder.is_dir() else []
            if category in CLASSES:
                counts[split][category] = len(files)
                if len(files) < min_per_class:
                    errors["minimum counts"].append(f"{split}/{category}: {len(files)} < {min_per_class}")
            for path in files:
                try:
                    digest = hashlib.md5(path.read_bytes()).hexdigest()
                    previous = seen.get(digest)
                    if previous is not None and previous[0] != split:
                        errors["split leakage"].append(f"{previous[1]} == {path}")
                    else:
                        seen[digest] = (split, path)
                    with Image.open(path) as img:
                        img.load()
                        if img.mode != "RGB" or img.size != (128, 128):
                            errors["image format"].append(f"{path}: {img.mode}, {img.size}")
                except (OSError, ValueError, Image.DecompressionBombError) as exc:
                    errors["image format"].append(f"{path}: {exc}")
    train_total = sum(counts["training"].values())
    val_total = sum(counts["validation"].values())
    if not train_total or not val_total:
        errors["class balance"].append("training and validation must be nonempty")
    else:
        for category in CLASSES:
            difference = abs(counts["training"][category] / train_total - counts["validation"][category] / val_total)
            if difference > tau:
                errors["class balance"].append(f"{category}: difference={difference:.6f} > {tau}")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--min-per-class", type=int, default=50)
    parser.add_argument("--tau", type=float, default=0.05)
    args = parser.parse_args()
    if args.min_per_class < 1 or not math.isfinite(args.tau) or not 0 <= args.tau <= 1:
        parser.error("--min-per-class must be positive and --tau must be finite in [0, 1]")
    try:
        errors = validate_dataset(args.dataset, args.min_per_class, args.tau)
    except OSError as exc:
        parser.exit(1, f"FAIL dataset access: {exc}\n")
    for category, failures in errors.items():
        detail = f" ({len(failures)} errors; first: {failures[0]})" if failures else ""
        print(f"{'FAIL' if failures else 'PASS'} {category}{detail}")
    return int(any(errors.values()))


if __name__ == "__main__":
    raise SystemExit(main())
