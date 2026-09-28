import os
import sys
import tempfile
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from climatrend.climate.db.database import get_db, init_db



@pytest.fixture
def temp_db_path(tmp_path: Path):
    """Provides an isolated SQLite database path for testing."""
    db_file = tmp_path / "test_climate.db"
    init_db(db_file)
    return db_file


@pytest.fixture
def db_conn(temp_db_path: Path):
    """Provides a database connection to the temporary test database."""
    with get_db(temp_db_path) as conn:
        yield conn
