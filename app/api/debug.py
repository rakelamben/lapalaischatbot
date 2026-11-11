"""
Blueprint API Debug Internal: Menyediakan rute evaluasi dan inspeksi NLU (/api/debug/chat)
serta pemuatan ulang konfigurasi panas (/api/debug/reload).
Hanya didaftarkan oleh factory aplikasi jika ENABLE_DEBUG=1.
"""

from __future__ import annotations

from typing import Any
from flask import Blueprint, current_app, jsonify, request

from app.api.validation import validate_chat_payload

debug_bp = Blueprint("debug", __name__)





# --- Endpoint Percakapan Mode Debug ---
# Menerima format pesan yang sama dengan /api/chat namun mengembalikan rincian komprehensif
# engine NLU (token bersih, ekstraksi entitas, skor 10 intent, alasan keputusan, dan latensi).
@debug_bp.route("/api/debug/chat", methods=["POST"])
def debug_chat() -> tuple[Any, int]:
    data = request.get_json(silent=True)
    message, prev_template_id = validate_chat_payload(data)

    chat_service = current_app.extensions["chat_service"]
    result = chat_service.handle_message(
        message=message,
        prev_template_id=prev_template_id,
        is_debug=True,
    )

    return jsonify(result), 200


# --- Endpoint Hot Reload Snapshot ---
# Membaca ulang tabel-tabel konfigurasi NLU dari database SQLite ke memori aplikasi
# tanpa memerlukan restart proses server (zero downtime configuration update).
@debug_bp.route("/api/debug/reload", methods=["POST"])
def debug_reload() -> tuple[Any, int]:
    chat_service = current_app.extensions["chat_service"]
    chat_service.reload_snapshot()

    return jsonify({"status": "reloaded"}), 200
