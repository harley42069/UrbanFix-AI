#!/usr/bin/env python3
"""Train YOLO road-damage detector with Ultralytics Python API.

Writes a training summary JSON under:
  <project>/<name>/train_summary.json
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _gpu_available() -> bool:
    try:
        import torch

        return bool(torch.cuda.is_available())
    except Exception:
        return False


def _resolve_device(device_arg: str | None) -> str:
    if device_arg:
        return device_arg
    return "0" if _gpu_available() else "cpu"


def _resolve_batch(batch_arg: str | None) -> int | str:
    if batch_arg:
        lower = batch_arg.strip().lower()
        if lower == "auto":
            return "auto"
        return int(batch_arg)
    return "auto" if _gpu_available() else 4


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except Exception:
        return None


def _extract_metric(metrics_obj: Any, attr_path: str) -> float | None:
    cur = metrics_obj
    for part in attr_path.split("."):
        if cur is None:
            return None
        if isinstance(cur, dict):
            cur = cur.get(part)
        else:
            cur = getattr(cur, part, None)
    return _safe_float(cur)


def _metrics_summary(train_result: Any) -> dict[str, float | None]:
    candidates = [train_result]
    trainer = getattr(train_result, "trainer", None)
    if trainer is not None:
        candidates.append(getattr(trainer, "metrics", None))

    map50 = map5095 = precision = recall = None
    for candidate in candidates:
        if candidate is None:
            continue

        map50 = map50 or _extract_metric(candidate, "box.map50")
        map5095 = map5095 or _extract_metric(candidate, "box.map")
        precision = precision or _extract_metric(candidate, "box.mp")
        recall = recall or _extract_metric(candidate, "box.mr")

        if map50 is None:
            map50 = _extract_metric(candidate, "metrics/mAP50(B)")
        if map5095 is None:
            map5095 = _extract_metric(candidate, "metrics/mAP50-95(B)")
        if precision is None:
            precision = _extract_metric(candidate, "metrics/precision(B)")
        if recall is None:
            recall = _extract_metric(candidate, "metrics/recall(B)")

    return {
        "mAP50": map50,
        "mAP50_95": map5095,
        "precision": precision,
        "recall": recall,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train YOLO road damage model with Ultralytics")
    parser.add_argument("--data", default="datasets/rdd2022_yolo/data.yaml", help="Path to data.yaml")
    parser.add_argument("--model", default="yolov8s.pt", help="Base model checkpoint")
    parser.add_argument("--imgsz", type=int, default=960, help="Input image size")
    parser.add_argument("--epochs", type=int, default=80, help="Number of epochs")
    parser.add_argument(
        "--batch",
        default=None,
        help="Batch size. Default: auto on GPU, 4 on CPU. You can pass an int or 'auto'.",
    )
    parser.add_argument(
        "--device",
        default=None,
        help="Training device. Default: 0 if GPU is available else cpu.",
    )
    parser.add_argument("--project", default="runs_road_damage", help="Output project directory")
    parser.add_argument("--name", default="yolov8s_rdd2022", help="Run name")
    parser.add_argument(
        "--export",
        default="none",
        choices=["none", "onnx"],
        help="Optional export format after training (default: none)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    data_yaml = Path(args.data).expanduser().resolve()
    if not data_yaml.exists():
        raise FileNotFoundError(f"data.yaml not found: {data_yaml}")

    device = _resolve_device(args.device)
    batch = _resolve_batch(args.batch)

    print("INFO: training configuration")
    print(f"INFO: data={data_yaml}")
    print(f"INFO: model={args.model}, imgsz={args.imgsz}, epochs={args.epochs}, batch={batch}, device={device}")
    print(f"INFO: project={args.project}, name={args.name}")

    from ultralytics import YOLO

    model = YOLO(args.model)
    train_result = model.train(
        data=str(data_yaml),
        imgsz=args.imgsz,
        epochs=args.epochs,
        batch=batch,
        device=device,
        project=args.project,
        name=args.name,
    )

    save_dir = Path(getattr(train_result, "save_dir", Path(args.project) / args.name)).resolve()
    best_weights = (save_dir / "weights" / "best.pt").resolve()

    export_path: str | None = None
    if args.export == "onnx":
        print("INFO: exporting best model to ONNX")
        export_model = YOLO(str(best_weights if best_weights.exists() else save_dir / "weights" / "last.pt"))
        exported = export_model.export(format="onnx", imgsz=args.imgsz)
        export_path = str(exported)

    metrics = _metrics_summary(train_result)

    summary = {
        "date_utc": datetime.now(timezone.utc).isoformat(),
        "data_yaml": str(data_yaml),
        "run_dir": str(save_dir),
        "best_weights_path": str(best_weights),
        "metrics": metrics,
        "hyperparams": {
            "model": args.model,
            "imgsz": args.imgsz,
            "epochs": args.epochs,
            "batch": batch,
            "device": device,
            "project": args.project,
            "name": args.name,
        },
        "export": {
            "format": args.export,
            "path": export_path,
        },
    }

    save_dir.mkdir(parents=True, exist_ok=True)
    summary_path = save_dir / "train_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"INFO: training summary written to {summary_path}")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
