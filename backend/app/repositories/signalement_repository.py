"""Repository Signalement avec filtres soft-delete par défaut."""

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.signalement import Signalement, SignalementStatus


class SignalementRepository:
    """Accès aux données Signalement."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, signalement_id: int, include_deleted: bool = False) -> Signalement | None:
        stmt = (
            select(Signalement)
            .options(selectinload(Signalement.detections), selectinload(Signalement.estimations))
            .where(Signalement.id == signalement_id)
        )
        if not include_deleted:
            stmt = stmt.where(Signalement.is_deleted.is_(False))
        return self.db.execute(stmt).scalar_one_or_none()

    def list_for_user(
        self,
        user_id: int,
        status: SignalementStatus | None = None,
        city: str | None = None,
        region: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Signalement]:
        stmt = select(Signalement).where(
            Signalement.user_id == user_id,
            Signalement.is_deleted.is_(False),
        )
        if status is not None:
            stmt = stmt.where(Signalement.status == status)
        if city:
            stmt = stmt.where(Signalement.city == city)
        if region:
            stmt = stmt.where(Signalement.region == region)

        stmt = stmt.order_by(Signalement.created_at.desc()).offset(offset).limit(limit)
        return list(self.db.execute(stmt).scalars().all())

    def create(self, signalement: Signalement) -> Signalement:
        self.db.add(signalement)
        self.db.flush()
        return signalement

    def soft_delete(self, signalement: Signalement) -> None:
        signalement.is_deleted = True
        self.db.add(signalement)
