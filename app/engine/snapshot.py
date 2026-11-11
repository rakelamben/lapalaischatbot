"""
NluSnapshot: Memuat seluruh data konfigurasi dan pola NLU ke memori sekali saat start.
Dapat dimuat dari file seed/ (untuk evaluasi/tuning mandiri) atau dari SQLite DB.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from app.engine.normalize import TextNormalizer
from app.engine.types import IntentData, Pattern


@dataclass
class NluSnapshot:
    intents: dict[str, IntentData]  # kode -> IntentData
    normalizer: TextNormalizer
    token_weights: dict[str, int]
    fixed_text: dict[str, str]
    glossary: list[dict[str, str]]
    diet_codes: tuple[str, ...]

    # --- Pemuatan Snapshot Mandiri dari File Seed JSON ---
    # Digunakan oleh skrip pengujian (pytest), evaluasi held-out (evaluate.py), dan grid search (tune.py)
    # sehingga engine dapat dijalankan secara instan dan deterministik tanpa memerlukan koneksi database SQLite.
    @classmethod
    def from_seed_dir(cls, seed_dir: Path | str) -> NluSnapshot:
        seed_path = Path(seed_dir)

        # 1. Baca seluruh file JSON sumber kebenaran
        with open(seed_path / "lexicon.json", "r", encoding="utf-8") as f:
            lexicon_data = json.load(f)
        with open(seed_path / "glossary.json", "r", encoding="utf-8") as f:
            glossary_data = json.load(f)
        with open(seed_path / "fixed_text.json", "r", encoding="utf-8") as f:
            fixed_text = json.load(f)
        with open(seed_path / "intents.json", "r", encoding="utf-8") as f:
            intents_data = json.load(f)
        with open(seed_path / "menu.json", "r", encoding="utf-8") as f:
            menu_data = json.load(f)

        stopwords = set(lexicon_data.get("stopword", []))
        synonyms = lexicon_data.get("sinonim", {})
        token_weights = lexicon_data.get("token_weight", {})
        glossary_items = glossary_data.get("istilah", [])
        multiword_phrases = [it["istilah"] for it in glossary_items]

        # 2. Inisialisasi normalizer leksikon
        normalizer = TextNormalizer(
            stopwords=stopwords,
            synonyms=synonyms,
            multiword_phrases=multiword_phrases,
        )

        # 3. Pra-proses pola intent dan template respons ke memori
        intents: dict[str, IntentData] = {}
        intent_id_counter = 1
        template_id_counter = 1

        for it in intents_data.get("intents", []):
            kode = it["kode"]
            nama = it["nama"]
            jenis = it["jenis"]
            frasa_kanonik = it.get("frasa_kanonik")

            patterns: list[Pattern] = []
            for p_str in it.get("pola", []):
                norm_p = normalizer.normalize(p_str)
                # Bobot per token pola: ambil dari token_weights atau default 2
                w_map = {tok: token_weights.get(tok, 2) for tok in norm_p.score_tokens}
                patterns.append(Pattern(raw=p_str, tokens=norm_p.score_tokens, weights=w_map))

            templates: list[tuple[int, str]] = []
            for tmpl in it.get("template", []):
                templates.append((template_id_counter, tmpl))
                template_id_counter += 1

            intents[kode] = IntentData(
                id=intent_id_counter,
                kode=kode,
                nama=nama,
                jenis=jenis,
                frasa_kanonik=frasa_kanonik,
                patterns=patterns,
                templates=templates,
            )
            intent_id_counter += 1

        diet_codes = tuple(dl["kode"] for dl in menu_data.get("label_diet", []))

        return cls(
            intents=intents,
            normalizer=normalizer,
            token_weights=token_weights,
            fixed_text=fixed_text,
            glossary=glossary_items,
            diet_codes=diet_codes,
        )

    # --- Pemuatan Snapshot dari Database SQLite ---
    # Digunakan saat server Flask atau service aplikasi dinyalakan, memuat tabel-tabel NLU
    # ke dalam cache memori satu kali saat proses startup.
    @classmethod
    def from_db(cls, conn: sqlite3.Connection) -> NluSnapshot:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # 1. Stopwords
        cur.execute("SELECT kata FROM stopword;")
        stopwords = {r["kata"] for r in cur.fetchall()}

        # 2. Synonyms
        cur.execute("SELECT varian, kanonik FROM synonym;")
        synonyms = {r["varian"]: r["kanonik"] for r in cur.fetchall()}

        # 3. Token weights
        cur.execute("SELECT token, bobot FROM token_weight;")
        token_weights = {r["token"]: r["bobot"] for r in cur.fetchall()}

        # 4. Glossary
        cur.execute("SELECT istilah, makna, jenis FROM glossary_term;")
        glossary_items = [dict(r) for r in cur.fetchall()]
        multiword_phrases = [it["istilah"] for it in glossary_items]

        normalizer = TextNormalizer(
            stopwords=stopwords,
            synonyms=synonyms,
            multiword_phrases=multiword_phrases,
        )

        # 5. Fixed text
        cur.execute("SELECT kunci, isi FROM fixed_text;")
        fixed_text = {r["kunci"]: r["isi"] for r in cur.fetchall()}

        # 6. Intents, patterns, templates
        cur.execute("SELECT id, kode, nama, jenis, frasa_kanonik FROM intent ORDER BY id ASC;")
        intent_rows = cur.fetchall()

        intents: dict[str, IntentData] = {}
        for i_row in intent_rows:
            i_id = i_row["id"]
            kode = i_row["kode"]

            # Patterns
            cur.execute("SELECT pola FROM intent_pattern WHERE intent_id = ?;", (i_id,))
            patterns: list[Pattern] = []
            for p_row in cur.fetchall():
                p_str = p_row["pola"]
                norm_p = normalizer.normalize(p_str)
                w_map = {tok: token_weights.get(tok, 2) for tok in norm_p.score_tokens}
                patterns.append(Pattern(raw=p_str, tokens=norm_p.score_tokens, weights=w_map))

            # Templates
            cur.execute("SELECT id, isi FROM response_template WHERE intent_id = ? ORDER BY id ASC;", (i_id,))
            templates = [(t_row["id"], t_row["isi"]) for t_row in cur.fetchall()]

            intents[kode] = IntentData(
                id=i_id,
                kode=kode,
                nama=i_row["nama"],
                jenis=i_row["jenis"],
                frasa_kanonik=i_row["frasa_kanonik"],
                patterns=patterns,
                templates=templates,
            )

        # 7. Diet codes
        cur.execute("SELECT kode FROM diet_label ORDER BY id ASC;")
        diet_codes = tuple(r["kode"] for r in cur.fetchall())

        return cls(
            intents=intents,
            normalizer=normalizer,
            token_weights=token_weights,
            fixed_text=fixed_text,
            glossary=glossary_items,
            diet_codes=diet_codes,
        )
