#!/usr/bin/env python3
"""Evaluate YOLO road-damage model on val/test split and write eval_report.json."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


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


def _metrics_summary(metrics_obj: Any) -> dict[str, float | None]:
    map50 = _extract_metric(metrics_obj, "box.map50") or _extract_metric(metrics_obj, "metrics/mAP50(B)")
    map5095 = _extract_metric(metrics_obj, "box.map") or _extract_metric(metrics_obj, "metrics/mAP50-95(B)")
    precision = _extract_metric(metrics_obj, "box.mp") or _extract_metric(metrics_obj, "metrics/precision(B)")
    recall = _extract_metric(metrics_obj, "box.mr") or _extract_metric(metrics_obj, "metrics/recall(B)")
    return {
        "mAP50": map50,
        "mAP50_95": map5095,
        "precision": precision,
        "recall": recall,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate YOLO road damage model")
    parser.add_argument("--weights", required=True, help="Path to best.pt or last.pt")
    parser.add_argument("--data", default="datasets/rdd2022_yolo/data.yaml", help="Path to data.yaml")
    parser.add_argument("--split", default="test", choices=["val", "test"], help="Evaluation split")
    parser.add_argument("--imgsz", type=int, default=960, help="Validation image size")
    parser.add_argument("--device", default="cpu", help="Device for evaluation")
    parser.add_argument("--out", default=None, help="Optional output report path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    weights = Path(args.weights).expanduser().resolve()
    data_yaml = Path(args.data).expanduser().resolve()

    if not weights.exists():
        raise FileNotFoundError(f"weights file not found: {weights}")
    if not data_yaml.exists():
        raise FileNotFoundError(f"data.yaml not found: {data_yaml}")

    from ultralytics import YOLO

    model = YOLO(str(weights))
    metrics_obj = model.val(
        data=str(data_yaml),
        split=args.split,
        imgsz=args.imgsz,
        device=args.device,
    )

    metrics = _metrics_summary(metrics_obj)

    out_path = (
        Path(args.out).expanduser().resolve()
        if args.out
        else weights.resolve().parents[1] / f"eval_report_{args.split}.json"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "date_utc": datetime.now(timezone.utc).isoformat(),
        "weights": str(weights),
        "data_yaml": str(data_yaml),
        "split": args.split,
        "imgsz": args.imgsz,
        "device": args.device,
        "metrics": metrics,
    }

    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"INFO: evaluation report written to {out_path}")
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
