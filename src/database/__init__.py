"""SQLAlchemy Core database foundation for PrepLens."""

from src.database.engine import get_engine
from src.database.schema import metadata

__all__ = ["get_engine", "metadata"]
