"""
Handler untuk intent Fallback sesuai PRD R10 dan System Design Bagian 6.6.
Menyusun baris tebakan jika skor teratas >= rho, serta tombol saran kanonik.
"""

from __future__ import annotations

from app.data.repository import Repository
from app.engine.handlers.base import BaseHandler, HandlerResult
from app.engine.snapshot import NluSnapshot
from app.engine.types import Analysis


# --- Handler Intent Fallback (PRD R10) ---
# Menyusun respons bantuan saat pesan pengguna di luar topik atau skor di bawah ambang:
# 1. Baris tebakan ("Mungkin maksud Anda...?") jika ada intent dengan skor >= rho (0.15).
# 2. Tombol saran topik info lainnya (chips kanonik) yang dapat diklik pengguna tanpa membuat flow percakapan.
class FallbackHandler(BaseHandler):
    def handle(
        self,
        analysis: Analysis,
        repo: Repository,
        snapshot: NluSnapshot,
    ) -> HandlerResult:
        tebakan_ranking = analysis.decision.tebakan
        tebakan_line = ""
        suggestions: list[dict[str, str]] = []

        # 1. Tebakan "Mungkin maksud Anda: {intent}?"
        if tebakan_ranking:
            intent_data = snapshot.intents.get(tebakan_ranking.intent)
            if intent_data:
                intent_display = intent_data.nama
                tmpl_tebakan = snapshot.fixed_text.get("tebakan", "Mungkin maksud Anda: {intent}?")
                tebakan_line = "\n" + tmpl_tebakan.format(intent=intent_display)
                if intent_data.frasa_kanonik:
                    suggestions.append({
                        "kode": intent_data.kode,
                        "label": intent_data.nama,
                        "frasa": intent_data.frasa_kanonik,
                    })

        # 2. Tombol saran intent info lainnya
        exclude_kode = tebakan_ranking.intent if tebakan_ranking else None
        other_suggestions = repo.get_info_suggestions(exclude_kode=exclude_kode)
        suggestions.extend(other_suggestions)

        jelajah_text = snapshot.fixed_text.get("jelajah", "Anda juga dapat menelusuri informasi berikut:")
        content_parts = []
        if tebakan_line:
            content_parts.append(tebakan_line)
        content_parts.append(f"\n{jelajah_text}")

        return HandlerResult(
            content="\n".join(content_parts),
            suggestions=suggestions,
        )
