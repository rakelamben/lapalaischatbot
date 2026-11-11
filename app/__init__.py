"""
Factory Aplikasi Flask LaPalaisChatBot: Menginisialisasi komponen aplikasi,
memuat konfigurasi lingkungan, mendaftarkan blueprint rute, serta menyiapkan layanan ChatService.
"""

from __future__ import annotations

import sqlite3
from typing import Type

from flask import Flask

from app.api import analytic_bp, chat_bp, debug_bp
from app.config import Config
from app.engine.params import EngineParams
from app.engine.snapshot import NluSnapshot
from app.errors import register_error_handlers
from app.pages import pages_bp
from app.services.chat_service import ChatService


# --- Application Factory: Inisialisasi Server Flask ---
# Menjalankan tahapan bootstrap sistem:
# 1. Memuat konfigurasi environment (DB path, debug flag, engine config path).
# 2. Mendaftarkan handler error terpusat (400, 404, 405, 500).
# 3. Memuat model NLU in-memory (NluSnapshot) dari SQLite dan parameter scoring (EngineParams).
# 4. Menginisialisasi ChatService pada extensions Flask.
# 5. Mendaftarkan blueprint publik (chat, pages) serta blueprint debug secara kondisional (isolasi fisik ENABLE_DEBUG).
def create_app(
    config_class: Type[Config] = Config,
    snapshot: NluSnapshot | None = None,
    params: EngineParams | None = None,
) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class)

    # 1. Daftarkan error handler terpusat
    register_error_handlers(app)

    # 2. Muat parameter NLU
    if params is None:
        params_path = app.config.get("ENGINE_CONFIG_PATH")
        if params_path and params_path.exists():
            params = EngineParams.from_file(params_path)
        else:
            params = EngineParams()

    # 3. Muat snapshot NLU in-memory
    db_path = app.config["DB_PATH"]
    if snapshot is None:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        try:
            snapshot = NluSnapshot.from_db(conn)
        finally:
            conn.close()

    # 4. Inisialisasi layanan chat bisnis
    chat_service = ChatService(
        snapshot=snapshot,
        params=params,
        db_path=db_path,
    )
    app.extensions["chat_service"] = chat_service

    # 5. Daftarkan rute blueprint
    app.register_blueprint(pages_bp)
    app.register_blueprint(chat_bp)

    # Isolasi fisik: blueprint debug dan analitik hanya didaftarkan jika ENABLE_DEBUG aktif
    if app.config.get("ENABLE_DEBUG", False):
        app.register_blueprint(debug_bp)
        app.register_blueprint(analytic_bp)

    return app
