"""
Unit tests untuk integritas data seed dan basis data SQLite (Fase 0).
Memverifikasi kepatuhan terhadap PRD v0.3 dan System Design Bagian 5 & 13.
"""

from __future__ import annotations

import csv
import json
import sqlite3
from pathlib import Path

from scripts.validate_seed import validate_seed


def test_seed_validation_rules(seed_dir: Path) -> None:
    """Memastikan skrip validate_seed tidak menghasilkan kesalahan apa pun."""
    errors = validate_seed(seed_dir)
    assert errors == [], f"Validasi seed menemukan kesalahan: {errors}"


def test_database_table_counts_and_constraints(temp_db: sqlite3.Connection) -> None:
    """Memastikan semua tabel terisi sesuai data seed awal (v1)."""
    cur = temp_db.cursor()

    # Periksa 11 intent
    cur.execute("SELECT COUNT(*) FROM intent;")
    assert cur.fetchone()[0] == 11

    # Periksa tepat 33 response templates (3 template x 11 intent)
    cur.execute("SELECT COUNT(*) FROM response_template;")
    assert cur.fetchone()[0] == 33

    # Periksa setiap intent memiliki tepat 3 template
    cur.execute("""
        SELECT i.kode, COUNT(t.id)
        FROM intent i
        JOIN response_template t ON t.intent_id = i.id
        GROUP BY i.id;
    """)
    template_counts = cur.fetchall()
    assert len(template_counts) == 11
    for kode, count in template_counts:
        assert count == 3, f"Intent {kode} memiliki {count} template (harus 3)"

    # Periksa placeholder {daftar} pada intent info dan ketiadaannya pada sosial/fallback
    cur.execute("""
        SELECT i.kode, i.jenis, t.isi
        FROM intent i
        JOIN response_template t ON t.intent_id = i.id;
    """)
    for kode, jenis, isi in cur.fetchall():
        if jenis == "info":
            assert "{daftar}" in isi, f"Template info '{kode}' harus memuat {{daftar}}: {isi}"
            assert isi.count("{daftar}") == 1, f"Template info '{kode}' harus memuat tepat satu {{daftar}}: {isi}"
        else:
            assert "{daftar}" not in isi, f"Template {jenis} '{kode}' tidak boleh memuat {{daftar}}: {isi}"

    # Periksa 15 hidangan dan 4 kategori
    cur.execute("SELECT COUNT(*) FROM menu_item;")
    assert cur.fetchone()[0] == 15

    cur.execute("SELECT COUNT(*) FROM menu_category;")
    assert cur.fetchone()[0] == 4

    # Periksa harga seluruh hidangan adalah integer > 0
    cur.execute("SELECT nama, harga FROM menu_item WHERE harga <= 0;")
    assert cur.fetchall() == []

    # Periksa 3 paket (2 Prix Fixe, 1 Carte Blanche) dan deskripsinya
    cur.execute("SELECT tipe, COUNT(*) FROM menu_package GROUP BY tipe;")
    pkg_counts = dict(cur.fetchall())
    assert pkg_counts.get("prix_fixe") == 2
    assert pkg_counts.get("carte_blanche") == 1

    cur.execute("SELECT nama, deskripsi FROM menu_package WHERE deskripsi IS NULL OR TRIM(deskripsi) = '';")
    assert cur.fetchall() == [], "Semua paket harus memiliki deskripsi konsep & pengalaman rasa"

    # Periksa urutan sajian paket berurutan tanpa celah (1..n)
    cur.execute("""
        SELECT package_id, GROUP_CONCAT(urutan, ',')
        FROM menu_package_item
        GROUP BY package_id;
    """)
    for pkg_id, urutan_str in cur.fetchall():
        orders = [int(x) for x in urutan_str.split(",")]
        assert orders == list(range(1, len(orders) + 1)), f"Urutan paket {pkg_id} tidak urut: {orders}"

    # Periksa pairing dan minuman non-alkohol
    cur.execute("SELECT COUNT(*) FROM beverage WHERE jenis = 'non_alkohol';")
    assert cur.fetchone()[0] >= 1

    cur.execute("""
        SELECT COUNT(DISTINCT p.beverage_id)
        FROM pairing p
        JOIN beverage b ON b.id = p.beverage_id
        WHERE b.jenis = 'non_alkohol';
    """)
    assert cur.fetchone()[0] >= 1, "Minuman non-alkohol harus terpakai dalam pairing"

    # Periksa info reservasi terurut 1..n
    cur.execute("SELECT urutan FROM reservation_info ORDER BY urutan;")
    res_orders = [row[0] for row in cur.fetchall()]
    assert res_orders == list(range(1, len(res_orders) + 1))


def test_evaluation_testset_format_and_splits(project_root: Path) -> None:
    """Memastikan testset.csv memenuhi spesifikasi PRD R8."""
    testset_path = project_root / "eval" / "testset.csv"
    assert testset_path.is_file(), "File eval/testset.csv tidak ditemukan"

    with open(testset_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert len(rows) == 230, f"Total kalimat uji harus 230 (ditemukan {len(rows)})"

    intent_counts: dict[str, int] = {}
    split_counts: dict[str, int] = {}
    tags: set[str] = set()

    for r in rows:
        intent = r["intent"]
        split = r["split"]
        tag = r["tag"]
        sentence = r["kalimat"].strip()

        assert sentence, "Kalimat uji tidak boleh kosong"
        intent_counts[intent] = intent_counts.get(intent, 0) + 1
        split_counts[split] = split_counts.get(split, 0) + 1
        tags.add(tag)

    # 10 intent dievaluasi masing-masing tepat 20 kalimat
    expected_intents = [
        "sapaan", "reservasi", "carte_blanche", "a_la_carte", "prix_fixe",
        "teknik", "diet", "harga", "pairing", "penutup"
    ]
    for it in expected_intents:
        assert intent_counts.get(it) == 20, f"Intent {it} harus memiliki 20 kalimat uji (ditemukan {intent_counts.get(it)})"

    # Fallback memiliki 30 kalimat out-of-scope
    assert intent_counts.get("fallback") == 30, f"Fallback harus memiliki 30 kalimat uji (ditemukan {intent_counts.get('fallback')})"

    # Split 70% tuning dan 30% heldout
    assert split_counts.get("tuning") == 161, f"Tuning split harus 161 baris (ditemukan {split_counts.get('tuning')})"
    assert split_counts.get("heldout") == 69, f"Heldout split harus 69 baris (ditemukan {split_counts.get('heldout')})"

    # Tag harus mencakup variasi
    assert {"formal", "informal", "typo", "multi", "oos"}.issubset(tags)
