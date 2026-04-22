# DEV Conventions (UrbanFix Backend)

This guide defines stable conventions to avoid import collisions, circular imports, and path inconsistencies.

## 1) Audit Checklist (open files in this order)

1. `backend/app/main.py`
2. `backend/app/api/__init__.py`
3. `backend/app/api/endpoints/__init__.py`
4. `backend/app/services/__init__.py`
5. `backend/app/core/config.py`
6. `backend/app/core/paths.py`
7. `backend/app/api/endpoints/analysis.py`
8. `backend/app/api/endpoints/websocket_endpoint.py`
9. `backend/app/api/endpoints/reports.py`
10. `backend/app/api/endpoints/detection.py`
11. `backend/app/services/detection.py`
12. `backend/app/models/detection.py`
13. `backend/app/api/endpoints/estimation.py`
14. `backend/app/services/cost_estimation.py`
15. `backend/app/models/estimation.py`

Why this order:
- First validate app wiring and router graph.
- Then check service exports and config/path conventions.
- Then inspect endpoints that import each other dynamically (`analysis_store` usage).
- Finally inspect same-name modules across layers (`detection`, `estimation`).

## 2) Stable naming convention

Keep endpoint names by feature, make model/service names explicit.

- Endpoints:
  - `app/api/endpoints/detection.py`
  - `app/api/endpoints/estimation.py`
- Models (preferred explicit names):
  - `app/models/detection_result.py` (instead of `detection.py`)
  - `app/models/cost_estimation.py` (instead of `estimation.py`)
- Services (preferred explicit names):
  - `app/services/yolo_detection_service.py` (instead of `detection.py`)
  - `app/services/groq_cost_estimation_service.py` (instead of `cost_estimation.py`)

Rule of thumb:
- `models/*` should be nouns (`*_result`, `*_record`).
- `services/*` should end with `_service`.
- `api/endpoints/*` should be route-focused feature names.

## 3) Minimal refactor strategy

### Option A (rename only 3-5 critical files)

Suggested low-risk renames:
1. `app/models/detection.py` -> `app/models/detection_result.py`
2. `app/models/estimation.py` -> `app/models/cost_estimation.py`
3. `app/services/detection.py` -> `app/services/yolo_detection_service.py`
4. Optional: `app/services/image_generation.py` -> `app/services/sdxl_image_generation_service.py`

Keep compatibility by adding temporary re-export shims for one release cycle.

Example shim (`app/models/detection.py`):
```python
from .detection_result import Detection

__all__ = ["Detection"]
```

### Option B (keep filenames, use import aliases)

No file rename. Use explicit aliases everywhere collisions exist.

```python
from app.models.detection import Detection as DetectionModel
from app.services.detection import DetectionService as YoloDetectionService
from app.api.endpoints import detection as detection_endpoint
```

For estimations:
```python
from app.models.estimation import Estimation as EstimationModel
from app.services.cost_estimation import CostEstimationService as GroqEstimationService
```

## 4) Import conventions

- Prefer absolute imports from `app.*` in endpoints/services.
- Avoid mixing relative and absolute styles in same file.
- Avoid runtime local imports unless needed to break a true cycle.
- If runtime import is required, add a short comment explaining why.

Good:
```python
from app.core.config import settings
from app.services import get_orchestrator_service
```

Avoid in same file:
```python
from app.core.config import settings
from ...core.security import verify_token
```

## 5) Path conventions

- Do not use hardcoded string paths in endpoints.
- Use `app.core.paths` helpers:
  - `UPLOADS_DIR`, `OUTPUTS_DIR`, `TEMP_DIR`
  - `ensure_runtime_dirs()`
  - `output_path(category, filename)`

Example:
```python
from app.core.paths import UPLOADS_DIR, output_path

image_path = UPLOADS_DIR / f"{file_id}.jpg"
report_path = output_path("reports", f"report_{file_id}.pdf")
```

## 6) Standard API error shape

Use a consistent error payload:

```json
{
  "success": false,
  "error": "VALIDATION_ERROR",
  "detail": "field 'region' is required",
  "timestamp": "2026-03-13T10:00:00Z"
}
```

Suggested error codes:
- `VALIDATION_ERROR`
- `NOT_FOUND`
- `UNAUTHORIZED`
- `FORBIDDEN`
- `CONFLICT`
- `INTERNAL_ERROR`

## 7) Pytest + VS Code compatibility

- Keep import roots stable: `app.*`.
- Keep `__init__.py` in package folders.
- If renaming files (Option A), keep shim modules temporarily.
- Run checks after each rename batch:
  - `pytest backend/test_imports.py`
  - `pytest backend/test_structure.py`
  - `pytest backend/test_api_endpoints.py`
