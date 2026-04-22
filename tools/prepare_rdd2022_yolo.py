#!/usr/bin/env python3
"""Prepare Kaggle RDD-2022 dataset for Ultralytics YOLO training.

Supported annotation formats:
- COCO JSON (instances*.json)
- Pascal VOC XML

Output structure:
{out}/
  images/train|val|test
  labels/train|val|test
  data.yaml
  prepare_report.json
"""

from __future__ import annotations

import argparse
import json
import random
import shutil
import time
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

try:
    from PIL import Image
except Exception as exc:  # pragma: no cover
    raise RuntimeError("Pillow is required. Install with: pip install pillow") from exc


IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}
CLASS_MAP = {
    "D00": 0,  # longitudinal_crack
    "D10": 1,  # transverse_crack
    "D20": 2,  # alligator_crack
    "D40": 3,  # pothole
}
# Optional remap for pre-labeled YOLO datasets when class ids are not already 0..3.
# Keep empty when source labels already use 0..3.
# Example alternative mapping:
# YOLO_CLASS_REMAP = {1: 0, 2: 1, 3: 2, 4: 3}
YOLO_CLASS_REMAP: dict[int, int] = {}

CLASS_NAMES = {
    0: "longitudinal_crack",
    1: "transverse_crack",
    2: "alligator_crack",
    3: "pothole",
}
SPLITS = ("train", "val", "test")


@dataclass
class Sample:
    image_path: Path
    split_hint: str | None = None
    width: int | None = None
    height: int | None = None
    boxes: list[tuple[int, float, float, float, float]] = field(default_factory=list)


class PrepareError(RuntimeError):
    """Clear user-facing preparation error."""


def copy_with_retry(src: Path, dst: Path, retries: int = 8, base_delay: float = 0.2) -> None:
    """Copy file with retry to tolerate transient Windows file locks (WinError 32)."""
    dst.parent.mkdir(parents=True, exist_ok=True)

    # Skip copy when destination is already the same file.
    if dst.exists():
        try:
            if src.resolve() == dst.resolve():
                return
        except Exception:
            pass

    last_exc: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            shutil.copy2(src, dst)
            return
        except PermissionError as exc:
            last_exc = exc
            if attempt >= retries:
                break
            time.sleep(base_delay * attempt)
        except OSError as exc:
            # Some Windows lock errors bubble up as generic OSError with winerror 32.
            if getattr(exc, "winerror", None) == 32:
                last_exc = exc
                if attempt >= retries:
                    break
                time.sleep(base_delay * attempt)
                continue
            raise

    raise PrepareError(
        f"Failed to copy file after {retries} attempts due to file lock: {src} -> {dst}. "
        f"Close viewers/sync tools/antivirus scanning this file and retry. Last error: {last_exc}"
    )


def str2bool(value: str) -> bool:
    lowered = value.strip().lower()
    if lowered in {"1", "true", "t", "yes", "y", "on"}:
        return True
    if lowered in {"0", "false", "f", "no", "n", "off"}:
        return False
    raise argparse.ArgumentTypeError(f"Invalid boolean value: {value}")


def parse_args() -> argparse.Namespace:
    root_default = Path(__file__).resolve().parents[1] / "datasets" / "rdd2022_yolo"
    parser = argparse.ArgumentParser(description="Prepare RDD-2022 for Ultralytics YOLO")
    parser.add_argument("--src", required=True, help="Path to Kaggle rdd-2022 dataset")
    parser.add_argument("--out", default=str(root_default), help="Output path (default: datasets/rdd2022_yolo)")
    parser.add_argument("--split", type=str2bool, default=True, help="Enable split generation (default: true)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed (default: 42)")
    parser.add_argument("--val-ratio", type=float, default=0.1, help="Validation ratio (default: 0.1)")
    parser.add_argument("--test-ratio", type=float, default=0.1, help="Test ratio (default: 0.1)")
    return parser.parse_args()


def iter_images(root: Path) -> Iterable[Path]:
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in IMAGE_EXTS:
            yield p


