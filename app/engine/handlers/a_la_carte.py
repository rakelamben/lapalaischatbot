"""
Handler untuk intent menu à la carte.
"""

from __future__ import annotations

from app.data.repository import Repository
from app.engine.handlers.base import BaseHandler, HandlerResult
from app.engine.snapshot import NluSnapshot
from app.engine.types import Analysis


# --- Handler Intent Menu À La Carte ---
# Mengambil seluruh hidangan satuan beserta kategorinya
# (Les Entrées, Les Plats, Les Fromages, Les Desserts).
# Nama hidangan dilindungi (protected_spans) agar tidak teranotasi ganda oleh glosarium.
class ALaCarteHandler(BaseHandler):
    def handle(
        self,
        analysis: Analysis,
        repo: Repository,
        snapshot: NluSnapshot,
    ) -> HandlerResult:
        grouped = repo.get_menu_items_grouped_by_category()
        if not grouped:
            return HandlerResult(is_empty=True)

        items = [item for category_items in grouped.values() for item in category_items]
        protected = [item["nama"] for item in items]

        return HandlerResult(
            content=items,
            protected_spans=protected,
        )
