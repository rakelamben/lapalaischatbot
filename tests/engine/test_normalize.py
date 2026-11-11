"""
Unit test untuk modul normalisasi (app/engine/normalize.py).
Memverifikasi kepatuhan terhadap PRD R1.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.engine.normalize import TextNormalizer, extract_and_remove_number, remove_accents


def get_default_normalizer() -> TextNormalizer:
    seed_dir = Path(__file__).resolve().parent.parent.parent / "seed"
    with open(seed_dir / "lexicon.json", "r", encoding="utf-8") as f:
        lexicon = json.load(f)
    with open(seed_dir / "glossary.json", "r", encoding="utf-8") as f:
        glossary = json.load(f)

    stopwords = set(lexicon.get("stopword", []))
    synonyms = lexicon.get("sinonim", {})
    phrases = [item["istilah"] for item in glossary.get("istilah", [])]
    return TextNormalizer(stopwords=stopwords, synonyms=synonyms, multiword_phrases=phrases)


def test_remove_accents() -> None:
    assert remove_accents("Entrées") == "Entrees"
    assert remove_accents("poêlé") == "poele"
    assert remove_accents("dégustation") == "degustation"
    assert remove_accents("Crème Brûlée") == "Creme Brulee"


def test_number_extraction() -> None:
    text, num = extract_and_remove_number("menu di bawah 1,2 juta")
    assert num == 1200000
    assert "1,2" not in text

    text, num = extract_and_remove_number("di atas 1.200.000 rupiah")
    assert num == 1200000

    text, num = extract_and_remove_number("budget 500rb dong")
    assert num == 500000

    text, num = extract_and_remove_number("sekitar 2jt")
    assert num == 2000000

    text, num = extract_and_remove_number("menu tanpa angka")
    assert num is None


def test_prd_r1_acceptance_criteria() -> None:
    normalizer = get_default_normalizer()

    # Given pesan "Ada menu Entrées?" When diproses Then token mengandung "entrees" dan tidak mengandung "ada" sebagai kata kunci
    res1 = normalizer.normalize("Ada menu Entrées?")
    assert "entrees" in res1.clean_tokens
    assert "entrees" in res1.score_tokens
    assert "ada" in res1.clean_tokens
    assert "ada" not in res1.score_tokens
    assert "menu" in res1.score_tokens  # kata 'menu' tetap ada untuk scoring

    # Given pesan "di bawah 1,2 juta" When diproses Then angka terbaca 1200000
    res2 = normalizer.normalize("di bawah 1,2 juta")
    assert res2.extracted_number == 1200000
    assert "bawah" in res2.clean_tokens

    # Given pesan "Prix Fixe" atau "prix fixe" When diproses Then keduanya menjadi token yang sama
    res3a = normalizer.normalize("Prix Fixe")
    res3b = normalizer.normalize("prix fixe")
    assert "prix_fixe" in res3a.clean_tokens
    assert "prix_fixe" in res3b.clean_tokens
    assert res3a.score_tokens == res3b.score_tokens

    # Frasa tanpa seafood -> non_seafood
    res4 = normalizer.normalize("menu tanpa seafood dong")
    assert "non_seafood" in res4.clean_tokens
    assert "non_seafood" in res4.score_tokens