def infer_split(path_like: str) -> str | None:
    parts = [part.lower() for part in Path(path_like).parts]
    if "train" in parts:
        return "train"
    if "val" in parts or "valid" in parts or "validation" in parts:
        return "val"
    if "test" in parts:
        return "test"
    return None


def normalize_bbox_xywh(x: float, y: float, w: float, h: float, img_w: int, img_h: int) -> tuple[float, float, float, float] | None:
    if img_w <= 0 or img_h <= 0:
        return None
    x1 = max(0.0, min(float(img_w), x))
    y1 = max(0.0, min(float(img_h), y))
    x2 = max(0.0, min(float(img_w), x + w))
    y2 = max(0.0, min(float(img_h), y + h))
    bw = x2 - x1
    bh = y2 - y1
    if bw <= 0 or bh <= 0:
        return None
    xc = (x1 + x2) / 2.0 / img_w
    yc = (y1 + y2) / 2.0 / img_h
    wn = bw / img_w
    hn = bh / img_h
    return (xc, yc, wn, hn)


def normalize_bbox_xyxy(xmin: float, ymin: float, xmax: float, ymax: float, img_w: int, img_h: int) -> tuple[float, float, float, float] | None:
    if img_w <= 0 or img_h <= 0:
        return None
    x1 = max(0.0, min(float(img_w), xmin))
    y1 = max(0.0, min(float(img_h), ymin))
    x2 = max(0.0, min(float(img_w), xmax))
    y2 = max(0.0, min(float(img_h), ymax))
    bw = x2 - x1
    bh = y2 - y1
    if bw <= 0 or bh <= 0:
        return None
    xc = (x1 + x2) / 2.0 / img_w
    yc = (y1 + y2) / 2.0 / img_h
    wn = bw / img_w
    hn = bh / img_h
    return (xc, yc, wn, hn)


def find_image_for_reference(src_root: Path, reference: str, basename_index: dict[str, list[Path]], context_dir: Path | None = None) -> Path | None:
    ref = Path(reference)

    candidates: list[Path] = []
    candidates.append(src_root / reference)
    if context_dir is not None:
        candidates.append(context_dir / reference)
    if ref.name != reference:
        candidates.append(src_root / ref.name)
        if context_dir is not None:
            candidates.append(context_dir / ref.name)

    for candidate in candidates:
        if candidate.exists() and candidate.is_file() and candidate.suffix.lower() in IMAGE_EXTS:
            return candidate.resolve()

    matches = basename_index.get(ref.name.lower(), [])
    if len(matches) == 1:
        return matches[0]
    return None


def build_basename_index(images: list[Path]) -> dict[str, list[Path]]:
    idx: dict[str, list[Path]] = defaultdict(list)
    for img in images:
        idx[img.name.lower()].append(img.resolve())
    return idx


def read_image_size(path: Path) -> tuple[int, int]:
    with Image.open(path) as im:
        return im.size


def detect_annotation_format(src: Path) -> tuple[str, list[Path]]:
    # 1) RDD_SPLIT YOLO format (preferred when present)
    yolo_layouts = [
        src / "RDD_SPLIT",
        src,
    ]
    for base in yolo_layouts:
        train_images = base / "train" / "images"
        train_labels = base / "train" / "labels"
        if train_images.exists() and train_labels.exists() and any(train_labels.rglob("*.txt")):
            return "yolo_split", [base]

    # 2) COCO format
    coco_files = sorted(src.rglob("instances*.json"))
    if coco_files:
        return "coco", coco_files

    # 3) VOC format
    voc_files = sorted(src.rglob("*.xml"))
    if voc_files:
        return "voc", voc_files

    json_files = sorted(src.rglob("*.json"))
    xml_files = sorted(src.rglob("*.xml"))
    visible = [str(p.relative_to(src)) for p in (json_files[:10] + xml_files[:10])]
    raise PrepareError(
        "Unsupported or unknown annotation format. "
        "Expected RDD_SPLIT YOLO, COCO (instances*.json) or Pascal VOC XML. "
        f"Detected candidate files: {visible if visible else 'none'}"
    )


