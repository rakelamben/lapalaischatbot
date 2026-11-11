"""
Unit test untuk Repository SQL (app/data/repository.py).
"""

from __future__ import annotations

import json
import sqlite3

from app.data.repository import Repository


def test_repository_menu_filter(temp_db: sqlite3.Connection) -> None:
    repo = Repository(temp_db)

    # 1. Filter harga <= 1.200.000 (13 hidangan)
    items_le = repo.filter_menu_items(batas_le=1200000)
    assert len(items_le) == 13
    assert any(i["nama"] == "Filet de Boeuf Rossini" for i in items_le)

    # 2. Filter harga > 1.200.000 (2 hidangan: Bar Roti & Homard Thermidor)
    items_gt = repo.filter_menu_items(batas_gt=1200000)
    assert len(items_gt) == 2
    names_gt = {i["nama"] for i in items_gt}
    assert names_gt == {"Bar Rôti, Beurre Blanc", "Homard Thermidor"}

    # 3. Filter diet vegetarian (8 hidangan)
    items_veg = repo.filter_menu_items(diet_codes=["vegetarian"])
    assert len(items_veg) == 8

    # 4. Filter diet vegetarian + halal (irisan: 4 hidangan)
    items_veg_halal = repo.filter_menu_items(diet_codes=["vegetarian", "halal"])
    assert len(items_veg_halal) == 4
    names_vh = {i["nama"] for i in items_veg_halal}
    assert names_vh == {
        "Velouté de Champignons",
        "Risotto aux Truffes",
        "Tarte Tatin",
        "Crème Brûlée",
    }

    # 5. Filter vegetarian di bawah 1,2 juta (8 hidangan, karena semua menu vegetarian harganya <= 760.000)
    items_veg_budget = repo.filter_menu_items(batas_le=1200000, diet_codes=["vegetarian"])
    assert len(items_veg_budget) == 8


def test_repository_packages(temp_db: sqlite3.Connection) -> None:
    repo = Repository(temp_db)

    # Prix Fixe
    pf = repo.get_packages(tipe="prix_fixe")
    assert len(pf) == 2
    for p in pf:
        assert p["durasi_menit"] in (90, 120)
        assert len(p["deskripsi"]) > 20
        assert len(p["hidangan"]) >= 3

    # Carte Blanche
    cb = repo.get_packages(tipe="carte_blanche")
    assert len(cb) == 1
    assert cb[0]["nama"] == "Carte Blanche"
    assert cb[0]["durasi_menit"] == 150
    assert len(cb[0]["hidangan"]) == 5
    assert len(cb[0]["deskripsi"]) > 20


def test_repository_pairings_and_reservations(temp_db: sqlite3.Connection) -> None:
    repo = Repository(temp_db)

    pairings = repo.get_pairings()
    assert len(pairings) >= 15
    first_p = pairings[0]
    assert "hidangan" in first_p
    assert "minuman" in first_p
    assert "deskripsi_minuman" in first_p

    res_info = repo.get_reservation_info()
    assert len(res_info) == 6
    assert res_info[0]["label"] == "Jam operasional"


def test_repository_log_chat(temp_db: sqlite3.Connection) -> None:
    repo = Repository(temp_db)
    intent = repo.get_intent_by_code("sapaan")
    assert intent is not None

    log_id = repo.log_chat(
        pesan="halo",
        intent_id=intent["id"],
        skor_json=json.dumps({"sapaan": 1.0}),
        entitas_json=json.dumps({}),
    )
    assert log_id > 0

    cur = temp_db.cursor()
    cur.execute("SELECT pesan, intent_id, skor FROM chat_log WHERE id = ?;", (log_id,))
    row = cur.fetchone()
    assert row["pesan"] == "halo"
    assert row["intent_id"] == intent["id"]
