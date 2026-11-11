"""
Handler untuk intent sosial: Sapaan dan Penutup.
"""

from __future__ import annotations

from app.data.repository import Repository
from app.engine.handlers.base import BaseHandler, HandlerResult
from app.engine.snapshot import NluSnapshot
from app.engine.types import Analysis


# --- Handler Intent Sosial (Sapaan & Penutup) ---
# Intent sosial tidak membutuhkan data dari database SQLite dan template responsnya
# tidak memuat placeholder {daftar}, sehingga handler mengembalikan HandlerResult kosong.
class SocialHandler(BaseHandler):
    def handle(
        self,
        analysis: Analysis,
        repo: Repository,
        snapshot: NluSnapshot,
    ) -> HandlerResult:
        return HandlerResult()
