"""
Handler untuk intent paket: Prix Fixe dan Carte Blanche.
"""

from __future__ import annotations

from app.data.repository import Repository
from app.engine.handlers.base import BaseHandler, HandlerResult
from app.engine.snapshot import NluSnapshot
from app.engine.types import Analysis


# --- Handler Intent Paket Course (Prix Fixe & Carte Blanche) ---
# Mengambil paket course dari database berdasarkan tipe:
# 1. Menampilkan nama paket, harga, durasi menit course, serta narasi konsep dan pengalaman rasa.
# 2. Merinci urutan hidangan sajian bernomor (1..n) beserta deskripsinya.
# 3. Menambahkan seluruh nama hidangan ke dalam protected_spans agar tidak teranotasi ganda oleh glosarium.
class PackageHandler(BaseHandler):
    def __init__(self, tipe: str) -> None:
        self.tipe = tipe  # 'prix_fixe' atau 'carte_blanche'

    def handle(
        self,
        analysis: Analysis,
        repo: Repository,
        snapshot: NluSnapshot,
    ) -> HandlerResult:
        packages = repo.get_packages(tipe=self.tipe)
        if not packages:
            return HandlerResult(is_empty=True)

        protected: list[str] = []

        for pkg in packages:
            for dish in pkg.get("hidangan", []):
                protected.append(dish["nama"])

        return HandlerResult(
            content=packages,
            protected_spans=protected,
        )
