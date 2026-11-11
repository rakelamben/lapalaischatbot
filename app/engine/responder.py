"""
Generator respons NLU sesuai PRD R5, R6, R7, R10, dan R11.
Aturan:
  - Pemilihan template acak dari 3 variasi tanpa mengulang prev_template_id.
  - Pengembalian data handler terstruktur pada Reply.content.
  - Penambahan disclaimer diet/alergen otomatis (R7).
  - Anotasi glosarium istilah Prancis (R11) dengan proteksi span.
  - Penanganan kasus kosong dengan pesan baku (fixed_text['kosong']).
"""

from __future__ import annotations

import random
from typing import Any

from app.engine.glossary import GlossaryAnnotator
from app.engine.handlers.base import HandlerResult
from app.engine.snapshot import NluSnapshot
from app.engine.types import Analysis, Reply


class Responder:
    def __init__(self, snapshot: NluSnapshot) -> None:
        self.snapshot = snapshot
        self.glossary_annotator = GlossaryAnnotator(snapshot.glossary)

    # --- Pemilihan Template Non-Repetitif (PRD R6) ---
    # Memilih 1 template secara acak dari 3 variasi yang dimiliki intent terpilih.
    # Jika prev_template_id disertakan oleh klien dan cocok dengan salah satu template intent ini,
    # template tersebut dikeluarkan dari kandidat pemilihan sehingga bot tidak mengulang kalimat pembuka yang sama.
    def select_template(
        self,
        templates: list[tuple[int, str]],
        prev_template_id: int | None,
        rng: random.Random | None = None,
    ) -> tuple[int, str]:
        if not templates:
            return (0, "")

        candidate_pool = [t for t in templates if t[0] != prev_template_id]
        if not candidate_pool:
            candidate_pool = templates

        chooser = rng if rng is not None else random
        return chooser.choice(candidate_pool)

    # --- Orkestrasi Pembuatan Balasan Akhir ---
    # Tahap 1: Evaluasi kondisi kosong (jika filter menu tidak menemukan hidangan yang cocok).
    # Tahap 2: Pemilihan template kalimat non-repetitif.
    # Tahap 3: Simpan data handler terstruktur terpisah dari teks balasan.
    # Tahap 4: Injeksi disclaimer diet/alergen otomatis (PRD R7).
    # Tahap 5: Anotasi glosarium istilah Prancis dengan proteksi nama menu (PRD R11).
    def generate_reply(
        self,
        analysis: Analysis,
        handler_result: HandlerResult,
        prev_template_id: int | None = None,
        rng_seed: int | None = None,
    ) -> Reply:
        intent_code = analysis.decision.intent
        intent_data = self.snapshot.intents.get(intent_code)
        rng = random.Random(rng_seed) if rng_seed is not None else None

        # 1. Kasus Hasil Kosong (misal tidak ada menu yang cocok dengan kriteria filter)
        if handler_result.is_empty:
            empty_text = self.snapshot.fixed_text.get(
                "kosong",
                "Mohon maaf, belum ada menu yang cocok dengan kriteria tersebut.",
            )
            return Reply(
                text=empty_text,
                template_id=None,
                suggestions=[],
                analysis=analysis,
            )

        # 2. Pemilihan template
        templates = intent_data.templates if intent_data else []
        selected_id, selected_tmpl = self.select_template(templates, prev_template_id, rng=rng)

        # Remove {daftar}
        # 3. Render placeholder {daftar}
        if intent_data and intent_data.jenis == "info":
            if "{daftar}" in selected_tmpl:
                rendered = selected_tmpl.replace("{daftar}", "")
            else:
                rendered = selected_tmpl
        elif intent_code == "fallback":
            rendered = f"{selected_tmpl}\n{handler_result.content}"
        else:
            # Intent sosial
            rendered = selected_tmpl

        # 4. Injeksi Disclaimer Diet/Alergen (PRD R7)
        if intent_code == "diet" or (analysis.entities.diet and len(analysis.entities.diet) > 0):
            disclaimer = self.snapshot.fixed_text.get("diet_disclaimer", "")
            if disclaimer and disclaimer not in rendered:
                rendered = f"{rendered}\n\n{disclaimer}"

        # 5. Anotasi Glosarium Prancis (PRD R11)
        final_text = self.glossary_annotator.annotate(
            rendered,
            protected_spans=handler_result.protected_spans,
        )

        return Reply(
            text=final_text.strip(),
            template_id=selected_id,
            suggestions=handler_result.suggestions,
            analysis=analysis,
            content=handler_result.content,
        )
