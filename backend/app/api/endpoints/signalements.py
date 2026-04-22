# app/api/endpoints/signalements.py

"""
Endpoints Signalements
CRUD signalements espaces urbains
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Body, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy import desc
from sqlalchemy.orm import Session

from ...core.config import settings
from ...core.errors import AppValidationError
from ...core.upload_validation import validate_image_upload
from ...db.session import get_db
from ...models.signalement import Signalement, SignalementStatus
from ...models.user import User, UserRole
from ...schemas.common import ApiResponse, PaginationMeta, ok
from ...schemas.signalement import (
    InteractionMode,
    ProblemCategory,
    PromptSignalementCreate,
    SignalementCreate,
    SignalementDetail,
    SignalementResponse,
    SignalementUpdate,
)
from ...tasks.pipeline_tasks import enqueue_signalement_processing
from ..dependencies import (
    get_current_active_user,
    get_current_user_optional,
    require_owner_or_admin,
)

router = APIRouter()


def parse_signalement_form(
    title: str = Form(...),
    description: str | None = Form(None),
    latitude: float = Form(...),
    longitude: float = Form(...),
    address: str | None = Form(None),
    city: str = Form(...),
    region: str = Form(...),
    metadata: str | None = Form(None),
) -> SignalementCreate:
    """Parse multipart/form-data fields into SignalementCreate model."""
    metadata_obj = None
    if metadata:
        try:
            metadata_obj = json.loads(metadata)
        except json.JSONDecodeError:
            metadata_obj = None

    return SignalementCreate(
        title=title,
        description=description,
        latitude=latitude,
        longitude=longitude,
        address=address,
        city=city,
        region=region,
        metadata=metadata_obj,
    )


def _resolve_owner_user(db: Session, current_user: User | None) -> User:
    """Return authenticated owner or create/reuse DEV guest owner.
    
    For guest users in dev mode, we avoid bcrypt/passlib to prevent
    platform-specific issues (Windows/Python 3.12 with bcrypt AttributeError).
    Guest users have no login, so we use a dummy hashed_password constant.
    """
    if current_user is not None:
        return current_user

    guest_email = "guest@urbanfix.local"
    guest_user = db.query(User).filter(User.email == guest_email).first()
    if guest_user:
        return guest_user

    # Use a dummy constant instead of calling get_password_hash() to avoid
    # bcrypt issues on Windows/Python 3.12 (ValueError: password > 72 bytes,
    # AttributeError: module 'bcrypt' has no '__about__').
    # Guest users never log in, so no real password needed.
    guest_user = User(
        email=guest_email,
        username="guest_user",
        hashed_password="__GUEST_DUMMY_NO_LOGIN__",
        full_name="Guest User",
        role=UserRole.CITIZEN,
        is_active=True,
        is_verified=True,
    )
    db.add(guest_user)
    db.commit()
    db.refresh(guest_user)
    return guest_user


def _resolve_interaction_metadata(metadata_obj: dict | None) -> dict:
    """Normalize interaction metadata with backward-compatible defaults."""
    metadata = dict(metadata_obj or {})
    raw_mode = str(metadata.get("interaction_mode") or InteractionMode.PHOTO_ONLY.value)
    raw_category = str(metadata.get("category") or ProblemCategory.OTHER.value)

    try:
        mode = InteractionMode(raw_mode)
    except ValueError:
        mode = InteractionMode.PHOTO_ONLY

    try:
        category = ProblemCategory(raw_category)
    except ValueError:
        category = ProblemCategory.OTHER

    metadata["interaction_mode"] = mode.value
    metadata["category"] = category.value
    return metadata


@router.post("/", response_model=ApiResponse[SignalementResponse], status_code=status.HTTP_201_CREATED)
async def create_signalement(
    request: Request,
    background_tasks: BackgroundTasks,
    signalement_data: SignalementCreate = Depends(parse_signalement_form),
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    """Cr�er nouveau signalement avec upload image."""
    validate_image_upload(image)
    metadata = _resolve_interaction_metadata(signalement_data.metadata)
    owner_user = _resolve_owner_user(db, current_user)

    uploads_dir = Path(settings.UPLOADS_DIR)
    uploads_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{owner_user.id}_{timestamp}_{image.filename}"
    image_path = uploads_dir / filename

    with open(image_path, "wb") as f:
        content = await image.read()
        f.write(content)

    signalement = Signalement(
        title=signalement_data.title,
        description=signalement_data.description,
        image_path=str(image_path),
        latitude=signalement_data.latitude,
        longitude=signalement_data.longitude,
        address=signalement_data.address,
        city=signalement_data.city,
        region=signalement_data.region,
        user_id=owner_user.id,
        status=SignalementStatus.PENDING,
        progress=0,
        current_stage="queued",
        last_error=None,
        completed_at=None,
        metadata_json=metadata,
        schema_version=1,
    )
    db.add(signalement)
    db.commit()
    db.refresh(signalement)

    return ok(SignalementResponse.model_validate(signalement), request)


@router.post("/prompt", response_model=ApiResponse[dict], status_code=status.HTTP_201_CREATED)
async def create_signalement_prompt_only(
    request: Request,
    background_tasks: BackgroundTasks,
    body: PromptSignalementCreate = Body(...),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    """Create a signalement without image and enqueue prompt-first processing."""
    if body.interaction_mode != InteractionMode.PROMPT_ONLY:
        raise AppValidationError("Cet endpoint supporte uniquement interaction_mode=prompt_only")

    owner_user = _resolve_owner_user(db, current_user)
    metadata = {
        "interaction_mode": body.interaction_mode.value,
        "category": body.category.value,
        "input_kind": "prompt",
        "generate_audio": body.generate_audio,
        "generate_video": body.generate_video,
        "generate_pdf": body.generate_pdf,
    }

    signalement = Signalement(
        title=body.title,
        description=body.description,
        image_path="prompt://no-image",
        latitude=body.latitude if body.latitude is not None else 36.8065,
        longitude=body.longitude if body.longitude is not None else 10.1815,
        address=None,
        city="Unknown",
        region="Unknown",
        user_id=owner_user.id,
        status=SignalementStatus.PENDING,
        progress=0,
        current_stage="queued",
        last_error=None,
        completed_at=None,
        metadata_json=metadata,
        schema_version=1,
    )
    db.add(signalement)
    db.commit()
    db.refresh(signalement)

    enqueue_info = enqueue_signalement_processing(
        signalement.id,
        background_tasks,
        user_prompt=body.user_prompt,
        interaction_mode=body.interaction_mode.value,
        category=body.category.value,
        generate_audio=body.generate_audio,
        generate_video=body.generate_video,
        generate_pdf=body.generate_pdf,
        generate_media=(body.generate_audio or body.generate_video or body.generate_pdf),
    )

    return ok(
        {
            "signalement_id": signalement.id,
            "process_id": enqueue_info.get("task_id") or f"bg-{signalement.id}",
            "status_url": f"/api/v1/process/{signalement.id}/status",
            "queued": True,
            "interaction_mode": body.interaction_mode.value,
            "category": body.category.value,
        },
        request,
    )


@router.get("/", response_model=ApiResponse[List[SignalementResponse]])
async def list_signalements(
    request: Request,
    skip: int = 0,
    limit: int = 20,
    status: Optional[SignalementStatus] = None,
    city: Optional[str] = None,
    region: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Lister signalements avec pagination et filtres."""
    query = db.query(Signalement)

    if status:
        query = query.filter(Signalement.status == status)
    if city:
        query = query.filter(Signalement.city == city)
    if region:
        query = query.filter(Signalement.region == region)

    if current_user.role == "citizen":
        query = query.filter(Signalement.user_id == current_user.id)

    total = query.count()
    rows = query.order_by(desc(Signalement.created_at)).offset(skip).limit(limit).all()

    pagination = PaginationMeta(
        total=total,
        page=skip // limit + 1 if limit else 1,
        page_size=limit,
        pages=(total + limit - 1) // limit if limit else 1,
        has_next=skip + limit < total,
        has_prev=skip > 0,
    )
    items = [SignalementResponse.model_validate(s) for s in rows]
    return ok(items, request, pagination=pagination)


@router.get("/{signalement_id}", response_model=SignalementDetail)
async def get_signalement(
    signalement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """R�cup�rer d�tails d'un signalement."""
    signalement = db.query(Signalement).filter(Signalement.id == signalement_id).first()

    if not signalement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Signalement introuvable",
        )

    if current_user.role == "citizen" and signalement.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acc�s non autoris�",
        )

    return signalement


@router.put("/{signalement_id}", response_model=SignalementResponse)
async def update_signalement(
    signalement_id: int,
    signalement_data: SignalementUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    signalement: Signalement = Depends(require_owner_or_admin()),
):
    """Mettre � jour signalement."""
    update_data = signalement_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(signalement, field, value)

    db.commit()
    db.refresh(signalement)

    return signalement


@router.delete("/{signalement_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_signalement(
    signalement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    signalement: Signalement = Depends(require_owner_or_admin()),
):
    """Supprimer signalement."""
    if os.path.exists(signalement.image_path):
        os.remove(signalement.image_path)

    db.delete(signalement)
    db.commit()

    return None
