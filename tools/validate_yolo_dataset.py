#!/usr/bin/env python3
"""Validate Ultralytics YOLO dataset integrity for RDD-2022 prepared output."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}
SPLITS = ("train", "val", "test")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate YOLO dataset")
    parser.add_argument("--data", default="datasets/rdd2022_yolo", help="Dataset root path")
    return parser.parse_args()


def iter_images(split_dir: Path):
    for p in split_dir.rglob("*"):
        if p.is_file() and p.suffix.lower() in IMAGE_EXTS:
            yield p


def validate_label_file(label_path: Path, errors: list[str]) -> int:
    lines = label_path.read_text(encoding="utf-8").splitlines()
    obj_count = 0
    for idx, raw in enumerate(lines, start=1):
        line = raw.strip()
        if not line:
            continue

        parts = line.split()
        if len(parts) != 5:
            errors.append(f"{label_path}: line {idx} must have 5 values, got {len(parts)}")
            continue

        class_raw, x_raw, y_raw, w_raw, h_raw = parts

        try:
            class_id = int(class_raw)
        except ValueError:
            errors.append(f"{label_path}: line {idx} invalid class_id '{class_raw}'")
            continue

        if class_id < 0 or class_id > 3:
            errors.append(f"{label_path}: line {idx} class_id out of range [0..3]: {class_id}")

        try:
            vals = [float(x_raw), float(y_raw), float(w_raw), float(h_raw)]
        except ValueError:
            errors.append(f"{label_path}: line {idx} has non-float coordinate values")
            continue

        names = ["x_center", "y_center", "width", "height"]
        for name, value in zip(names, vals):
            if not (0.0 <= value <= 1.0):
                errors.append(f"{label_path}: line {idx} {name} out of range [0,1]: {value}")

        obj_count += 1
    return obj_count


def main() -> int:
    args = parse_args()
    root = Path(args.data).expanduser().resolve()

    images_root = root / "images"
    labels_root = root / "labels"

    if not root.exists():
        print(f"ERROR: dataset path does not exist: {root}")
        return 2

    if not images_root.exists() or not labels_root.exists():
        print(f"ERROR: expected directories missing under {root}: images/ and labels/")
        return 2

    errors: list[str] = []
    total_images = 0
    total_labels = 0
    total_objects = 0

    split_summaries: list[str] = []

    for split in SPLITS:
        split_images_dir = images_root / split
        split_labels_dir = labels_root / split

        if not split_images_dir.exists():
            split_summaries.append(f"{split}: 0 images (missing dir)")
            continue

        images = sorted(iter_images(split_images_dir))
        split_objects = 0

        for image in images:
            total_images += 1
            rel = image.relative_to(split_images_dir)
            label_path = split_labels_dir / rel.with_suffix(".txt")

            if not label_path.exists():
                errors.append(f"Missing label for image: {image} -> expected {label_path}")
                continue

            total_labels += 1
            count = validate_label_file(label_path, errors)
            split_objects += count
            total_objects += count

        split_summaries.append(f"{split}: {len(images)} images, {split_objects} objects")

    print("YOLO dataset validation summary")
    print(f"- root: {root}")
    print(f"- total images: {total_images}")
    print(f"- total label files present: {total_labels}")
    print(f"- total objects: {total_objects}")
    for line in split_summaries:
        print(f"- {line}")

    if errors:
        print("\nValidation errors:")
        for msg in errors[:100]:
            print(f"  - {msg}")
        if len(errors) > 100:
            print(f"  - ... and {len(errors) - 100} more")
        return 1

    print("\nValidation OK: no errors found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
