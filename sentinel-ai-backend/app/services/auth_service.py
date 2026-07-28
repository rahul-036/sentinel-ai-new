import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.models.user import User
from app.repositories.user_repository import create, get_by_email, get_by_id
from app.schemas.user import UserCreate


async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    return await get_by_id(db, user_id)


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    return await get_by_email(db, email)


async def create_user(db: AsyncSession, schema: UserCreate) -> User:
    hashed = hash_password(schema.password)
    return await create(db, schema, hashed)


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User | None:
    user = await get_by_email(db, email)
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user
