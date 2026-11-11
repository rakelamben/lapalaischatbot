"""
Handler untuk intent teknik masakan.
"""

from __future__ import annotations

from app.data.repository import Repository
from app.engine.handlers.base import BaseHandler, HandlerResult
from app.engine.snapshot import NluSnapshot
from app.engine.types import Analysis


# --- Handler Intent Teknik Masakan Prancis ---
# Mengambil daftar istilah teknik memasak Prancis (sous-vide, confit, flambe, dll.)
# beserta penjelasan maknanya dalam satu kalimat ringkas.
# Baik istilah maupun definisi dimasukkan ke protected_spans karena artinya sudah ada di baris tersebut.
class TeknikHandler(BaseHandler):
    def handle(
        self,
        analysis: Analysis,
        repo: Repository,
        snapshot: NluSnapshot,
    ) -> HandlerResult:
        terms = repo.get_technique_terms()
        if not terms:
            return HandlerResult(is_empty=True)

        protected: list[str] = []

        for t in terms:
            istilah = t["istilah"]
            makna = t["makna"]
            # Lindungi istilah & makna pada baris teknik agar tidak teranotasi ganda
            protected.append(istilah)
            protected.append(makna)

        return HandlerResult(
            content=terms,
            protected_spans=protected,
        )
