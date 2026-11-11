"""
Blueprint Halaman Web LaPalaisChatBot: Menyajikan seluruh rute antarmuka visual
(beranda tamu /, konsol evaluasi /debug, dan dashboard analitik /analytic).
"""

from __future__ import annotations

from flask import Blueprint, abort, current_app, render_template

pages_bp = Blueprint("pages", __name__)


# --- Rute Beranda Antarmuka Tamu ---
# Menyajikan halaman landing dan antarmuka obrolan virtual concierge restoran La Palais.
@pages_bp.route("/", methods=["GET"])
def index() -> str:
    return render_template("index.html")


# --- Halaman Web Debug NLU ---
# Menyajikan antarmuka visual konsol debug 3-section untuk evaluator engine NLU.
# Dibatasi secara ketat dan hanya dapat diakses bila server berjalan dengan ENABLE_DEBUG=1.
@pages_bp.route("/debug", methods=["GET"])
def debug_page() -> str:
    if not current_app.config.get("ENABLE_DEBUG", False):
        abort(404)
    return render_template("debug.html")


# --- Halaman Dashboard Analitik & Monitoring Database ---
# Menyajikan visualisasi KPI performa klasifikasi intent, distribusi 10 intent,
# status tabel master restoran, serta tabel interaksi riwayat chat_log.
# Dibatasi secara ketat dan hanya dapat diakses bila server berjalan dengan ENABLE_DEBUG=1.
@pages_bp.route("/analytic", methods=["GET"])
def analytic_page() -> str:
    if not current_app.config.get("ENABLE_DEBUG", False):
        abort(404)
    return render_template("analytic.html")
