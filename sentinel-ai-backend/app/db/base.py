# Re-export Base and import all models so Alembic autogenerate can discover them.
from app.db.base_class import Base  # noqa: F401
from app.models.user import User  # noqa: F401
