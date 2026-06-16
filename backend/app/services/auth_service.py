from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User
from app.security import create_access_token, hash_password, verify_password


class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def get_by_email(self, email: str) -> User | None:
        return self.db.scalar(select(User).where(User.user_email == email.lower()))

    def authenticate(self, email: str, password: str) -> tuple[User, str] | None:
        user = self.get_by_email(email)
        if not user or not user.is_active:
            return None
        if not verify_password(password, user.password_hash):
            return None
        token = create_access_token(user.user_id, user.user_role)
        return user, token

    def create_user(self, email: str, password: str, full_name: str, role: str) -> User:
        user = User(
            user_email=email.lower(),
            password_hash=hash_password(password),
            full_name=full_name,
            user_role=role,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
