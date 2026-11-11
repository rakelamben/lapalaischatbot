"""
Konfigurasi aplikasi Flask untuk LaPalaisChatBot.
Membaca environment variables dengan fallback default yang aman.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=_PROJECT_ROOT / ".env", override=False)


# --- Konfigurasi Lingkungan Aplikasi ---
# Mengelola parameter runtime server:
# - PROJECT_ROOT: Path absolut ke direktori kerja utama proyek.
# - DB_PATH: Lokasi file basis data SQLite (default: data/lapalais.db).
# - ENABLE_DEBUG: Menentukan apakah endpoint dan panel /debug diaktifkan (default: False).
# - ENGINE_CONFIG_PATH: Lokasi file JSON parameter NLU (default: config/engine.json).
# - SECRET_KEY: Kunci sesi Flask.
class Config:
    PROJECT_ROOT = _PROJECT_ROOT
    DB_PATH = Path(os.getenv("DB_PATH", PROJECT_ROOT / "data" / "lapalais.db"))
    ENABLE_DEBUG = os.getenv("ENABLE_DEBUG", "0").lower() in ("1", "true", "yes")
    ENGINE_CONFIG_PATH = Path(os.getenv("ENGINE_CONFIG_PATH", PROJECT_ROOT / "config" / "engine.json"))
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-lapalais-2026")
    TESTING = False


# Konfigurasi khusus untuk unit testing
class TestConfig(Config):
    TESTING = True
    ENABLE_DEBUG = True
