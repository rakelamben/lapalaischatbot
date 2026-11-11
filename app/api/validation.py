"""
Validasi payload permintaan HTTP untuk endpoint chat.
Memastikan integritas tipe data, pembatasan panjang karakter, dan format JSON.
"""

from __future__ import annotations

from typing import Any


# --- Eksepsi Kustom Validasi Permintaan ---
# Membawa kode error spesifik ('json_tidak_valid', 'pesan_kosong', 'pesan_terlalu_panjang')
# serta pesan penjelasan untuk dikembalikan dalam format respon JSON 400.
class ValidationError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


# --- Validasi Payload Body Chat ---
# Memeriksa data yang dikirimkan klien pada POST /api/chat dan POST /api/debug/chat:
# 1. Payload wajib berupa JSON Object (dict).
# 2. Kolom 'message' wajib ada, bertipe string, dan tidak boleh kosong atau hanya berisi spasi.
# 3. Panjang 'message' dibatasi maksimal 500 karakter untuk keamanan dan mencegah penyalahgunaan beban NLU.
# 4. Kolom 'prev_template_id' bersifat opsional; jika dikirim, harus bernilai integer (atau diabaikan bila None/tidak valid).
def validate_chat_payload(data: Any) -> tuple[str, int | None]:
    if not isinstance(data, dict):
        raise ValidationError(
            code="json_tidak_valid",
            message="Body permintaan harus berupa JSON object yang valid.",
        )

    # Mendukung kunci 'message' (standar API PRD/System Design) atau alias 'pesan'
    message = data.get("message") if "message" in data else data.get("pesan")
    if not isinstance(message, str) or not message.strip():
        raise ValidationError(
            code="pesan_kosong",
            message="Pesan tidak boleh kosong atau hanya berisi spasi.",
        )

    clean_message = message.strip()
    if len(clean_message) > 500:
        raise ValidationError(
            code="pesan_terlalu_panjang",
            message="Pesan tidak boleh melebihi 500 karakter.",
        )

    prev_id = data.get("prev_template_id")
    if prev_id is not None and not isinstance(prev_id, int):
        prev_id = None

    return clean_message, prev_id