def _parse_yolo_label_line(raw: str) -> tuple[int, float, float, float, float] | None:
    line = raw.strip()
    if not line:
        return None
    parts = line.split()
    if len(parts) != 5:
        return None
    try:
        cls = int(parts[0])
        xc = float(parts[1])
        yc = float(parts[2])
        w = float(parts[3])
        h = float(parts[4])
    except ValueError:
        return None
    return cls, xc, yc, w, h


def _resolve_yolo_class_mapping(present_class_ids: set[int]) -> dict[int, int]:
    # Always keep canonical ids if they already exist in source labels.
    mapping: dict[int, int] = {i: i for i in (0, 1, 2, 3) if i in present_class_ids}

    if present_class_ids.issubset({0, 1, 2, 3}):
        return mapping

    if not YOLO_CLASS_REMAP:
        return mapping

    valid_targets = {0, 1, 2, 3}
    mapped_targets = set(YOLO_CLASS_REMAP.values())
    if not mapped_targets.issubset(valid_targets):
        raise PrepareError(
            f"Invalid YOLO_CLASS_REMAP targets {sorted(mapped_targets)}. Allowed targets: [0,1,2,3]."
        )

    mapping.update(dict(YOLO_CLASS_REMAP))
    return mapping


def parse_yolo_split(src: Path, base_dir: Path) -> tuple[dict[Path, Sample], dict[str, object]]:
    """Load pre-labeled YOLO dataset from RDD_SPLIT style directories."""
    samples: dict[Path, Sample] = {}
    present_class_ids: set[int] = set()

    for split_name in ("train", "test"):
        images_dir = base_dir / split_name / "images"
        labels_dir = base_dir / split_name / "labels"
        if not images_dir.exists():
            continue

        for img_path in sorted(iter_images(images_dir)):
            image_path = img_path.resolve()
            sample = samples.setdefault(
                image_path,
                Sample(image_path=image_path, split_hint=split_name),
            )
            if sample.width is None or sample.height is None:
                sample.width, sample.height = read_image_size(image_path)

            label_path = labels_dir / f"{img_path.stem}.txt"
            if not label_path.exists():
                continue

            for raw in label_path.read_text(encoding="utf-8").splitlines():
                parsed = _parse_yolo_label_line(raw)
                if parsed is None:
                    continue
                cls, xc, yc, w, h = parsed
                present_class_ids.add(cls)
                sample.boxes.append((cls, xc, yc, w, h))

    class_mapping = _resolve_yolo_class_mapping(present_class_ids)

    # Always keep final dataset in 4-class target space and ignore unknown classes.
    for sample in samples.values():
        remapped: list[tuple[int, float, float, float, float]] = []
        for cls, xc, yc, w, h in sample.boxes:
            if cls in class_mapping:
                dst_cls = class_mapping[cls]
                remapped.append((dst_cls, xc, yc, w, h))
        sample.boxes = remapped

    report_info = {
        "yolo_source_base": str(base_dir),
        "yolo_present_class_ids": sorted(present_class_ids),
        "yolo_class_mapping_used": {str(k): v for k, v in class_mapping.items()},
    }
    return samples, report_info


