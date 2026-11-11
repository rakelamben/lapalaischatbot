"""
Handler untuk intent reservasi.
"""

from __future__ import annotations

from flask import jsonify

from app.data.repository import Repository
from app.engine.handlers.base import BaseHandler, HandlerResult
from app.engine.snapshot import NluSnapshot
from app.engine.types import Analysis


# --- Handler Intent Informasi Reservasi ---
# Mengambil ketentuan operasional, kontak, jam buka, dan aturan reservasi dari tabel reservation_info,
# lalu memformatnya menjadi poin-poin terurut untuk disubstitusikan ke template respons.
class ReservasiHandler(BaseHandler):
    def handle(
        self,
        analysis: Analysis,
        repo: Repository,
        snapshot: NluSnapshot,
    ) -> HandlerResult:
        info_rows = repo.get_reservation_info()
        data = info_rows if info_rows else None
        return HandlerResult(content=data)
