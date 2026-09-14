"""Common FastAPI dependencies, re-exported for convenient importing from routes."""
from app.core.database import get_db
from app.core.security import get_current_user, get_current_user_id, require_permission

__all__ = ["get_db", "get_current_user", "get_current_user_id", "require_permission"]