def parse_coco(src: Path, anno_files: list[Path], images: list[Path]) -> dict[Path, Sample]:
    basename_index = build_basename_index(images)
    samples: dict[Path, Sample] = {
        p.resolve(): Sample(image_path=p.resolve(), split_hint=infer_split(str(p.relative_to(src))))
        for p in images
    }

    for anno_path in anno_files:
        payload = json.loads(anno_path.read_text(encoding="utf-8"))
        categories = {int(c["id"]): str(c.get("name", "")) for c in payload.get("categories", [])}
        images_map = {int(img["id"]): img for img in payload.get("images", [])}
        by_image: dict[int, list[dict]] = defaultdict(list)
        for ann in payload.get("annotations", []):
            image_id = ann.get("image_id")
            if image_id is None:
                continue
            by_image[int(image_id)].append(ann)

        for image_id, img_info in images_map.items():
            file_name = str(img_info.get("file_name", "")).strip()
            if not file_name:
                continue
            image_path = find_image_for_reference(src, file_name, basename_index, anno_path.parent)
            if image_path is None:
                continue

            sample = samples.setdefault(image_path, Sample(image_path=image_path))
            sample.split_hint = sample.split_hint or infer_split(file_name) or infer_split(str(anno_path.relative_to(src)))
            if sample.width is None or sample.height is None:
                iw = int(img_info.get("width") or 0)
                ih = int(img_info.get("height") or 0)
                if iw > 0 and ih > 0:
                    sample.width, sample.height = iw, ih

            anns = by_image.get(image_id, [])
            if sample.width is None or sample.height is None:
                sample.width, sample.height = read_image_size(image_path)

            for ann in anns:
                cat_id = ann.get("category_id")
                if cat_id is None:
                    continue
                cat_name = categories.get(int(cat_id), "")
                if cat_name not in CLASS_MAP:
                    continue
                bbox = ann.get("bbox")
                if not isinstance(bbox, list) or len(bbox) < 4:
                    continue
                normalized = normalize_bbox_xywh(
                    float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3]), sample.width, sample.height
                )
                if normalized is None:
                    continue
                sample.boxes.append((CLASS_MAP[cat_name],) + normalized)

    return samples


def _xml_text(root: ET.Element, path: str, default: str = "") -> str:
    found = root.find(path)
    if found is None or found.text is None:
        return default
    return found.text.strip()


def parse_voc(src: Path, anno_files: list[Path], images: list[Path]) -> dict[Path, Sample]:
    basename_index = build_basename_index(images)
    samples: dict[Path, Sample] = {
        p.resolve(): Sample(image_path=p.resolve(), split_hint=infer_split(str(p.relative_to(src))))
        for p in images
    }

    for xml_path in anno_files:
        tree = ET.parse(xml_path)
        root = tree.getroot()

        filename = _xml_text(root, "filename")
        xml_img_path = _xml_text(root, "path")

        ref = xml_img_path or filename
        if not ref:
            continue

        image_path = find_image_for_reference(src, ref, basename_index, xml_path.parent)
        if image_path is None:
            continue

        sample = samples.setdefault(image_path, Sample(image_path=image_path))
        sample.split_hint = sample.split_hint or infer_split(ref) or infer_split(str(xml_path.relative_to(src)))

        if sample.width is None or sample.height is None:
            iw = int(_xml_text(root, "size/width", "0") or "0")
            ih = int(_xml_text(root, "size/height", "0") or "0")
            if iw > 0 and ih > 0:
                sample.width, sample.height = iw, ih
            else:
                sample.width, sample.height = read_image_size(image_path)

        for obj in root.findall("object"):
            class_name = _xml_text(obj, "name")
            if class_name not in CLASS_MAP:
                continue

            xmin = float(_xml_text(obj, "bndbox/xmin", "0") or "0")
            ymin = float(_xml_text(obj, "bndbox/ymin", "0") or "0")
            xmax = float(_xml_text(obj, "bndbox/xmax", "0") or "0")
            ymax = float(_xml_text(obj, "bndbox/ymax", "0") or "0")

            normalized = normalize_bbox_xyxy(xmin, ymin, xmax, ymax, sample.width, sample.height)
            if normalized is None:
                continue
            sample.boxes.append((CLASS_MAP[class_name],) + normalized)

    return samples


def compute_split_mapping(samples: dict[Path, Sample], do_split: bool, seed: int, val_ratio: float, test_ratio: float) -> dict[Path, str]:
    items = list(samples.items())
    if not items:
        return {}

    if not do_split:
        return {path: "train" for path, _ in items}

    has_existing_split = any(sample.split_hint in {"train", "val", "test"} for _, sample in items)
    mapping: dict[Path, str] = {}

    if has_existing_split:
        for path, sample in items:
            mapping[path] = sample.split_hint if sample.split_hint in {"train", "val", "test"} else "train"
        return mapping

    rng = random.Random(seed)
    paths = [p for p, _ in items]
    rng.shuffle(paths)

    total = len(paths)
    n_test = int(round(total * test_ratio))
    n_val = int(round(total * val_ratio))
    if n_test + n_val >= total:
        n_test = min(n_test, max(0, total - 2))
        n_val = min(n_val, max(0, total - n_test - 1))

    test_set = set(paths[:n_test])
    val_set = set(paths[n_test:n_test + n_val])

    for path in paths:
        if path in test_set:
            mapping[path] = "test"
        elif path in val_set:
            mapping[path] = "val"
        else:
            mapping[path] = "train"

    return mapping


