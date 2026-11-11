"""
Blueprint API Analitik & Monitoring Database: Menyediakan rute data agregasi (/analytic/summary)
dan riwayat log percakapan (/analytic/logs) untuk dashboard /analytic.
Hanya didaftarkan oleh factory aplikasi jika ENABLE_DEBUG=1.
"""

from __future__ import annotations

from typing import Any
from flask import Blueprint, current_app, jsonify, request

analytic_bp = Blueprint("analytic", __name__, url_prefix="/analytic")


# --- Endpoint Ringkasan Analitik & Status Database ---
# Mengembalikan agregasi statistik interaksi (total query, rasio keberhasilan klasifikasi,
# persentase frekuensi 10 intent, dan jumlah record tabel master data).
@analytic_bp.route("/summary", methods=["GET"])
def get_summary() -> tuple[Any, int]:
    chat_service = current_app.extensions["chat_service"]
    data = chat_service.get_analytics_summary()
    return jsonify(data), 200


# --- Endpoint Riwayat Log Percakapan ---
# Mengembalikan daftar catatan interaksi percakapan dari tabel chat_log terurut menurun.
# Mendukung query parameter 'limit' (default: 50, maksimal: 200).
@analytic_bp.route("/logs", methods=["GET"])
def get_logs() -> tuple[Any, int]:
    limit = request.args.get("limit", default=50, type=int)
    limit = max(1, min(limit, 200))

    chat_service = current_app.extensions["chat_service"]
    logs = chat_service.get_recent_logs(limit=limit)
    return jsonify({"logs": logs, "count": len(logs)}), 200
