"""
Script untuk membangun basis data SQLite (data/lapalais.db) dari seed JSON.
Dapat dijalankan:
    python scripts/seed.py [--reset] [--db-path PATH]
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path


def load_json(path: Path) -> dict | list:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_db(db_path: Path, seed_dir: Path, migrations_dir: Path, reset: bool = False) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)

    if reset and db_path.exists():
        print(f"Menghapus database lama: {db_path}")
        db_path.unlink()

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")

    # 1. Jalankan migrasi
    migration_file = migrations_dir / "001_init.sql"
    if not migration_file.is_file():
        raise FileNotFoundError(f"File migrasi tidak ditemukan: {migration_file}")

    print("Menerapkan skema SQL...")
    with open(migration_file, "r", encoding="utf-8") as f:
        schema_sql = f.read()
    conn.executescript(schema_sql)

    # 2. Muat data seed
    print("Memuat file seed JSON...")
    intents_data = load_json(seed_dir / "intents.json")
    lexicon_data = load_json(seed_dir / "lexicon.json")
    glossary_data = load_json(seed_dir / "glossary.json")
    fixed_text_data = load_json(seed_dir / "fixed_text.json")
    menu_data = load_json(seed_dir / "menu.json")
    pairing_data = load_json(seed_dir / "pairing.json")
    reservasi_data = load_json(seed_dir / "reservasi.json")

    cur = conn.cursor()

    # Bersihkan tabel jika tidak reset file
    if not reset:
        cur.executescript("""
            DELETE FROM chat_log;
            DELETE FROM pairing;
            DELETE FROM beverage;
            DELETE FROM menu_package_item;
            DELETE FROM menu_package;
            DELETE FROM menu_item_diet;
            DELETE FROM menu_item;
            DELETE FROM diet_label;
            DELETE FROM menu_category;
            DELETE FROM reservation_info;
            DELETE FROM glossary_term;
            DELETE FROM token_weight;
            DELETE FROM synonym;
            DELETE FROM stopword;
            DELETE FROM fixed_text;
            DELETE FROM response_template;
            DELETE FROM intent_pattern;
            DELETE FROM intent;
        """)

    # 3. Insert fixed_text
    print("Menyimpan fixed_text...")
    for k, v in fixed_text_data.items():
        cur.execute("INSERT OR REPLACE INTO fixed_text (kunci, isi) VALUES (?, ?)", (k, v))

    # 4. Insert glossary
    print("Menyimpan glossary_term...")
    for item in glossary_data.get("istilah", []):
        cur.execute(
            "INSERT INTO glossary_term (istilah, makna, jenis) VALUES (?, ?, ?)",
            (item["istilah"], item["makna"], item.get("jenis", "umum")),
        )

    # 5. Insert lexicon (stopword, synonym, token_weight)
    print("Menyimpan leksikon (stopword, synonym, token_weight)...")
    for sw in lexicon_data.get("stopword", []):
        cur.execute("INSERT OR IGNORE INTO stopword (kata) VALUES (?)", (sw,))

    for var, kanonik in lexicon_data.get("sinonim", {}).items():
        cur.execute("INSERT OR REPLACE INTO synonym (varian, kanonik) VALUES (?, ?)", (var, kanonik))

    for tok, w in lexicon_data.get("token_weight", {}).items():
        cur.execute("INSERT OR REPLACE INTO token_weight (token, bobot) VALUES (?, ?)", (tok, w))

    # 6. Insert intents, patterns, templates
    print("Menyimpan intents, pola, dan templates...")
    for it in intents_data.get("intents", []):
        cur.execute(
            "INSERT INTO intent (kode, nama, jenis, frasa_kanonik) VALUES (?, ?, ?, ?)",
            (it["kode"], it["nama"], it["jenis"], it.get("frasa_kanonik")),
        )
        intent_id = cur.lastrowid

        for p in it.get("pola", []):
            cur.execute("INSERT INTO intent_pattern (intent_id, pola) VALUES (?, ?)", (intent_id, p))

        for tmpl in it.get("template", []):
            cur.execute("INSERT INTO response_template (intent_id, isi) VALUES (?, ?)", (intent_id, tmpl))

    # 7. Insert menu (label_diet, menu_category, menu_item, menu_item_diet, paket)
    print("Menyimpan data menu dan paket...")
    diet_id_map: dict[str, int] = {}
    for dl in menu_data.get("label_diet", []):
        cur.execute("INSERT INTO diet_label (kode, nama) VALUES (?, ?)", (dl["kode"], dl["nama"]))
        diet_id_map[dl["kode"]] = cur.lastrowid

    category_id_map: dict[str, int] = {}
    for cat in menu_data.get("kategori", []):
        cur.execute("INSERT INTO menu_category (nama, urutan) VALUES (?, ?)", (cat["nama"], cat["urutan"]))
        category_id_map[cat["nama"]] = cur.lastrowid

    item_id_map: dict[str, int] = {}
    for h in menu_data.get("hidangan", []):
        cur.execute(
            "INSERT INTO menu_item (nama, deskripsi, kategori_id, harga) VALUES (?, ?, ?, ?)",
            (h["nama"], h["deskripsi"], category_id_map[h["kategori"]], h["harga"]),
        )
        item_id = cur.lastrowid
        item_id_map[h["nama"]] = item_id

        for dcode in h.get("diet", []):
            cur.execute(
                "INSERT INTO menu_item_diet (item_id, diet_id) VALUES (?, ?)",
                (item_id, diet_id_map[dcode]),
            )

    for pkg in menu_data.get("paket", []):
        cur.execute(
            "INSERT INTO menu_package (tipe, nama, deskripsi, harga, durasi_menit) VALUES (?, ?, ?, ?, ?)",
            (pkg["tipe"], pkg["nama"], pkg["deskripsi"], pkg["harga"], pkg["durasi_menit"]),
        )
        pkg_id = cur.lastrowid

        for idx, dish_name in enumerate(pkg.get("hidangan", []), start=1):
            cur.execute(
                "INSERT INTO menu_package_item (package_id, item_id, urutan) VALUES (?, ?, ?)",
                (pkg_id, item_id_map[dish_name], idx),
            )

    # 8. Insert pairing (beverage, pairing)
    print("Menyimpan beverage dan pairing...")
    beverage_id_map: dict[str, int] = {}
    for b in pairing_data.get("minuman", []):
        cur.execute(
            "INSERT INTO beverage (nama, deskripsi, jenis) VALUES (?, ?, ?)",
            (b["nama"], b["deskripsi"], b["jenis"]),
        )
        beverage_id_map[b["nama"]] = cur.lastrowid

    for pr in pairing_data.get("pairing", []):
        hidangan_id = item_id_map[pr["hidangan"]]
        for bname in pr.get("minuman", []):
            cur.execute(
                "INSERT INTO pairing (item_id, beverage_id) VALUES (?, ?)",
                (hidangan_id, beverage_id_map[bname]),
            )

    # 9. Insert reservasi
    print("Menyimpan reservation_info...")
    for r in reservasi_data.get("info", []):
        cur.execute(
            "INSERT INTO reservation_info (label, isi, urutan) VALUES (?, ?, ?)",
            (r["label"], r["isi"], r["urutan"]),
        )

    conn.commit()
    conn.close()
    print(f"✅ Seeding basis data selesai: {db_path}")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Seed database SQLite dari JSON.")
    parser.add_argument("--reset", action="store_true", help="Hapus DB lama jika ada sebelum mengisi ulang")
    parser.add_argument("--db-path", type=str, default=None, help="Lokasi database SQLite")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent
    db_path = Path(args.db_path) if args.db_path else project_root / "data" / "lapalais.db"
    seed_dir = project_root / "seed"
    migrations_dir = project_root / "migrations"

    build_db(db_path, seed_dir, migrations_dir, reset=args.reset)


if __name__ == "__main__":
    main()
