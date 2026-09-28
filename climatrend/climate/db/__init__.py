"""
ClimaTrend Climate Database Package.
Provides SQLite connection management, schema initialization, and query helpers.
"""

from climatrend.climate.db.database import get_db, init_db

__all__ = ["get_db", "init_db"]
