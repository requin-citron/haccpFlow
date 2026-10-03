from __future__ import annotations

import logging

from sqlalchemy import func, select

from app.config import Settings
from app.core.security import hash_password
from app.db.session import get_session_factory
from app.models.user import User, UserRole, normalize_email

logger = logging.getLogger(__name__)


async def seed_admin_user(settings: Settings) -> None:
    """Create the first admin if the users table is empty.

    Never overwrites an existing user and never logs the password.
    """

    email = normalize_email(settings.admin_email)
    password = settings.admin_password.get_secret_value()
    if not email or not password:
        return

    async with get_session_factory()() as session:
        existing = await session.scalar(select(func.count()).select_from(User))
        if existing:
            return
        session.add(
            User(
                email=email,
                hashed_password=hash_password(password),
                role=UserRole.ADMIN,
                is_active=True,
            )
        )
        await session.commit()
        logger.info("Created initial admin user %s", email)