def compute_split_mapping_yolo_split(samples: dict[Path, Sample], do_split: bool, seed: int, val_ratio: float) -> dict[Path, str]:
    """For RDD_SPLIT YOLO: keep test set, split val from train set."""
    items = list(samples.items())
    if not items:
        return {}

    mapping: dict[Path, str] = {}
    train_pool: list[Path] = []

    for path, sample in items:
        if sample.split_hint == "test":
            mapping[path] = "test"
        else:
            train_pool.append(path)

    if not do_split:
        for p in train_pool:
            mapping[p] = "train"
        return mapping

    rng = random.Random(seed)
    rng.shuffle(train_pool)
    n_val = int(round(len(train_pool) * val_ratio))
    if n_val >= len(train_pool) and len(train_pool) > 1:
        n_val = len(train_pool) - 1

    val_set = set(train_pool[:n_val])
    for p in train_pool:
        mapping[p] = "val" if p in val_set else "train"

    return mapping


def safe_target_stem(src: Path, image_path: Path) -> str:
    rel = image_path.relative_to(src)
    parts = list(rel.parts)
    if not parts:
        return image_path.stem
    parts[-1] = Path(parts[-1]).stem
    stem = "__".join(parts)
    stem = stem.replace(" ", "_")
    return stem


def write_dataset(src: Path, out: Path, samples: dict[Path, Sample], split_map: dict[Path, str]) -> dict[str, object]:
    images_out = out / "images"
    labels_out = out / "labels"
    for split in SPLITS:
        (images_out / split).mkdir(parents=True, exist_ok=True)
        (labels_out / split).mkdir(parents=True, exist_ok=True)

    class_counter: Counter[int] = Counter()
    images_without_labels = 0
    split_counts = Counter()
    object_per_image: list[tuple[str, int]] = []

    for image_path, sample in samples.items():
        split = split_map.get(image_path, "train")
        split_counts[split] += 1

        stem = safe_target_stem(src, image_path)
        dst_image = images_out / split / f"{stem}{image_path.suffix.lower()}"
        dst_label = labels_out / split / f"{stem}.txt"

        copy_with_retry(image_path, dst_image)

        lines: list[str] = []
        for class_id, xc, yc, w, h in sample.boxes:
            class_counter[class_id] += 1
            lines.append(f"{class_id} {xc:.6f} {yc:.6f} {w:.6f} {h:.6f}")

        if not lines:
            images_without_labels += 1
        object_per_image.append((str(dst_image.relative_to(out)).replace("\\", "/"), len(lines)))
        dst_label.write_text("\n".join(lines), encoding="utf-8")

    object_per_image.sort(key=lambda item: item[1], reverse=True)

    report = {
        "num_images_total": len(samples),
        "num_images_train": split_counts.get("train", 0),
        "num_images_val": split_counts.get("val", 0),
        "num_images_test": split_counts.get("test", 0),
        "objects_per_class": {
            CLASS_NAMES[0]: class_counter.get(0, 0),
            CLASS_NAMES[1]: class_counter.get(1, 0),
            CLASS_NAMES[2]: class_counter.get(2, 0),
            CLASS_NAMES[3]: class_counter.get(3, 0),
        },
        "num_images_without_labels": images_without_labels,
        "top_20_images_by_object_count": [
            {"image": image, "objects": count}
            for image, count in object_per_image[:20]
        ],
    }

    return report


