"""
Penanganan galat terstandar dalam format JSON untuk aplikasi Flask.
Memastikan seluruh galat HTTP mengembalikan struktur { "error": { "code", "message" } }.
"""

from __future__ import annotations

import logging
from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException

from app.api.validation import ValidationError

logger = logging.getLogger(__name__)


# --- Registrasi Handler Galat Global ---
# Mengikat handler ke aplikasi Flask agar respon galat selalu konsisten:
# 1. ValidationError (400): Mengembalikan kode galat spesifik dari lapisan validasi input.
# 2. HTTP 404: Mengembalikan pesan ramah jika route atau endpoint tidak ditemukan.
# 3. HTTP 405: Mengembalikan pesan jika metode HTTP yang digunakan salah.
# 4. HTTP 500 & Unhandled Exception: Menangkap galat tak terduga, mencatatnya ke server log,
#    dan menyajikan pesan generik tanpa membocorkan trace internal ke pengguna.
def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(ValidationError)
    def handle_validation_error(err: ValidationError):
        return jsonify({
            "error": {
                "code": err.code,
                "message": err.message,
            }
        }), err.status_code

    @app.errorhandler(400)
    def handle_bad_request(err):
        msg = getattr(err, "description", "Permintaan tidak valid.")
        return jsonify({
            "error": {
                "code": "permintaan_tidak_valid",
                "message": msg,
            }
        }), 400

    @app.errorhandler(404)
    def handle_not_found(err):
        return jsonify({
            "error": {
                "code": "tidak_ditemukan",
                "message": "Endpoint atau sumber daya yang diminta tidak ditemukan.",
            }
        }), 404

    @app.errorhandler(405)
    def handle_method_not_allowed(err):
        return jsonify({
            "error": {
                "code": "metode_tidak_diizinkan",
                "message": f"Metode {request.method} tidak diizinkan untuk endpoint ini.",
            }
        }), 405

    @app.errorhandler(500)
    @app.errorhandler(Exception)
    def handle_server_error(err):
        # Jika itu adalah HTTPException bawaan Werkzeug (misal 401, 403), teruskan statusnya
        if isinstance(err, HTTPException):
            return jsonify({
                "error": {
                    "code": "kesalahan_http",
                    "message": err.description,
                }
            }), err.code

        # Untuk eksepsi tak terduga lainnya (status 500)
        logger.error(f"Kesalahan server internal pada {request.path}: {err}", exc_info=True)
        return jsonify({
            "error": {
                "code": "kesalahan_server",
                "message": "Terjadi kesalahan internal pada server. Silakan coba beberapa saat lagi.",
            }
        }), 500
