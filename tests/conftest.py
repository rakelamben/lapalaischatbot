"""
Pytest fixtures untuk LaPalaisChatBot.
Menyediakan koneksi SQLite in-memory / file sementara yang di-seed dari data/seed.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

# Pastikan root proyek masuk ke sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from scripts.seed import build_db


@pytest.fixture(scope="session")
def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def seed_dir(project_root: Path) -> Path:
    return project_root / "seed"


@pytest.fixture(scope="session")
def migrations_dir(project_root: Path) -> Path:
    return project_root / "migrations"


@pytest.fixture
def temp_db_path(tmp_path: Path, seed_dir: Path, migrations_dir: Path) -> Path:
    """Fixture path file SQLite sementara yang di-seed untuk setiap test."""
    db_file = tmp_path / "test_lapalais.db"
    build_db(db_file, seed_dir, migrations_dir, reset=True)
    return db_file


@pytest.fixture
def temp_db(temp_db_path: Path) -> sqlite3.Connection:
    """Fixture koneksi database SQLite sementara yang di-seed untuk setiap test."""
    conn = sqlite3.connect(temp_db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    yield conn
    conn.close()
