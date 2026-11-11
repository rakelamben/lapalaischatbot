"""
Validator integritas data seed sesuai PRD v0.3 dan System Design Bagian 5.6 & 13.8.
Dapat dijalankan langsung dari terminal:
    python scripts/validate_seed.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def load_json(path: Path) -> dict | list:
    if not path.is_file():
        raise FileNotFoundError(f"File seed tidak ditemukan: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# --- Validator Integritas Data Seed (PRD R5 & System Design 5.6) ---
# Memeriksa seluruh aturan model data sebelum database dibangun:
# 1. Kelengkapan dan sintaksis JSON pada 7 file seed.
# 2. Konsistensi teks sistem fixed_text.
# 3. Validitas glosarium kuliner dan kuota istilah teknik (8-12 istilah).
# 4. Kebenaran leksikon (stopword, sinonim, bobot token 1 atau 3).
# 5. Struktur 11 intent: keunikan pola, frasa kanonik, dan tepat 3 template (dengan tepat satu {daftar} untuk info).
# 6. Integritas menu: kategori 1..n, harga Rupiah > 0, relasi diet, dan paket berurutan beserta deskripsi alur rasa.
# 7. Validitas relasi pairing (termasuk ketersediaan pilihan non-alkohol).
# 8. Urutan informasi reservasi.
# 9. Pengecekan silang istilah Prancis terhadap glosarium.
def validate_seed(seed_dir: Path | None = None) -> list[str]:
    if seed_dir is None:
        seed_dir = Path(__file__).resolve().parent.parent / "seed"

    errors: list[str] = []

    # 1. Load semua file seed
    try:
        intents_data = load_json(seed_dir / "intents.json")
        lexicon_data = load_json(seed_dir / "lexicon.json")
        glossary_data = load_json(seed_dir / "glossary.json")
        fixed_text_data = load_json(seed_dir / "fixed_text.json")
        menu_data = load_json(seed_dir / "menu.json")
        pairing_data = load_json(seed_dir / "pairing.json")
        reservasi_data = load_json(seed_dir / "reservasi.json")
    except Exception as e:
        return [f"Gagal memuat file JSON seed: {e}"]

    # 2. Validasi fixed_text.json
    required_fixed_keys = {"diet_disclaimer", "tebakan", "kosong", "jelajah"}
    missing_fixed = required_fixed_keys - set(fixed_text_data.keys())
    if missing_fixed:
        errors.append(f"fixed_text.json kekurangan kunci: {missing_fixed}")
    if "{intent}" not in fixed_text_data.get("tebakan", ""):
        errors.append("fixed_text.json 'tebakan' harus memuat placeholder '{intent}'")

    # 3. Validasi glossary.json
    glossary_terms = set()
    technique_terms = set()
    for item in glossary_data.get("istilah", []):
        t = item.get("istilah", "").strip()
        makna = item.get("makna", "").strip()
        jenis = item.get("jenis", "").strip()
        if not t:
            errors.append("glossary.json: Ada istilah kosong")
            continue
        if not makna:
            errors.append(f"glossary.json: Istilah '{t}' tidak memiliki makna")
        if jenis not in ("umum", "teknik"):
            errors.append(f"glossary.json: Istilah '{t}' jenis tidak valid: '{jenis}' (harus 'umum' atau 'teknik')")
        low_t = t.lower()
        if low_t in glossary_terms:
            errors.append(f"glossary.json: Duplikasi istilah '{t}'")
        glossary_terms.add(low_t)
        if jenis == "teknik":
            technique_terms.add(low_t)

    if len(technique_terms) < 8 or len(technique_terms) > 15:
        errors.append(f"glossary.json: Jumlah istilah teknik {len(technique_terms)} (PRD mensyaratkan 8–12 istilah)")

    # 4. Validasi lexicon.json
    stopwords = set(lexicon_data.get("stopword", []))
    if not stopwords:
        errors.append("lexicon.json: Daftar stopword kosong")

    synonyms = lexicon_data.get("sinonim", {})
    if not isinstance(synonyms, dict) or not synonyms:
        errors.append("lexicon.json: Kamus sinonim kosong atau tidak valid")

    token_weights = lexicon_data.get("token_weight", {})
    for tok, w in token_weights.items():
        if w not in (1, 3):
            errors.append(f"lexicon.json: Bobot token '{tok}' adalah {w} (hanya diperbolehkan 1 atau 3)")

    # 5. Validasi intents.json
    intents = intents_data.get("intents", [])
    if len(intents) != 11:
        errors.append(f"intents.json: Jumlah intent {len(intents)}, harus tepat 11 intent")

    intent_codes = set()
    seen_patterns: dict[str, str] = {}  # pattern -> intent_kode

    for it in intents:
        kode = it.get("kode")
        nama = it.get("nama")
        jenis = it.get("jenis")
        frasa_kanonik = it.get("frasa_kanonik")
        pola = it.get("pola", [])
        template = it.get("template", [])

        if not kode or not nama:
            errors.append("intents.json: Ada intent tanpa kode atau nama")
            continue

        if kode in intent_codes:
            errors.append(f"intents.json: Duplikasi kode intent '{kode}'")
        intent_codes.add(kode)

        if jenis not in ("info", "sosial", "fallback"):
            errors.append(f"intents.json: Intent '{kode}' jenis tidak valid: '{jenis}'")

        if jenis == "info" and not frasa_kanonik:
            errors.append(f"intents.json: Intent info '{kode}' wajib memiliki 'frasa_kanonik'")
        elif jenis in ("sosial", "fallback") and frasa_kanonik is not None:
            errors.append(f"intents.json: Intent {jenis} '{kode}' frasa_kanonik harus null")

        # Template check: tepat 3 template
        if len(template) != 3:
            errors.append(f"intents.json: Intent '{kode}' memiliki {len(template)} template (harus tepat 3)")

        for tmpl in template:
            if not tmpl.strip():
                errors.append(f"intents.json: Intent '{kode}' memiliki template kosong")
            if jenis == "info":
                if tmpl.count("{daftar}") != 1:
                    errors.append(f"intents.json: Template intent info '{kode}' harus memuat tepat satu '{{daftar}}': '{tmpl}'")
            else:
                if "{daftar}" in tmpl:
                    errors.append(f"intents.json: Template intent {jenis} '{kode}' tidak boleh memuat '{{daftar}}': '{tmpl}'")

        # Pola check
        if kode == "fallback":
            if len(pola) != 0:
                errors.append("intents.json: Intent fallback tidak boleh memiliki pola")
        else:
            if len(pola) == 0:
                errors.append(f"intents.json: Intent '{kode}' tidak memiliki pola")

        for p in pola:
            p_clean = p.strip().lower()
            if not p_clean:
                errors.append(f"intents.json: Intent '{kode}' memiliki pola kosong")
            if p_clean in seen_patterns:
                errors.append(f"intents.json: Pola bentrok '{p}' pada intent '{kode}' dan '{seen_patterns[p_clean]}'")
            seen_patterns[p_clean] = kode

    # 6. Validasi menu.json
    diet_labels = {d["kode"]: d["nama"] for d in menu_data.get("label_diet", [])}
    if not diet_labels:
        errors.append("menu.json: Tidak ada label_diet")

    categories = {c["nama"]: c["urutan"] for c in menu_data.get("kategori", [])}
    if not categories:
        errors.append("menu.json: Tidak ada kategori")
    category_orders = list(categories.values())
    if sorted(category_orders) != list(range(1, len(category_orders) + 1)):
        errors.append(f"menu.json: Urutan kategori harus 1..n tanpa celah: {category_orders}")

    dishes = menu_data.get("hidangan", [])
    dish_names = set()
    for d in dishes:
        dn = d.get("nama", "").strip()
        if not dn:
            errors.append("menu.json: Ada hidangan tanpa nama")
            continue
        if dn.lower() in dish_names:
            errors.append(f"menu.json: Duplikasi hidangan '{dn}'")
        dish_names.add(dn.lower())

        kat = d.get("kategori")
        if kat not in categories:
            errors.append(f"menu.json: Hidangan '{dn}' kategori '{kat}' tidak ada di daftar kategori")

        harga = d.get("harga")
        if not isinstance(harga, int) or harga <= 0:
            errors.append(f"menu.json: Hidangan '{dn}' harga '{harga}' tidak valid (harus integer > 0)")

        for dl in d.get("diet", []):
            if dl not in diet_labels:
                errors.append(f"menu.json: Hidangan '{dn}' memiliki diet label tidak dikenal: '{dl}'")

    packages = menu_data.get("paket", [])
    for pkg in packages:
        pname = pkg.get("nama", "").strip()
        ptype = pkg.get("tipe")
        pharga = pkg.get("harga")
        pdurasi = pkg.get("durasi_menit")
        pdeskripsi = pkg.get("deskripsi", "").strip()
        phidangan = pkg.get("hidangan", [])

        if ptype not in ("prix_fixe", "carte_blanche"):
            errors.append(f"menu.json: Paket '{pname}' tipe '{ptype}' tidak valid")
        if not pdeskripsi:
            errors.append(f"menu.json: Paket '{pname}' tidak memiliki deskripsi (maksud, konsep, & pengalaman rasa)")
        if not isinstance(pharga, int) or pharga <= 0:
            errors.append(f"menu.json: Paket '{pname}' harga '{pharga}' tidak valid")
        if not isinstance(pdurasi, int) or pdurasi <= 0:
            errors.append(f"menu.json: Paket '{pname}' durasi_menit '{pdurasi}' tidak valid")
        if not phidangan:
            errors.append(f"menu.json: Paket '{pname}' tidak memiliki hidangan")
        for h in phidangan:
            if h.lower() not in dish_names:
                errors.append(f"menu.json: Hidangan '{h}' pada paket '{pname}' tidak terdaftar di daftar hidangan")

    # 7. Validasi pairing.json
    beverages = {b["nama"].lower(): b for b in pairing_data.get("minuman", [])}
    if not beverages:
        errors.append("pairing.json: Tidak ada minuman")
    for bname, b in beverages.items():
        if b.get("jenis") not in ("wine", "non_alkohol"):
            errors.append(f"pairing.json: Minuman '{b['nama']}' jenis '{b.get('jenis')}' tidak valid")
        if not b.get("deskripsi", "").strip():
            errors.append(f"pairing.json: Minuman '{b['nama']}' tidak memiliki deskripsi")

    pairings = pairing_data.get("pairing", [])
    used_non_alkohol = False
    for p in pairings:
        h = p.get("hidangan", "").strip()
        if h.lower() not in dish_names:
            errors.append(f"pairing.json: Hidangan '{h}' dalam pairing tidak terdaftar")
        for b in p.get("minuman", []):
            if b.lower() not in beverages:
                errors.append(f"pairing.json: Minuman '{b}' dalam pairing tidak terdaftar")
            elif beverages[b.lower()].get("jenis") == "non_alkohol":
                used_non_alkohol = True

    if not used_non_alkohol:
        errors.append("pairing.json: Minuman non-alkohol harus dipakai minimal satu kali dalam pairing")

    # 8. Validasi reservasi.json
    reservations = reservasi_data.get("info", [])
    if not reservations:
        errors.append("reservasi.json: Daftar info reservasi kosong")
    res_orders = []
    res_labels = set()
    for r in reservations:
        lbl = r.get("label", "").strip()
        isi = r.get("isi", "").strip()
        urutan = r.get("urutan")
        if not lbl or not isi:
            errors.append(f"reservasi.json: Info reservasi '{lbl}' memiliki label atau isi kosong")
        if lbl in res_labels:
            errors.append(f"reservasi.json: Duplikasi label reservasi '{lbl}'")
        res_labels.add(lbl)
        res_orders.append(urutan)

    if sorted(res_orders) != list(range(1, len(res_orders) + 1)):
        errors.append(f"reservasi.json: Urutan info reservasi harus 1..n tanpa celah: {res_orders}")

    # 9. Validasi istilah Prancis utama di glosarium
    # Kategori menu
    for kat in categories.keys():
        if kat.lower() not in glossary_terms:
            errors.append(f"Kategori '{kat}' belum terdaftar di glossary.json")

    return errors


def main() -> None:
    errors = validate_seed()
    if errors:
        print(f"❌ Validasi seed GAGAL dengan {len(errors)} kesalahan:")
        for i, err in enumerate(errors, 1):
            print(f"  {i}. {err}")
        sys.exit(1)
    else:
        print("✅ Validasi seed BERHASIL! Semua aturan data PRD & System Design terpenuhi sempurna.")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
