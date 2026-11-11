"""
Koneksi basis data SQLite untuk LaPalaisChatBot.
Mengaktifkan mode WAL dan penegakan foreign keys.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "lapalais.db"


# --- Resolusi Lokasi Database ---
# Mengambil path database dari environment variable jika tersedia (misalnya saat testing/staging),
# atau kembali ke path default di folder data/lapalais.db.
def get_db_path() -> Path:
    env_path = os.getenv("DB_PATH")
    if env_path:
        return Path(env_path)
    return DEFAULT_DB_PATH


# --- Pembuatan Koneksi Database ---
# Menginisialisasi koneksi SQLite dengan konfigurasi:
# - sqlite3.Row: agar hasil query bisa diakses dengan nama kolom layaknya dictionary.
# - PRAGMA foreign_keys = ON: menjamin integritas relasional data restoran.
# - PRAGMA busy_timeout = 5000: menunggu hingga 5 detik jika ada operasi tulis konkuren sebelum melempar galat database locked.
def get_connection(db_path: Path | str | None = None) -> sqlite3.Connection:
    target_path = Path(db_path) if db_path else get_db_path()
    conn = sqlite3.connect(target_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA busy_timeout = 5000;")
    return conn
