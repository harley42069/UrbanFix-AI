# YOLO Training Guide (Road Damage)

This guide explains how to train and evaluate Ultralytics YOLO using the prepared dataset.

## Prerequisites

- Python 3.12 environment activated
- Prepared dataset with:
  - datasets/rdd2022_yolo/data.yaml
  - datasets/rdd2022_yolo/images/train|val|test
  - datasets/rdd2022_yolo/labels/train|val|test
- Ultralytics installed:

```powershell
python -m pip install ultralytics
```

## Recommended Training Commands

### GPU (recommended)

```powershell
python tools/train_yolo_road_damage.py --data datasets/rdd2022_yolo/data.yaml --model yolov8s.pt --imgsz 960 --epochs 80 --device 0 --batch auto --project runs_road_damage --name yolov8s_rdd2022
```

### CPU (fallback)

```powershell
python tools/train_yolo_road_damage.py --data datasets/rdd2022_yolo/data.yaml --model yolov8s.pt --imgsz 960 --epochs 80 --device cpu --batch 4 --project runs_road_damage --name yolov8s_rdd2022_cpu
```

### Train and export ONNX

```powershell
python tools/train_yolo_road_damage.py --data datasets/rdd2022_yolo/data.yaml --model yolov8s.pt --imgsz 960 --epochs 80 --export onnx
```

## Key Parameters

- `--data`: dataset YAML path
- `--model`: base checkpoint (`yolov8n.pt`, `yolov8s.pt`, etc.)
- `--imgsz`: image size used during training/validation
- `--epochs`: number of training epochs
- `--batch`: `auto` on GPU or explicit int
- `--device`: `0` for first GPU, or `cpu`
- `--project`, `--name`: output run directory

## Output Artifacts

Typical run directory:

- `runs_road_damage/<name>/weights/best.pt`
- `runs_road_damage/<name>/weights/last.pt`
- `runs_road_damage/<name>/train_summary.json`
- `runs_road_damage/<name>/results.png`
- optional ONNX export file when `--export onnx`

## Metrics Interpretation

In `train_summary.json`, key metrics are:

- `mAP50`: AP at IoU=0.50 (higher is better)
- `mAP50_95`: AP averaged over IoU 0.50 to 0.95 (stricter, higher is better)
- `precision`: fraction of predicted positives that are correct
- `recall`: fraction of ground-truth objects detected

Suggested practical checks:

1. `mAP50` increases over epochs and stabilizes
2. `mAP50_95` improves without severe precision/recall collapse
3. precision/recall balance is acceptable for your deployment

## Evaluation (Val/Test)

Example test evaluation with best weights:

```powershell
python tools/eval_yolo_road_damage.py --weights runs_road_damage/yolov8s_rdd2022/weights/best.pt --data datasets/rdd2022_yolo/data.yaml --split test --imgsz 960 --device 0
```

This writes `eval_report_test.json` in the run directory.

## Backend Integration Recommendation

Recommended deployment path for backend config:

1. Keep training outputs in `runs_road_damage/<name>/weights/best.pt`
2. Copy selected model to backend models folder:

```powershell
Copy-Item runs_road_damage/yolov8s_rdd2022/weights/best.pt backend/models/yolo_road_damage_best.pt
```

3. Point backend YOLO model path to this file (for example via env/config):

- `backend/models/yolo_road_damage_best.pt`

This keeps training runs reproducible while backend uses a stable model path.

## Production-Ready Backend Notes

- Stable model file expected by backend runtime:
  - `backend/models/yolo_road_damage_best.pt`
- Recommended setting in backend env:
  - `YOLO_MODEL_PATH=./models/yolo_road_damage_best.pt`

If the configured model file is missing, the detection service logs a warning and
the API remains available in graceful fallback mode (`boxes=[]` + `warnings`).

### Annotated Image Output Convention

When annotation is generated for a process, backend stores it under a stable path:

- `<outputs_root>/process/<process_id>/annotated.jpg`

Status payload keeps historical fields and now also exposes:

- `outputs.annotated_image` (existing)
- `outputs.annotated_image_path` (non-breaking explicit alias)

## Release Checklist

Use this checklist before promoting a model/backend release.

1. Place the model at stable backend path:
  - `./models/yolo_road_damage_best.pt`

2. Verify backend env vars:
  - `YOLO_MODEL_PATH=./models/yolo_road_damage_best.pt`
  - `YOLO_CONFIDENCE_THRESHOLD=0.25`
  - `YOLO_IOU_THRESHOLD=0.45`

3. Run unit tests:

```powershell
Push-Location backend
$env:PYTHONPATH='.'
pytest tests/test_process_status.py tests/test_detection_fallback.py -q
Pop-Location
```

4. Run smoke process and check status API:

```powershell
Push-Location backend
$env:PYTHONPATH='.'
pytest tests/test_process_status.py -k smoke -q
Pop-Location
```

5. Confirm expected `/status` fields are present:
  - `detections`
  - `detection_result`
  - `outputs.annotated_image_path`
