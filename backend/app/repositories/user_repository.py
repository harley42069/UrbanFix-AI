"""Repository User avec filtres soft-delete par défaut."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User


class UserRepository:
    """Accès aux données User."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: int, include_deleted: bool = False) -> User | None:
        stmt = select(User).where(User.id == user_id)
        if not include_deleted:
            stmt = stmt.where(User.is_deleted.is_(False))
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_email(self, email: str, include_deleted: bool = False) -> User | None:
        stmt = select(User).where(User.email == email)
        if not include_deleted:
            stmt = stmt.where(User.is_deleted.is_(False))
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_username(self, username: str, include_deleted: bool = False) -> User | None:
        stmt = select(User).where(User.username == username)
        if not include_deleted:
            stmt = stmt.where(User.is_deleted.is_(False))
        return self.db.execute(stmt).scalar_one_or_none()

    def list_active(self, limit: int = 100, offset: int = 0) -> list[User]:
        stmt = (
            select(User)
            .where(User.is_deleted.is_(False))
            .order_by(User.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())

    def create(self, user: User) -> User:
        self.db.add(user)
        self.db.flush()
        return user

    def soft_delete(self, user: User) -> None:
        user.is_deleted = True
        self.db.add(user)