def write_data_yaml(out: Path) -> None:
    yaml_text = "\n".join(
        [
            f"path: {str(out.resolve()).replace('\\\\', '/')}",
            "train: images/train",
            "val: images/val",
            "test: images/test",
            "names:",
            f"  0: {CLASS_NAMES[0]}",
            f"  1: {CLASS_NAMES[1]}",
            f"  2: {CLASS_NAMES[2]}",
            f"  3: {CLASS_NAMES[3]}",
            "",
        ]
    )
    (out / "data.yaml").write_text(yaml_text, encoding="utf-8")


def ensure_output_structure(out: Path) -> None:
    """Create output directories expected by Ultralytics dataset layout."""
    for split in SPLITS:
        (out / "images" / split).mkdir(parents=True, exist_ok=True)
        (out / "labels" / split).mkdir(parents=True, exist_ok=True)


def main() -> int:
    args = parse_args()
    src = Path(args.src).expanduser().resolve()
    out = Path(args.out).expanduser().resolve()

    if not src.exists() or not src.is_dir():
        raise PrepareError(f"Source dataset path does not exist or is not a directory: {src}")

    if args.val_ratio < 0 or args.test_ratio < 0 or args.val_ratio + args.test_ratio >= 1:
        raise PrepareError("Invalid split ratios. Require val_ratio >= 0, test_ratio >= 0 and val_ratio + test_ratio < 1")

    images = sorted(iter_images(src))
    if not images:
        raise PrepareError(f"No images found under: {src}")
    print(f"INFO: total images found under source: {len(images)}")

    ann_format, ann_files = detect_annotation_format(src)
    print(f"INFO: detected annotation format: {ann_format}")

    extra_report: dict[str, object] = {}
    if ann_format == "coco":
        print(f"INFO: loading COCO annotations from {len(ann_files)} file(s)")
        samples = parse_coco(src, ann_files, images)
    elif ann_format == "voc":
        print(f"INFO: loading VOC annotations from {len(ann_files)} file(s)")
        samples = parse_voc(src, ann_files, images)
    elif ann_format == "yolo_split":
        print(f"INFO: loading RDD_SPLIT YOLO annotations from base: {ann_files[0]}")
        samples, yolo_report = parse_yolo_split(src, ann_files[0])
        extra_report.update(yolo_report)
        print(f"INFO: yolo_split images loaded: {len(samples)}")
        print(
            "INFO: yolo_split class ids found: "
            f"{extra_report.get('yolo_present_class_ids', [])}, mapping used: {extra_report.get('yolo_class_mapping_used', {})}"
        )
    else:
        raise PrepareError(f"Unsupported annotation format detected: {ann_format}")

    if ann_format == "yolo_split":
        split_map = compute_split_mapping_yolo_split(
            samples=samples,
            do_split=args.split,
            seed=args.seed,
            val_ratio=args.val_ratio,
        )
    else:
        split_map = compute_split_mapping(
            samples=samples,
            do_split=args.split,
            seed=args.seed,
            val_ratio=args.val_ratio,
            test_ratio=args.test_ratio,
        )

    split_counts = Counter(split_map.values())
    print(
        "INFO: split distribution -> "
        f"train={split_counts.get('train', 0)}, val={split_counts.get('val', 0)}, test={split_counts.get('test', 0)}"
    )

    out.mkdir(parents=True, exist_ok=True)
    ensure_output_structure(out)
    print(f"INFO: output structure ready at: {out}")

    print("INFO: copying images and writing labels...")
    report = write_dataset(src, out, samples, split_map)
    print(
        "INFO: copy/write done -> "
        f"images_copied={report.get('num_images_total', 0)}, labels_written={report.get('num_images_total', 0)}, "
        f"images_without_labels={report.get('num_images_without_labels', 0)}"
    )

    print("INFO: generating data.yaml")
    write_data_yaml(out)

    report["annotation_format"] = ann_format
    report["annotation_files"] = [str(p.relative_to(src)).replace("\\", "/") for p in ann_files]
    report["source"] = str(src)
    report["output"] = str(out)
    report.update(extra_report)

    print("INFO: generating prepare_report.json")
    (out / "prepare_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("INFO: dataset preparation complete")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except PrepareError as exc:
        print(f"ERROR: {exc}")
        raise SystemExit(2)
