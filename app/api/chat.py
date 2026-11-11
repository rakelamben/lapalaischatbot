"""
Blueprint API Chat & Health: Menyediakan rute publik untuk tamu restoran (/api/chat)
serta pemeriksaan kesiapan sistem (/healthz).
"""

from __future__ import annotations

import sqlite3
from typing import Any
from flask import Blueprint, current_app, jsonify, request

from app.api.validation import validate_chat_payload

chat_bp = Blueprint("chat", __name__)


# --- Endpoint Percakapan Publik ---
# Menerima payload JSON {"pesan": str, "prev_template_id": int | null}.
# Memvalidasi input melalui validate_chat_payload dan mengeksekusi layanan ChatService.
# Respon hanya memuat teks jawaban, template_id, dan saran kanonik (tanpa bocoran data internal/debug).
@chat_bp.route("/api/chat", methods=["POST"])
def chat() -> tuple[Any, int]:
    data = request.get_json(silent=True)
    message, prev_template_id = validate_chat_payload(data)

    chat_service = current_app.extensions["chat_service"]
    result = chat_service.handle_message(
        message=message,
        prev_template_id=prev_template_id,
        is_debug=False,
    )

    return jsonify(result), 200


# --- Endpoint Kesiapan Layanan (Health Check) ---
# Memeriksa status kesehatan server dan konektivitas dasar ke database SQLite.
# Digunakan oleh load balancer, docker orchestrator, atau sistem monitoring.
@chat_bp.route("/healthz", methods=["GET"])
def healthz() -> tuple[Any, int]:
    try:
        db_path = current_app.config["DB_PATH"]
        conn = sqlite3.connect(str(db_path))
        conn.execute("SELECT 1;")
        conn.close()
        return jsonify({"status": "ok"}), 200
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500
