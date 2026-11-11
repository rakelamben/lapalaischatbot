"""
Handler terpadu untuk intent Diet dan Harga (menu filter bersama).
Memproses entitas harga dan label diet secara simultan.
"""

from __future__ import annotations

from app.data.repository import Repository
from app.engine.handlers.base import BaseHandler, HandlerResult
from app.engine.snapshot import NluSnapshot
from app.engine.types import Analysis


# --- Handler Filter Gabungan (Diet & Harga) ---
# Mengimplementasikan PRD R4: entitas harga dan diet diekstrak untuk memilih subset data yang sama.
# Mendukung 4 skenario pemfilteran data:
# 1. Hanya label diet tanpa batasan harga.
# 2. Harga batas atas (op == 'le'): memfilter hidangan <= batas.
# 3. Harga batas bawah (op == 'gt'): memfilter hidangan > batas.
# 4. Rentang umum (op == 'both'): menggabungkan hasil kedua batas.
class MenuFilterHandler(BaseHandler):
    def handle(
        self,
        analysis: Analysis,
        repo: Repository,
        snapshot: NluSnapshot,
    ) -> HandlerResult:
        ent = analysis.entities
        diet_codes = list(ent.diet)
        harga_ent = ent.harga

        protected: list[str] = []

        # Kasus 1: Tanpa entitas harga spesifik (misal hanya filter diet)
        if not harga_ent:
            items = repo.filter_menu_items(diet_codes=diet_codes)
            if not items:
                return HandlerResult(is_empty=True)

            for item in items:
                protected.append(item["nama"])

            return HandlerResult(
                content=items,
                protected_spans=protected,
            )

        # Kasus 2: Entitas harga op == 'le' (<= batas)
        if harga_ent.op == "le":
            items = repo.filter_menu_items(batas_le=harga_ent.nilai, diet_codes=diet_codes)
            if not items:
                return HandlerResult(is_empty=True)

            for item in items:
                protected.append(item["nama"])

            return HandlerResult(
                content=items,
                protected_spans=protected,
            )

        # Kasus 3: Entitas harga op == 'gt' (> batas)
        if harga_ent.op == "gt":
            items = repo.filter_menu_items(batas_gt=harga_ent.nilai, diet_codes=diet_codes)
            if not items:
                return HandlerResult(is_empty=True)

            for item in items:
                protected.append(item["nama"])

            return HandlerResult(
                content=items,
                protected_spans=protected,
            )

        # Kasus 4: Entitas harga op == 'both' (tampilkan dua kelompok: <= batas dan > batas)
        threshold = harga_ent.nilai
        items_le = repo.filter_menu_items(batas_le=threshold, diet_codes=diet_codes)
        items_gt = repo.filter_menu_items(batas_gt=threshold, diet_codes=diet_codes)

        if not items_le and not items_gt:
            return HandlerResult(is_empty=True)

        if items_le:
            for item in items_le:
                protected.append(item["nama"])

        if items_gt:
            for item in items_gt:
                protected.append(item["nama"])

        return HandlerResult(
            content=items_le + items_gt,
            protected_spans=protected,
        )
