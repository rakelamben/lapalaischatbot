"""
Unit test untuk modul ekstraksi entitas (app/engine/entities.py).
Memverifikasi kepatuhan terhadap PRD R4.
"""

from __future__ import annotations

from pathlib import Path

from app.engine.entities import extract_entities
from app.engine.params import EngineParams
from app.engine.snapshot import NluSnapshot


def get_snapshot() -> NluSnapshot:
    seed_dir = Path(__file__).resolve().parent.parent.parent / "seed"
    return NluSnapshot.from_seed_dir(seed_dir)


def test_prd_r4_acceptance_criteria() -> None:
    snapshot = get_snapshot()
    params = EngineParams()

    # Given pesan "menu di bawah 1,2 juta" When diproses Then yang ditampilkan hanya menu berharga <= 1.200.000
    norm1 = snapshot.normalizer.normalize("menu di bawah 1,2 juta")
    ent1 = extract_entities(norm1, snapshot, params)
    assert ent1.harga is not None
    assert ent1.harga.nilai == 1200000
    assert ent1.harga.op == "le"

    # Given pesan "menu di atas 1.200.000" When diproses Then yang ditampilkan hanya menu berharga > 1.200.000
    norm2 = snapshot.normalizer.normalize("menu di atas 1.200.000")
    ent2 = extract_entities(norm2, snapshot, params)
    assert ent2.harga is not None
    assert ent2.harga.nilai == 1200000
    assert ent2.harga.op == "gt"

    # Given pesan "menu vegetarian di bawah 1,2 juta" When diproses Then hasil = irisan label vegetarian dan harga <= 1.200.000
    norm3 = snapshot.normalizer.normalize("menu vegetarian di bawah 1,2 juta")
    ent3 = extract_entities(norm3, snapshot, params)
    assert ent3.diet == ("vegetarian",)
    assert ent3.harga is not None
    assert ent3.harga.nilai == 1200000
    assert ent3.harga.op == "le"


def test_entity_direction_without_number() -> None:
    snapshot = get_snapshot()
    params = EngineParams(price_default_threshold=1200000)

    norm = snapshot.normalizer.normalize("menu murah terjangkau")
    ent = extract_entities(norm, snapshot, params)
    assert ent.harga is not None
    assert ent.harga.nilai == 1200000
    assert ent.harga.op == "le"
