"""
Handler untuk intent pairing minuman (wine dan non-alkohol).
"""

from __future__ import annotations

from app.data.repository import Repository
from app.engine.handlers.base import BaseHandler, HandlerResult
from app.engine.snapshot import NluSnapshot
from app.engine.types import Analysis


# --- Handler Intent Informasi Pairing Minuman ---
# Mengambil relasi pairing dari database untuk hidangan dan minuman,
# beserta catatan aroma/karakternya.
# Nama hidangan dan nama minuman dilindungi (protected_spans) agar tidak teranotasi ganda oleh glosarium.
class PairingHandler(BaseHandler):
    def handle(
        self,
        analysis: Analysis,
        repo: Repository,
        snapshot: NluSnapshot,
    ) -> HandlerResult:
        pairings = repo.get_pairings()
        if not pairings:
            return HandlerResult(is_empty=True)

        protected: list[str] = []

        for p in pairings:
            protected.append(p["hidangan"])
            protected.append(p["minuman"])

        return HandlerResult(
            content=pairings,
            protected_spans=protected,
        )
