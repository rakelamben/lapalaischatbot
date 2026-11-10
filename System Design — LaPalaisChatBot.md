# System Design — LaPalaisChatBot

**Rancangan teknis untuk PRD v0.3** · Pemilik: Jas · Draf v0.1 · 9 November 2026

> Ringkasan: LaPalaisChatBot dibangun sebagai satu aplikasi Flask bermodul dengan engine NLU rule-based berupa Python murni, konten di SQLite, dan antarmuka HTML/CSS/JS native dalam dua mode (client dan debug). Engine tidak mengimpor Flask maupun SQL, jadi bisa diuji, dituning, dan dievaluasi lewat skrip tanpa menjalankan server.

## 1. Keputusan arsitektur kunci

1. **Satu proses, tiga lapis.** Route Flask tipis → service → engine murni; data diambil lewat repository. Skala proyek (demo dan uji) tidak membutuhkan layanan terpisah.
2. **Server stateless.** Tidak ada sesi. Aturan “jangan ulang template” (R6) dipenuhi klien yang mengirim `prev_template_id`, sehingga prinsip tanpa flow tetap terjaga.
3. **Konten di SQLite, parameter engine di JSON.** Nilai τ, δ, ρ, dan bobot hidup di `config/engine.json` yang masuk git, jadi hasil tuning bisa direproduksi dan dibandingkan.
4. **Seed JSON adalah sumber kebenaran; SQLite dibangun darinya** oleh `scripts/seed.py`. Scraping nanti hanya menulis ke seed JSON dan harus lolos validasi aturan model data (5.6).
5. **Debug mode terpisah secara fisik.** Halaman `/debug` dan blueprint `/api/debug/*` hanya terdaftar jika `ENABLE_DEBUG=1`; endpoint client tidak pernah mengirim skor (OQ-6 PRD).
6. **Relasi, bukan kolom boolean.** Label diet, paket, dan pairing memakai tabel relasi, sehingga menambah label, paket, atau minuman cukup menambah baris tanpa migrasi skema.

## 2. Requirements

### 2.1 Peta kebutuhan PRD ke modul

| PRD | Modul | Catatan |
| --- | --- | --- |
| R1 Preprocessing | `engine/normalize.py` | Aksen, angka, frasa, stopword, sinonim |
| R2 Skor intent | `engine/scoring.py` | Jaccard, Fuzzy token, Cakupan berbobot; maks per pola |
| R3 Keputusan | `engine/decision.py` | τ, δ, ρ, aturan prioritas |
| R4 Entity | `engine/entities.py` + `repository.py` | Regex membaca pertanyaan; SQL memfilter data |
| R5 Sumber data tunggal | tabel SQLite + `seed/` | Template hanya berisi `{daftar}` |
| R6 Variasi | `engine/responder.py` | 3 template per intent, tidak mengulang |
| R7 Disclaimer | `engine/handlers/` | Ditambahkan di luar template, tidak bisa terlewat |
| R8 Evaluator | `scripts/evaluate.py`, `tune.py`, `eval/testset.csv` | Ablation dan grid search |
| R9 Antarmuka | `web/`, `app/pages.py` | Flask + HTML/CSS/JS modular |
| R10 Fallback | `engine/handlers/` | Tebakan + tombol kanonik |
| R11 Glosarium | `engine/responder.py` | Anotasi makna setiap kemunculan istilah |
| P1 Debug dan log | `app/api/debug.py`, tabel `chat_log` | Peringkat intent hanya di debug |

### 2.2 Non-fungsional

| Aspek | Target | Cara memenuhi |
| --- | --- | --- |
| Latensi | < 100 ms di server; < 1 s di klien | Cache NLU di memori, kueri SQL ber-indeks |
| Determinisme | Pesan sama → skor sama | Tanpa acak di engine; acak hanya di pemilihan template dan bisa di-seed |
| Reproduksibilitas | Evaluasi bisa diulang | Parameter di git, seed tetap, set uji CSV |
| Keamanan | Tanpa XSS dan SQL injection | `textContent` di klien, SQL parametrik, pesan ≤ 500 karakter, debug mati secara default |
| Kemudahan ubah | Tambah menu, label, intent tanpa ubah inti | Handler per intent, data relasional |
| Teruji | Semua kriteria penerimaan PRD jadi tes otomatis | pytest dan golden tests (bagian 9) |

**Estimasi beban.** 11 intent × ±12 pola ≈ 130 pola; pesan ±6 token menghasilkan ±2.500 perbandingan `SequenceMatcher`, yaitu beberapa milidetik. Tidak perlu antrean, cache hasil, atau scaling horizontal.

## 3. Tech stack dan rekomendasi

| Lapisan | Pilihan | Alasan |
| --- | --- | --- |
| Runtime | Python 3.11+ | `difflib`, `unicodedata`, `sqlite3` sudah bawaan |
| Backend | Flask 3, app factory + Blueprint | Sesuai pilihanmu; blueprint memisahkan client dan debug |
| Engine NLU | Python murni: `difflib.SequenceMatcher`, `unicodedata`, `re`; tanpa library NLP atau ML | Sesuai non-goals PRD; deterministik, bisa dijelaskan, dan bisa dijalankan dari skrip evaluasi tanpa Flask |
| Frontend | HTML + CSS + ES Modules (`type=module`), tanpa bundler | Sesuai pilihanmu; modul native cukup untuk skala ini |
| Database | SQLite via `sqlite3` bawaan, tanpa ORM; `foreign_keys=ON`, mode WAL, `busy_timeout` | Skema kecil; ORM menambah dependensi tanpa manfaat |
| Migrasi | File SQL bernomor + `PRAGMA user_version` | Cukup untuk satu pengembang, tanpa Alembic |
| Seed dan validasi | JSON + `scripts/seed.py` + `scripts/validate_seed.py` | Diff mudah dibaca di git |
| Tes | pytest + Flask test client | Standar |
| Evaluasi dan tuning | `scripts/evaluate.py`, `tune.py`; numpy dan matplotlib (dev saja) | Grid search cepat dan plot distribusi skor (R8) |
| Server (opsional) | gunicorn 2 worker | WAL SQLite aman untuk beban ini |

Dependensi runtime hanya **Flask**. numpy, matplotlib, dan pytest hanya untuk pengembangan.

### Catatan tentang komponen 21st.dev

Komponen “Ai Assistant” (MIT) dibangun dengan React, Tailwind, dan lucide-react, jadi **tidak bisa dipakai langsung** di stack native. Halaman komponen hanya menampilkan deskripsi dan contoh pemakaian; kode sumbernya baru terbuka dengan akun gratis, sehingga rancangan ini mengambil *perilaku dan gaya* dari deskripsinya, bukan implementasinya: latar gradien, kolom input pesan, indikator mengetik, animasi pesan muncul, tombol hapus riwayat, dan tata letak responsif. Semuanya ditulis ulang dengan CSS variables, `@keyframes`, dan fungsi DOM biasa; ikon memakai SVG inline (mis. send dan trash dari set lucide).

## 4. Arsitektur

```text
 Browser: Client mode (/)   ·   Debug mode (/debug)
   HTML + CSS + JS modules
        │ POST /api/chat          │ POST /api/debug/chat
        ▼                         ▼
 ┌──────────────── Flask app (create_app) ─────────────────┐
 │  pages   │  api/chat  │  api/debug (jika ENABLE_DEBUG)   │
 │                 ▼                                       │
 │            ChatService                                  │
 │  ┌── Engine (Python murni, tanpa Flask/SQL) ─────────┐  │
 │  │ normalize → score → decide → entities → respond   │  │
 │  └───────────────────────┬───────────────────────────┘  │
 │  NluSnapshot (cache)  ◄──┤──►  Repository (SQL parametrik)│
 └──────────────────────────┼──────────────────────────────┘
                            ▼
                  SQLite: data/lapalais.db
```

**Aturan dependensi:** `engine` tidak mengimpor `flask` atau `sqlite3`; `repository` adalah satu-satunya modul berisi SQL; route tidak memuat logika bisnis. Aturan ini menjaga engine tetap bisa dipanggil dari skrip evaluasi.

**Alur satu pesan:**

1. Klien mengirim `message` dan `prev_template_id` (opsional).
2. Route memvalidasi (tidak kosong, ≤ 500 karakter, JSON valid).
3. Engine menormalisasi pesan (R1) dan mengekstrak entity harga dan diet (R4).
4. Engine menghitung skor 10 intent yang bisa dinilai (R2).
5. Decision memilih intent atau fallback (R3).
6. Handler intent mengambil data lewat repository, difilter oleh entity.
7. Responder memilih template (bukan `prev_template_id`), mengisi `{daftar}`, menambah disclaimer (R7), lalu menganotasi istilah Prancis (R11).
8. Service menulis `chat_log` di dalam `try/except`; kegagalan log tidak boleh menggagalkan balasan.
9. Route mengembalikan JSON.

**Struktur proyek:**

```text
lapalais/
├── README.md                      # cara setup, seed, jalan, tes
├── requirements.txt               # Flask
├── requirements-dev.txt           # pytest, numpy, matplotlib, ruff (opsional)
├── .env.example                   # DB_PATH, ENABLE_DEBUG, ENGINE_CONFIG_PATH
├── .gitignore                     # data/*.db, reports/, .env, __pycache__/
├── wsgi.py                        # titik masuk gunicorn: create_app()
│
├── app/                           # aplikasi Flask
│   ├── __init__.py                # create_app(): config, blueprint, muat NluSnapshot
│   ├── config.py                  # baca environment
│   ├── errors.py                  # handler galat JSON (400, 404, 500)
│   ├── pages.py                   # melayani / dan /debug (file statis web/)
│   ├── api/
│   │   ├── __init__.py
│   │   ├── chat.py                # POST /api/chat, GET /healthz
│   │   ├── debug.py               # POST /api/debug/chat, /api/debug/reload
│   │   └── validation.py          # validasi body: tipe, kosong, panjang
│   ├── services/
│   │   └── chat_service.py        # orkestrasi: engine + repository + chat_log
│   ├── engine/                    # Python murni: tanpa Flask dan tanpa SQL
│   │   ├── __init__.py            # analyze(message, snapshot, params)
│   │   ├── types.py               # dataclass: Analysis, Ranking, Decision, Reply
│   │   ├── params.py              # muat dan validasi config/engine.json
│   │   ├── snapshot.py            # NluSnapshot: pola, leksikon, bobot, template, glosarium
│   │   ├── normalize.py           # R1
│   │   ├── scoring.py             # R2
│   │   ├── decision.py            # R3 (tau, delta, rho, aturan prioritas)
│   │   ├── entities.py            # R4: harga dan label diet
│   │   ├── responder.py           # R6, R7: pilih dan render template
│   │   ├── glossary.py            # R11: anotasi makna istilah Prancis
│   │   └── handlers/              # satu handler per intent
│   │       ├── __init__.py        # registri: kode intent -> handler
│   │       ├── base.py            # kontrak Handler dan hasil (daftar, teks tetap)
│   │       ├── social.py          # sapaan, penutup
│   │       ├── reservasi.py
│   │       ├── paket.py           # carte_blanche, prix_fixe
│   │       ├── a_la_carte.py
│   │       ├── teknik.py
│   │       ├── menu_filter.py     # diet dan harga (filter bersama)
│   │       ├── pairing.py
│   │       └── fallback.py        # R10: tebakan + tombol saran
│   └── data/
│       ├── __init__.py
│       ├── db.py                  # koneksi, PRAGMA, jalankan migrasi
│       └── repository.py          # satu-satunya modul berisi SQL
│
├── migrations/
│   └── 001_init.sql               # skema lengkap + PRAGMA user_version
│
├── seed/                          # sumber kebenaran data (JSON, masuk git)
│   ├── README.md                  # sumber data, kurs tetap, aturan scraping
│   ├── intents.json               # intent, pola, 3 template per intent
│   ├── lexicon.json               # stopword, sinonim, token_weight
│   ├── glossary.json              # istilah Prancis, makna, jenis (umum/teknik)
│   ├── fixed_text.json            # diet_disclaimer, tebakan, kosong, jelajah
│   ├── menu.json                  # kategori, hidangan, label diet, paket
│   ├── pairing.json               # minuman dan pairing
│   └── reservasi.json             # label dan isi info reservasi
│
├── config/
│   └── engine.json                # weights, tau, delta, rho, ambang fuzzy, kata arah
│
├── data/                          # dibuat oleh seed.py (git-ignored)
│   └── lapalais.db
│
├── eval/
│   ├── testset.csv                # kalimat, intent, split, tag
│   └── baseline_tfidf.py          # pembanding TF-IDF + cosine untuk ablation
│
├── reports/                       # luaran evaluasi: tabel metrik, plot (git-ignored)
│
├── scripts/
│   ├── seed.py                    # bangun DB dari seed/ (--reset)
│   ├── validate_seed.py           # aturan model data (juga untuk hasil scraping)
│   ├── evaluate.py                # akurasi, confusion matrix, fallback, ablation
│   └── tune.py                    # grid search bobot, tau, delta
│
├── tests/
│   ├── conftest.py                # fixture: DB sementara dari seed, app, client
│   ├── engine/
│   │   ├── test_normalize.py
│   │   ├── test_scoring.py
│   │   ├── test_decision.py
│   │   ├── test_entities.py
│   │   └── test_responder.py      # variasi, tanpa ulang, disclaimer, glosarium
│   ├── test_seed_integrity.py     # validasi seed, template, konsistensi data
│   ├── test_repository.py         # kueri filter harga dan diet
│   ├── test_api.py                # kode galat, debug mati = 404
│   └── test_acceptance_prd.py     # kriteria Given/When/Then R1-R11
│
└── web/                           # frontend native
    ├── index.html                 # client mode
    ├── debug.html                 # debug mode
    ├── css/
    │   ├── tokens.css             # warna, spasi, radius, durasi animasi
    │   ├── base.css               # reset, tipografi, latar gradien
    │   ├── chat.css               # bubble, composer, chips, typing indicator
    │   └── debug.css              # panel analisis
    └── js/
        ├── main.js                # titik masuk, pilih komponen sesuai data-mode
        ├── api.js                 # fetch, timeout, normalisasi galat
        ├── store.js               # state kecil + subscribe()
        ├── utils/
        │   ├── dom.js             # helper h(tag, attrs, ...children)
        │   └── icons.js           # ikon SVG dibuat dengan createElementNS
        └── components/
            ├── chat-window.js
            ├── message-list.js
            ├── composer.js
            ├── typing-indicator.js
            ├── suggestion-chips.js
            └── debug-panel.js
```

## 5. Model data

### 5.1 Prinsip

- **Satu fakta disimpan satu kali.** Yang bisa diturunkan tidak disimpan: label diet paket adalah irisan label hidangannya dan frasa multi-kata diambil dari istilah multi-kata di glosarium.
- **Tidak ada kolom tanpa pemakai.** Setiap kolom dipakai respons, filter, atau aturan keputusan. Sengaja tidak ada kolom `aktif`, stok, rating, gambar, atau timestamp di tabel konten.
- **Label bersifat afirmatif.** Baris `menu_item_diet` berarti “terbukti memenuhi label”; tidak ada baris berarti tidak berlabel. Label tidak pernah diinferensi, yang penting untuk R7.
- **Uang adalah integer Rupiah.** Tanpa float.
- **Menambah bukan migrasi.** Kebutuhan baru diwujudkan sebagai baris data (tabel 5.5).

### 5.2 Relasi antar tabel

```text
menu_category 1──* menu_item *──* diet_label        (menu_item_diet)
                      │ *──* menu_package            (menu_package_item)
                      └ *──* beverage                (pairing)
intent 1──* intent_pattern
intent 1──* response_template
intent 1──* chat_log
Berdiri sendiri: fixed_text, stopword, synonym, token_weight,
                 glossary_term, reservation_info
```

### 5.3 Skema SQL (`migrations/001_init.sql`)

```sql
PRAGMA foreign_keys = ON;
PRAGMA user_version = 1;

-- NLU: intent, pola, template, teks tetap
CREATE TABLE intent (
  id            INTEGER PRIMARY KEY,
  kode          TEXT NOT NULL UNIQUE,            -- 'diet', 'harga', ...
  nama          TEXT NOT NULL,                   -- label tombol dan debug
  jenis         TEXT NOT NULL CHECK (jenis IN ('info','sosial','fallback')),
  frasa_kanonik TEXT,                            -- dikirim tombol saran
  CHECK ((jenis = 'info') = (frasa_kanonik IS NOT NULL))
);
CREATE TABLE intent_pattern (
  id        INTEGER PRIMARY KEY,
  intent_id INTEGER NOT NULL REFERENCES intent(id) ON DELETE CASCADE,
  pola      TEXT NOT NULL,
  UNIQUE (intent_id, pola)
);
CREATE TABLE response_template (
  id        INTEGER PRIMARY KEY,
  intent_id INTEGER NOT NULL REFERENCES intent(id) ON DELETE CASCADE,
  isi       TEXT NOT NULL,                       -- info: memuat {daftar}
  UNIQUE (intent_id, isi)
);
CREATE TABLE fixed_text (kunci TEXT PRIMARY KEY, isi TEXT NOT NULL);

-- Leksikon
CREATE TABLE stopword (kata TEXT PRIMARY KEY);
CREATE TABLE synonym (varian TEXT PRIMARY KEY, kanonik TEXT NOT NULL);
CREATE TABLE token_weight (                      -- hanya pengecualian; default 2
  token TEXT PRIMARY KEY,
  bobot INTEGER NOT NULL CHECK (bobot IN (1, 3))
);
CREATE TABLE glossary_term (
  id      INTEGER PRIMARY KEY,
  istilah TEXT NOT NULL UNIQUE COLLATE NOCASE,
  makna   TEXT NOT NULL,                         -- satu kalimat pendek
  jenis   TEXT NOT NULL DEFAULT 'umum' CHECK (jenis IN ('umum','teknik'))
);

-- Menu
CREATE TABLE menu_category (
  id     INTEGER PRIMARY KEY,
  nama   TEXT NOT NULL UNIQUE,
  urutan INTEGER NOT NULL UNIQUE
);
CREATE TABLE menu_item (
  id          INTEGER PRIMARY KEY,
  nama        TEXT NOT NULL UNIQUE COLLATE NOCASE,
  deskripsi   TEXT NOT NULL,                     -- bahasa Indonesia
  kategori_id INTEGER NOT NULL REFERENCES menu_category(id),
  harga       INTEGER NOT NULL CHECK (harga > 0) -- Rupiah
);
CREATE TABLE diet_label (
  id   INTEGER PRIMARY KEY,
  kode TEXT NOT NULL UNIQUE,                     -- vegetarian, halal, non_seafood
  nama TEXT NOT NULL
);
CREATE TABLE menu_item_diet (
  item_id INTEGER NOT NULL REFERENCES menu_item(id)  ON DELETE CASCADE,
  diet_id INTEGER NOT NULL REFERENCES diet_label(id) ON DELETE CASCADE,
  PRIMARY KEY (item_id, diet_id)
) WITHOUT ROWID;
CREATE TABLE menu_package (
  id           INTEGER PRIMARY KEY,
  tipe         TEXT NOT NULL CHECK (tipe IN ('prix_fixe','carte_blanche')),
  nama         TEXT NOT NULL UNIQUE,
  deskripsi    TEXT NOT NULL,                             -- konsep, tujuan, & pengalaman rasa
  harga        INTEGER NOT NULL CHECK (harga > 0),        -- Rupiah
  durasi_menit INTEGER NOT NULL CHECK (durasi_menit > 0)  -- durasi total course
);
CREATE TABLE menu_package_item (
  package_id INTEGER NOT NULL REFERENCES menu_package(id) ON DELETE CASCADE,
  item_id    INTEGER NOT NULL REFERENCES menu_item(id),
  urutan     INTEGER NOT NULL CHECK (urutan > 0),         -- urutan sajian
  PRIMARY KEY (package_id, item_id),
  UNIQUE (package_id, urutan)
) WITHOUT ROWID;
CREATE TABLE beverage (
  id        INTEGER PRIMARY KEY,
  nama      TEXT NOT NULL UNIQUE,
  deskripsi TEXT NOT NULL,                                -- bahasa Indonesia
  jenis     TEXT NOT NULL CHECK (jenis IN ('wine','non_alkohol'))
);
CREATE TABLE pairing (
  item_id     INTEGER NOT NULL REFERENCES menu_item(id) ON DELETE CASCADE,
  beverage_id INTEGER NOT NULL REFERENCES beverage(id)  ON DELETE CASCADE,
  PRIMARY KEY (item_id, beverage_id)
) WITHOUT ROWID;
CREATE TABLE reservation_info (
  id     INTEGER PRIMARY KEY,
  label  TEXT NOT NULL UNIQUE,                   -- 'Jam operasional', ...
  isi    TEXT NOT NULL,
  urutan INTEGER NOT NULL
);

-- Log (P1)
CREATE TABLE chat_log (
  id          INTEGER PRIMARY KEY,
  dibuat_pada TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
  pesan       TEXT NOT NULL,
  intent_id   INTEGER NOT NULL REFERENCES intent(id),  -- hasil keputusan
  skor        TEXT NOT NULL CHECK (json_valid(skor)),  -- semua intent + komponen
  entitas     TEXT CHECK (entitas IS NULL OR json_valid(entitas))
);

CREATE INDEX ix_menu_item_kategori ON menu_item(kategori_id);
CREATE INDEX ix_menu_item_harga    ON menu_item(harga);
CREATE INDEX ix_item_diet_diet     ON menu_item_diet(diet_id);
CREATE INDEX ix_pkg_item_item      ON menu_package_item(item_id);
CREATE INDEX ix_pairing_beverage   ON pairing(beverage_id);
CREATE INDEX ix_pattern_intent     ON intent_pattern(intent_id);
CREATE INDEX ix_template_intent    ON response_template(intent_id);
```

### 5.4 Fungsi tabel terhadap intent

| Intent | Data yang dipakai |
| --- | --- |
| Sapaan, Penutup | `response_template` saja |
| Informasi reservasi | `reservation_info` |
| Carte Blanche | `menu_package` (tipe `carte_blanche`, kolom `durasi_menit`, `deskripsi` konsep/pengalaman rasa) + `menu_package_item` (kolom `urutan`) + `menu_item` |
| Menu à la carte | `menu_category` + `menu_item` |
| Set course (Prix Fixe) | `menu_package` (tipe `prix_fixe`, kolom `durasi_menit`, `deskripsi` konsep/pengalaman rasa) + `menu_package_item` (kolom `urutan`) + `menu_item` |
| Teknik masakan | `glossary_term` dengan `jenis = 'teknik'` |
| Diet/alergen | `menu_item` + `menu_item_diet` + `diet_label` |
| Menu berdasarkan harga | `menu_item.harga` (+ filter diet bila ada) |
| Informasi pairing | `pairing` + `beverage` (termasuk `deskripsi` minuman) + `menu_item` |
| Fallback | `intent` (tombol saran), `fixed_text` |

Kontrak template: template intent `info` wajib memuat tepat satu `{daftar}` (R5: variasi kalimat, data sama); template `sosial` dan `fallback` tidak memuat placeholder. Seed gagal validasi bila aturan ini dilanggar. Teks tetap di `fixed_text`: `diet_disclaimer`, `tebakan` (“Mungkin maksud Anda: {intent}?”), `kosong` (tidak ada menu yang cocok), `jelajah` (pengantar tombol saran).

### 5.5 Cara menambah tanpa mengubah skema

| Kebutuhan baru | Yang berubah |
| --- | --- |
| Label diet baru (mis. bebas gluten) | 1 baris `diet_label`, baris `menu_item_diet`, alias di `synonym`; tanpa kode |
| Alergen tambahan (P2) | Sama seperti label diet; jadi data, bukan kolom |
| Kategori, hidangan, paket, minuman baru | Baris di tabel terkait |
| Info reservasi baru | 1 baris `reservation_info` |
| Intent baru | Baris `intent`, pola, 3 template, dan satu kelas handler (satu-satunya yang butuh kode) |
| Hubungan hidangan dan teknik (P2) | Tabel relasi baru `menu_item_technique` |

### 5.6 Kueri kunci dan aturan data

Filter harga dan diet dijalankan di SQL. Beberapa label berarti **semua** label harus dipenuhi:

```sql
SELECT i.id, i.nama, i.deskripsi, i.harga, c.nama AS kategori
FROM menu_item i JOIN menu_category c ON c.id = i.kategori_id
WHERE (:batas_le IS NULL OR i.harga <= :batas_le)
  AND (:batas_gt IS NULL OR i.harga >  :batas_gt)
  AND (:n_label = 0 OR i.id IN (
        SELECT d.item_id FROM menu_item_diet d
        JOIN diet_label l ON l.id = d.diet_id
        WHERE l.kode IN (SELECT value FROM json_each(:kode_label))
        GROUP BY d.item_id
        HAVING COUNT(DISTINCT l.kode) = :n_label))
ORDER BY c.urutan, i.harga;
```

**Aturan validasi seed** (`validate_seed.py`, juga menjadi aturan untuk hasil scraping nanti):

- Harga integer Rupiah > 0; harga mata uang lain dikonversi dengan kurs tetap yang dicatat di `seed/README.md`.
- Nama hidangan unik; `deskripsi` hidangan dan minuman berbahasa Indonesia dan diparafrase, bukan salinan teks sumber.
- Label diet hanya diberikan bila terbukti dari sumber; jangan menebak.
- Setiap paket berisi ≥ 1 hidangan yang ada, bernomor urut 1 sampai n tanpa celah (seed.py mengisi nomor dari posisi hidangan dalam daftar paket), punya durasi dalam menit > 0, dan memuat `deskripsi` yang menjelaskan maksud/tujuan course set, konsep, serta profil sensori/pengalaman rasa; setiap hidangan punya kategori.
- Setiap istilah Prancis yang muncul di nama kategori, paket, atau template ada di glosarium.
- Setiap intent `info` punya tepat 3 template dengan satu `{daftar}`; `sosial` dan `fallback` 3 template tanpa placeholder.
- Pola intent tidak kosong dan tidak identik antar intent.

### 5.7 Parameter engine (`config/engine.json`)

| Parameter | Nilai awal | Sumber keputusan |
| --- | --- | --- |
| `weights` (jaccard, fuzzy, cakupan) | 0,4 / 0,3 / 0,3 | PRD R2, dituning |
| `tau` | 0,45 | PRD #1 |
| `delta` | 0,10 | PRD OQ-5 |
| `rho` | 0,15 | PRD OQ-4 |
| `fuzzy_match_min` | 0,8 | PRD R2 |
| `fuzzy_exact_max_len` | 3 (token ≤ 3 huruf harus persis) | Usulan: mencegah “jus” cocok dengan “bus” |
| `token_weight_default` | 2 | PRD #4 (3 pembeda, 2 domain, 1 umum) |
| `price_default_threshold` | 1200000 | PRD R4 |
| `direction_le` / `direction_gt` | Daftar awal kata arah (bawah, kurang, murah / atas, lebih, mahal) | Usulan, dituning dari set uji |
| `max_message_length` | 500 | Usulan |

### 5.8 Contoh seed (ilustrasi, bukan data final)

```json
{
  "kategori": [{"nama": "Les Entrées", "urutan": 1}, {"nama": "Les Plats", "urutan": 2}],
  "hidangan": [
    {"nama": "Velouté de Champignons", "kategori": "Les Entrées", "harga": 285000,
     "deskripsi": "Sup krim jamur yang halus", "diet": ["vegetarian", "non_seafood"]},
    {"nama": "Boeuf Bourguignon", "kategori": "Les Plats", "harga": 890000,
     "deskripsi": "Daging sapi dimasak pelan dalam saus anggur merah", "diet": ["non_seafood"]}
  ],
  "paket": [
    {"tipe": "prix_fixe", "nama": "Menu Dégustation Trois Plats", "harga": 1100000, "durasi_menit": 90,
     "hidangan": ["Velouté de Champignons", "Boeuf Bourguignon"]}
  ],
  "minuman": [
    {"nama": "Chablis", "jenis": "wine", "deskripsi": "Anggur putih kering yang segar",
     "pairing": ["Velouté de Champignons"]}
  ]
}
```

## 6. Engine

### 6.1 Pipeline dan tipe data

`analyze(message, snapshot, params)` mengembalikan `Analysis` (token, entity, peringkat, keputusan). Engine memakai dataclass tak-berubah; seluruh data NLU datang dari `NluSnapshot` yang dimuat sekali saat start (pola, leksikon, bobot, template, glosarium). Menu, paket, pairing, dan info reservasi **tidak** di-cache: diambil lewat SQL saat dibutuhkan, jadi perubahan data langsung terlihat tanpa reload.

### 6.2 Normalisasi (R1)

1. Huruf kecil dan hapus aksen (`unicodedata` NFKD).
2. Ubah ekspresi angka menjadi nilai: `1.200.000`, `1,2 juta`, `1.2jt` → 1200000. Angka disimpan sebagai entity dan **dikeluarkan** dari token skor agar tidak menurunkan Jaccard.
3. Tanda baca menjadi spasi; rapikan spasi.
4. Ganti frasa dan sinonim dengan pencocokan terpanjang lebih dulu: varian dari `synonym` ditambah istilah multi-kata di `glossary_term` (mis. `prix fixe` → `prix_fixe`).
5. Salin token untuk ekstraksi entity, lalu buang stopword untuk skor. Kata arah (bawah, atas) dibaca dari salinan sebelum stopword dibuang.

### 6.3 Skor (R2)

```python
def score_pattern(msg: frozenset[str], pat: Pattern, p: Params) -> Components:
    inter   = pat.tokens & msg
    jaccard = len(inter) / len(pat.tokens | msg)
    hits    = {t for t in pat.tokens if token_matches(t, msg, p)}
    fuzzy   = len(hits) / len(pat.tokens)
    cakupan = sum(pat.weight[t] for t in hits) / sum(pat.weight.values())
    return Components(jaccard, fuzzy, cakupan)

def score_intent(msg, intent, p):
    best = max((score_pattern(msg, pat, p) for pat in intent.patterns),
               key=lambda c: p.w_j * c.jaccard + p.w_f * c.fuzzy + p.w_c * c.cakupan)
    return best  # skor intent = komponen dari pola terbaik
```

`token_matches` memakai `SequenceMatcher(...).ratio() ≥ fuzzy_match_min`, dengan `quick_ratio` sebagai penyaring awal dan kecocokan persis untuk token ≤ 3 huruf. Hanya 10 intent yang punya pola; **fallback adalah hasil keputusan, bukan kandidat**. Karena itu tampilan debug menampilkan 10 baris peringkat plus baris keputusan; PRD P1 menyebut “11 intent”, dan ini perlu disamakan (OQ-1).

### 6.4 Keputusan (R3, R10)

```python
def decide(ranking, p):
    top, second = ranking[0], ranking[1]
    if top.skor < p.tau:
        guess = top if top.skor >= p.rho else None
        return Decision('fallback', alasan='di_bawah_tau', tebakan=guess)
    if top.skor - second.skor >= p.delta:
        return Decision(top.kode, alasan='ambang')
    return resolve(top, second)   # aturan prioritas di bawah
```

`resolve` menerapkan aturan prioritas PRD berurutan: (a) intent `sosial` kalah dari intent `info` yang lolos τ; (b) pasangan diet dan harga dijawab sebagai satu intent karena kedua handler membaca kedua entity; (c) pemenang adalah intent dengan jumlah bobot token pembeda (bobot 3) lebih besar; (d) bila masih seri, intent ber-`id` terkecil menang dan alasan dicatat `seri`.

### 6.5 Entity (R4)

- **Harga:** nilai angka dari normalisasi + arah dari kata arah. Arah *kurang/bawah* → `harga <= nilai`; arah *atas/lebih* → `harga > nilai`. Tanpa angka dipakai `price_default_threshold`. Tanpa arah, handler menampilkan dua kelompok (sampai dengan dan di atas batas).
- **Diet:** token yang sama dengan `diet_label.kode` setelah sinonim (mis. “tanpa seafood” → `non_seafood`). Beberapa label berarti irisan.
- Entity diekstrak untuk **semua** pesan; handler diet dan harga memakai keduanya lewat satu fungsi filter bersama.

### 6.6 Respons (R5–R7, R10, R11)

1. **Pilih template:** acak dari 3 template intent, mengecualikan `prev_template_id` bila milik intent yang sama. Generator acak bisa diberi seed untuk tes.
2. **Render:** `{daftar}` diisi teks daftar dari handler (baris “• nama — deskripsi — Rp...”, dengan judul kelompok seperti “Sampai dengan Rp1.200.000”). Untuk paket, daftar bernomor sesuai urutan sajian, diawali durasi serta narasi deskripsi paket (maksud, konsep, dan pengalaman rasa); khusus untuk Carte Blanche, template menekankan rekomendasi chef hari ini yang spontan berdasarkan bahan segar terbaik; untuk pairing, baris “• hidangan: minuman — deskripsi minuman”.
3. **Disclaimer:** handler diet menambahkan `diet_disclaimer` setelah template dirender, sehingga tidak bisa dihilangkan oleh penulis template.
4. **Anotasi glosarium:** setiap kemunculan istilah (tanpa peduli huruf besar-kecil dan aksen) diikuti maknanya dalam tanda kurung, dengan pencocokan terpanjang dulu. Nama hidangan tidak dianotasi karena sudah punya deskripsi; handler menandainya sebagai span terlindungi. Nama minuman dan istilah pada daftar teknik diperlakukan sama, karena maknanya sudah ada di baris yang sama.
5. **Fallback:** kalimat pembuka (template) + baris `tebakan` bila skor teratas ≥ ρ + `suggestions`: tombol untuk semua intent `info` selain tebakan (tebakan di urutan pertama). Setiap tombol membawa `frasa_kanonik`, jadi tidak ada flow.
6. **Hasil kosong:** bila irisan filter kosong, handler memakai `kosong`, bukan fallback.

## 7. API

| Endpoint | Metode | Fungsi |
| --- | --- | --- |
| `/api/chat` | POST | Balasan untuk client mode |
| `/api/debug/chat` | POST | Balasan + blok `debug` (hanya jika `ENABLE_DEBUG=1`) |
| `/api/debug/reload` | POST | Muat ulang `NluSnapshot` setelah seed berubah (hanya debug) |
| `/healthz` | GET | Cek hidup untuk deployment |
| `/` dan `/debug` | GET | Halaman statis client dan debug |

**Permintaan:** `{"message": "menu vegetarian di bawah 1,2 juta", "prev_template_id": 14}`

**Respons client:**

```json
{
  "reply": "Berikut menu yang sesuai pilihan Anda:\n• Velouté (sup krim) ...",
  "template_id": 17,
  "suggestions": []
}
```

**Respons debug** menambahkan:

```json
"debug": {
  "tokens": ["menu", "vegetarian", "bawah"],
  "entities": {"harga": {"op": "le", "nilai": 1200000}, "diet": ["vegetarian"]},
  "ranking": [{"intent": "diet", "skor": 0.71, "jaccard": 0.50, "fuzzy": 1.0, "cakupan": 0.80}],
  "decision": {"intent": "diet", "alasan": "ambang", "tau": 0.45, "delta": 0.10, "rho": 0.15},
  "latency_ms": 4
}
```

| Kode | Kondisi | Isi |
| --- | --- | --- |
| 400 `pesan_kosong` | Pesan kosong atau hanya spasi | `{"error": {"code": ..., "message": ...}}` |
| 400 `pesan_terlalu_panjang` | > 500 karakter | sama |
| 400 `json_tidak_valid` | Body bukan JSON object | sama |
| 404 | `/api/debug/*` saat debug mati | sama |
| 500 `kesalahan_server` | Galat tak terduga | Pesan generik; detail hanya di log server |

Engine tidak pernah melempar galat untuk teks aneh (emoji, simbol, satu huruf): hasil kosong setelah normalisasi menjadi fallback tanpa tebakan.

## 8. Frontend dan UI

### 8.1 Struktur modul

```text
web/
├── index.html            # client mode  (<body data-mode=client>)
├── debug.html            # debug mode   (<body data-mode=debug>)
├── css/                  # tokens.css, base.css, chat.css, debug.css
└── js/
    ├── main.js           # titik masuk, merakit komponen sesuai mode
    ├── api.js            # fetch + timeout + normalisasi galat
    ├── store.js          # state kecil + subscribe()
    ├── utils/dom.js      # helper h(tag, attrs, ...children)
    └── components/       # chat-window, message-list, composer,
                          # typing-indicator, suggestion-chips, debug-panel
```

| Modul | Tugas |
| --- | --- |
| `main.js` | Membaca `data-mode`, membuat store, memasang komponen |
| `api.js` | `sendMessage()` ke `/api/chat` atau `/api/debug/chat`; `AbortController` 8 detik; galat jaringan dan server jadi satu bentuk error |
| `store.js` | Menyimpan `messages`, `prevTemplateId`, `pending`, `lastDebug`; komponen berlangganan perubahan |
| `message-list.js` | Menggambar bubble, auto-scroll, `aria-live=polite` |
| `composer.js` | Textarea + tombol kirim; Enter mengirim, Shift+Enter baris baru; dinonaktifkan saat `pending` |
| `typing-indicator.js` | Tiga titik animasi selama `pending` |
| `suggestion-chips.js` | Tombol saran dari respons fallback; klik mengirim `frasa_kanonik` sebagai pesan biasa |
| `debug-panel.js` | Ringkasan keputusan, token, entity, tabel peringkat, parameter |
| `utils/dom.js` | Pembuat elemen yang selalu memakai `textContent`, tidak pernah `innerHTML` |

Pola komponen: fungsi pabrik yang mengembalikan `{ el, update }`; komunikasi lewat store dan callback, tanpa framework. Tombol “Hapus obrolan” mengosongkan `messages` dan `prevTemplateId`; tidak ada penyimpanan di browser (tanpa memori tamu, sesuai non-goals).

### 8.2 Client mode dan debug mode

```text
CLIENT (/)                          DEBUG (/debug)
+---------------------------+       +------------------------+-----------------------+
| La Palais   [Hapus]       |       | Chat (sama dengan      | Keputusan: diet       |
+---------------------------+       | client mode)           | Alasan: ambang        |
|  pesan tamu         ...   |       |                        | tau 0,45  delta 0,10  |
|  ... balasan bot          |       |                        | Token  |  Entity      |
|  [Info reservasi] [Prix..]|       |                        | Peringkat 10 intent   |
+---------------------------+       |                        | skor + 3 komponen +   |
| [ Tulis pertanyaan... ] > |       | [ composer ]        >  | bar, terpilih ditandai|
+---------------------------+       +------------------------+-----------------------+
```

| Aspek | Client mode | Debug mode |
| --- | --- | --- |
| Endpoint | `/api/chat` | `/api/debug/chat` |
| Isi layar | Chat saja, tombol saran saat fallback | Chat + panel analisis |
| Skor dan peringkat | Tidak pernah dikirim | Semua 10 intent + komponen, alasan keputusan |
| Ketersediaan | Selalu | Hanya jika `ENABLE_DEBUG=1` |
| Layar sempit | Satu kolom | Panel berada di bawah chat dalam `<details>` yang bisa dilipat |

Panel debug mengikuti respons terakhir dan menyorot intent terpilih, baris margin yang menipis (selisih < δ), dan baris di bawah ρ. Ini alat utama untuk menganalisis salah klasifikasi saat tuning.

### 8.3 Komponen UI dan adaptasi dari 21st.dev

| Elemen pada referensi | Implementasi native |
| --- | --- |
| Latar gradien | `linear-gradient` dari variabel `--bg-from` dan `--bg-to` pada `body` |
| Kolom input pesan | `composer.js`: textarea auto-tinggi + tombol kirim berikon SVG |
| Percakapan pengguna dan AI | `message-list.js`: bubble berbeda untuk tamu dan bot |
| Indikator mengetik | Tiga `<span>` dengan `@keyframes` bergantian |
| Animasi pesan muncul | `@keyframes rise` (fade + geser 8 px), 180 ms |
| Hapus riwayat | Tombol di header, memanggil `store.reset()` |
| Responsif | Lebar maksimum 720 px di tengah, padding mengikuti viewport, `100dvh` |

Untuk fitur yang tidak ada di referensi (tombol saran, panel debug), gaya dan token yang sama dipakai ulang supaya tampilan konsisten.

### 8.4 Gaya visual dan aksesibilitas

- **Token CSS** di `tokens.css`: warna, radius, spasi, durasi animasi. Usulan awal tema gelap bernuansa restoran Prancis: latar burgundi gelap ke hitam hangat, aksen emas pucat, teks krem, bubble tamu burgundi, bubble bot transparan. Judul memakai font serif sistem (mis. Georgia) agar tanpa dependensi font eksternal.
- **Aksesibilitas:** label pada textarea, fokus terlihat jelas, `aria-live=polite` untuk balasan baru, tombol saran bisa diakses keyboard, kontras teks minimal 4,5:1.
- **Gerak:** semua animasi dimatikan di bawah `@media (prefers-reduced-motion: reduce)`.
- **Teks respons:** ditampilkan dengan `white-space: pre-line` agar baris “•” dari server terbaca tanpa parser markdown.

## 9. Kualitas dan operasional

### 9.1 Pengujian

| Lapisan | Isi | Alat |
| --- | --- | --- |
| Unit engine | Normalisasi (aksen, angka, frasa), skor, keputusan, entity | pytest |
| Golden test PRD | Setiap kriteria Given/When/Then di R1–R11 menjadi satu tes | pytest |
| Integritas data | Validasi seed; tiap intent `info` punya 3 template dengan satu `{daftar}`; ketiga template merender daftar identik (R5); setiap istilah glosarium selalu diikuti makna (R11); disclaimer diet muncul di semua variasi (R7) | pytest + `validate_seed.py` |
| Tidak mengulang template | Dua panggilan berturut-turut menghasilkan template berbeda (R6), generator acak di-seed | pytest |
| API | Kode galat, batas panjang, debug mati mengembalikan 404 | Flask test client |
| Evaluasi akurasi | Akurasi, confusion matrix, metrik fallback, ketahanan typo pada set held-out | `evaluate.py` |
| UI | Uji manual berskenario dengan 8–10 penguji (PRD bagian 7); fungsi DOM murni bisa diuji dengan Node bila perlu | manual |

### 9.2 Evaluasi dan tuning (R8)

- `eval/testset.csv` berisi kolom `kalimat`, `intent` (kode atau `fallback`), `split` (`tuning` atau `heldout`), dan `tag` (formal, informal, typo, multi, oos). Kolom `tag` dipakai untuk metrik ketahanan typo di PRD.
- **Tuning cepat tanpa menghitung ulang `SequenceMatcher`:** hitung sekali tiga komponen untuk setiap pasangan kalimat dan pola, simpan sebagai matriks numpy. Skor intent adalah maks atas pola dari kombinasi bobot, sehingga tiap kombinasi bobot cukup perkalian matriks plus `reduceat` per intent. τ dan δ lalu dievaluasi di atas matriks skor yang sudah jadi.
- **Grid awal:** bobot dengan langkah 0,1 yang berjumlah 1 (66 kombinasi), τ 0,30–0,60 langkah 0,01, δ 0,02–0,20 langkah 0,02. Hanya set `tuning` yang dipakai; `heldout` dihitung sekali di akhir.
- **Ablation:** bobot (1,0,0), (0,1,0), (0,0,1), baseline 0,4/0,3/0,3, bobot hasil tuning, dan TF-IDF + cosine sebagai pembanding terpisah (`eval/baseline_tfidf.py`). Luaran: tabel metrik dan plot distribusi skor per intent untuk memilih τ.

### 9.3 Observabilitas

Aplikasi menulis log JSON per baris (id permintaan, intent, skor teratas, alasan, latensi). Tabel `chat_log` menyimpan pesan, intent hasil keputusan, serta skor semua intent dan entity sebagai JSON; kueri `json_extract` cukup untuk mencari pesan dengan margin tipis atau yang jatuh ke fallback.

### 9.4 Keamanan dan privasi

- Semua SQL parametrik; input dibatasi 500 karakter dan harus JSON object.
- Klien tidak pernah memakai `innerHTML`; balasan server dianggap teks biasa.
- Debug mati secara default; bila disajikan ke publik, lindungi dengan basic auth di reverse proxy (OQ-4).
- `chat_log` menyimpan teks bebas dari penguji; tidak ada identitas pengguna, dan tabel boleh dikosongkan kapan saja.

### 9.5 Deployment

Pengembangan: `python scripts/seed.py --reset` lalu `flask --app app run --debug`, dengan `ENABLE_DEBUG=1` bila perlu. Uji publik: gunicorn dua worker di belakang reverse proxy. Backup cukup `seed/` di git; SQLite dapat dibangun ulang, dan satu-satunya data runtime adalah `chat_log`.

## 10. Trade-off dan yang ditinjau ulang

| Keputusan | Alternatif | Alasan memilih | Dampak |
| --- | --- | --- | --- |
| Modular monolith | Layanan NLU terpisah | Satu pengembang, beban kecil | Tidak bisa diskalakan terpisah; tidak perlu sekarang |
| `sqlite3` mentah | SQLAlchemy | Skema kecil, nol dependensi | SQL ditulis sendiri; terisolasi di `repository` |
| Label diet sebagai relasi | Kolom boolean | Menambah label tanpa migrasi | Kueri lebih panjang (join) |
| Seed JSON sebagai sumber | Database sebagai sumber | Diff di git, reproducible, cocok untuk scraping bertahap | Perlu langkah `seed.py` |
| Parameter di JSON | Tabel `config` | Versi di git, mudah dibandingkan | Ubah parameter berarti ubah file, bukan lewat UI |
| Server stateless + `prev_template_id` | Sesi server | Tetap tanpa flow, mudah diuji | Klien bisa mengirim id sembarang; diabaikan bila bukan milik intent terpilih |
| Cache NLU, menu via SQL | Cache semuanya | Perubahan menu langsung terlihat | Perubahan pola atau glosarium butuh `reload` |
| Skor di `chat_log` sebagai JSON | Tabel skor ternormalisasi | Satu baris per pesan, cukup untuk analisis | Analisis agregat butuh `json_each` |
| Frontend tanpa framework | React (seperti komponen referensi) | Sesuai stack pilihanmu | Interaksi ditulis manual; UI sekecil ini masih nyaman |

**Akan ditinjau ulang saat sistem tumbuh:** pencarian level hidangan (P2) akan butuh indeks nama hidangan dan relasi hidangan-teknik; jumlah pola ribuan butuh indeks terbalik token-ke-pola supaya skor tidak linear; dukungan Inggris butuh kolom bahasa pada pola dan template; alur multi-turn butuh tabel sesi; trafik publik atau tulis bersamaan butuh PostgreSQL; pengelola non-teknis butuh antarmuka admin untuk konten.

## 11. Open Questions

Semua poin non-blocking kecuali nomor 2. Tiap poin berisi rekomendasi supaya bisa langsung disetujui atau diubah.

1. **OQ-1 \[NON-BLOCKING\] \[PRD\] Peringkat 10 atau 11 intent.** Fallback tidak punya pola sehingga tidak bisa dinilai. Rekomendasi: debug menampilkan 10 intent berskor plus baris keputusan; samakan kalimat “seluruh 11 intent” di PRD P1 menjadi “seluruh intent yang dinilai”. ==> ya hanya 10 intent, tapi fallback tetap dijadikan intent yang tidak dinilai yaitu sebagai flag fallback
2. **OQ-2 \[BLOCKING\] \[Data\] Apakah semua hidangan di paket juga dijual à la carte?** Model menyimpan paket sebagai kumpulan `menu_item`, sehingga hidangan khusus paket akan ikut muncul di daftar à la carte. Rekomendasi: asumsikan ya untuk v1. Jika tidak, tambahkan penanda hidangan khusus paket sebelum seed dibuat.
3. **OQ-3 \[NON-BLOCKING\] \[Data\] Apakah filter harga dan diet berlaku untuk paket?** Rekomendasi: v1 hanya untuk `menu_item`; paket muncul lewat intent Carte Blanche dan Prix Fixe. Label diet paket bisa diturunkan nanti (paket vegetarian bila semua hidangannya vegetarian) tanpa mengubah skema.
4. **OQ-4 \[NON-BLOCKING\] \[Engineering\] Perlindungan debug mode.** Rekomendasi: cukup `ENABLE_DEBUG` untuk pengembangan lokal; bila diuji publik, pasang basic auth di reverse proxy dan jangan aktifkan endpoint `reload` di sana.
5. **OQ-5 \[NON-BLOCKING\] \[Desain\] Tema visual.** Rekomendasi: tema gelap burgundi-emas yang disebut di 8.4 sebagai titik awal; token CSS membuat penggantian tema murah.
6. **OQ-6 \[NON-BLOCKING\] \[Engineering\] Daftar kata arah harga.** Kata ambigu seperti “sampai” dan “minimal” perlu diputuskan. Rekomendasi: mulai dari daftar di 5.7, lalu perbaiki dari kalimat uji bertag `multi` dan `informal`.
7. **OQ-7 \[NON-BLOCKING\] \[Data\] Makna durasi dan deskripsi minuman.** Diasumsikan `durasi_menit` adalah total durasi satu set course (berlaku untuk Prix Fixe dan Carte Blanche) dan `beverage.deskripsi` menjelaskan minumannya sendiri. Rekomendasi: pertahankan; jika yang dimaksud adalah alasan sebuah minuman cocok dengan hidangan tertentu, simpan catatan itu sebagai kolom baru di tabel `pairing`.

## 12. Rencana implementasi

Urutan mengikuti fase PRD; tidak ada tenggat tetap.

| Fase PRD | Paket kerja | Hasil |
| --- | --- | --- |
| 0 Data dan uji | `001_init.sql`, `seed/*.json` sample kecil, `validate_seed.py`, `seed.py`; `eval/testset.csv` (≈ 220 + 30 kalimat) | DB terisi sample; set uji siap |
| 1 Engine dasar | `normalize`, `scoring`, `decision`, `entities`, `handlers`, `responder`; golden test R1–R11 | `analyze()` lulus tes dari baris perintah |
| 1 Aplikasi | `create_app`, `api/chat`, `chat_log`, `/healthz` | Endpoint chat berjalan |
| 2 Evaluasi dan tuning | `evaluate.py`, `tune.py`, ablation, plot distribusi skor | `engine.json` hasil tuning + laporan |
| 3 Antarmuka | Modul `web/`, client mode lalu debug mode (`/api/debug/*`) | Demo dua mode |
| 3 Uji pengguna | 8–10 penguji, 5 tugas, kuesioner | Metrik lagging PRD |

**Dependensi:** engine baru bisa diuji bermakna setelah seed dan set uji ada; debug mode sebaiknya dibuat sebelum tuning karena panel peringkat mempercepat analisis salah klasifikasi.

## 13. Seed pertama (v1)

Seed ini adalah data pertama yang mengikuti model data di bagian 5. **Semua isinya (menu, harga, jam, kontak) hanyalah contoh** untuk menguji engine dan akan diganti dengan data restoran sebenarnya. Bentuk file di bagian ini menggantikan contoh di 5.8.

| File | Tabel tujuan | Catatan |
| --- | --- | --- |
| `intents.json` | `intent`, `intent_pattern`, `response_template` | 11 intent, 106 pola, 33 template |
| `lexicon.json` | `stopword`, `synonym`, `token_weight` | `sinonim` dibaca sebagai varian → kanonik |
| `glossary.json` | `glossary_term` | 21 istilah (10 teknik, 11 umum) |
| `fixed_text.json` | `fixed_text` | 4 teks tetap |
| `menu.json` | `diet_label`, `menu_category`, `menu_item`, `menu_item_diet`, `menu_package`, `menu_package_item` | 15 hidangan, 3 paket; `urutan` paket = posisi hidangan dalam daftar |
| `pairing.json` | `beverage`, `pairing` | 9 minuman, 20 pasangan |
| `reservasi.json` | `reservation_info` | 6 baris |

### 13.1 `seed/intents.json`

Pola ditulis alami; saat dimuat, pola dinormalisasi dengan pipeline yang sama dengan pesan (aksen dihapus, stopword dibuang, sinonim dan frasa diganti).

```json
{
  "intents": [
    {"kode": "sapaan", "nama": "Sapaan", "jenis": "sosial", "frasa_kanonik": null,
     "pola": ["halo", "hai", "hallo", "selamat pagi", "selamat siang", "selamat sore", "selamat malam", "permisi", "assalamualaikum", "salam"],
     "template": [
       "Selamat datang di restoran kami. Ada yang bisa kami bantu seputar menu, reservasi, atau pairing minuman?",
       "Halo, selamat datang. Silakan tanyakan apa saja tentang menu, harga, atau reservasi kami.",
       "Selamat datang. Kami siap membantu Anda memilih hidangan yang tepat."]},

    {"kode": "reservasi", "nama": "Info reservasi", "jenis": "info", "frasa_kanonik": "Bagaimana cara reservasi?",
     "pola": ["reservasi", "reservasi meja", "booking meja", "pesan meja", "pesan tempat", "cara reservasi", "jam buka", "jam operasional", "kontak restoran", "dress code", "kebijakan pembatalan"],
     "template": [
       "Berikut informasi reservasi kami: {daftar}",
       "Untuk reservasi, mohon perhatikan hal berikut: {daftar}",
       "Kami dengan senang hati menyambut reservasi Anda. Informasi yang perlu diketahui: {daftar}"]},

    {"kode": "carte_blanche", "nama": "Carte Blanche (pilihan chef)", "jenis": "info", "frasa_kanonik": "Apa isi menu Carte Blanche?",
     "pola": ["carte blanche", "menu carte blanche", "isi carte blanche", "pilihan chef", "menu pilihan chef", "chef pick", "rekomendasi chef", "menu chef"],
     "template": [
       "Ini adalah rekomendasi Carte Blanche dari chef kami hari ini, diracik khusus berdasarkan bahan musiman tersegar: {daftar}",
       "Dalam Carte Blanche hari ini, chef mempersembahkan kejutan rasa dengan pilihan hidangan terbaik yang bisa berbeda setiap harinya: {daftar}",
       "Menyerahkan pilihan sepenuhnya kepada intuisi chef hari ini—inilah rangkaian hidangan otentik Carte Blanche yang kami siapkan: {daftar}"]},

    {"kode": "a_la_carte", "nama": "Menu à la carte", "jenis": "info", "frasa_kanonik": "Tampilkan menu à la carte",
     "pola": ["a la carte", "menu a la carte", "menu satuan", "les entrees", "les plats", "les fromages", "les desserts", "hidangan pembuka", "hidangan utama", "hidangan penutup", "daftar menu", "dessert"],
     "template": [
       "Silakan pilih hidangan satuan dari menu à la carte kami: {daftar}",
       "Berikut menu à la carte kami per kategori: {daftar}",
       "Menu à la carte kami terbagi dalam beberapa kategori: {daftar}"]},

    {"kode": "prix_fixe", "nama": "Set course (Prix Fixe)", "jenis": "info", "frasa_kanonik": "Apa saja menu Prix Fixe?",
     "pola": ["prix fixe", "menu prix fixe", "set course", "menu set course", "paket menu", "menu paket", "degustation", "menu degustation", "gourmand", "menu gourmand", "durasi course"],
     "template": [
       "Berikut set course Prix Fixe kami: {daftar}",
       "Untuk pengalaman makan berurutan dengan harga tetap, inilah pilihan Prix Fixe kami: {daftar}",
       "Kami menyiapkan beberapa set course untuk Anda: {daftar}"]},

    {"kode": "teknik", "nama": "Teknik masakan", "jenis": "info", "frasa_kanonik": "Apa saja teknik masakan yang dipakai?",
     "pola": ["teknik masak", "teknik masakan", "istilah masakan", "istilah memasak", "cara memasak", "sous vide", "confit", "braise", "poele", "saute", "pocher", "flambe", "gratiner", "deglacer", "meuniere"],
     "template": [
       "Berikut istilah teknik masakan yang kami gunakan: {daftar}",
       "Agar lebih mudah memahami menu, ini penjelasan teknik masakan kami: {daftar}",
       "Teknik memasak yang sering muncul pada menu kami: {daftar}"]},

    {"kode": "diet", "nama": "Menu diet dan alergen", "jenis": "info", "frasa_kanonik": "Menu apa saja yang vegetarian, halal, atau tanpa seafood?",
     "pola": ["vegetarian", "halal", "tanpa seafood", "menu diet", "alergi", "alergen", "pantangan makanan"],
     "template": [
       "Berikut menu yang sesuai dengan kebutuhan Anda: {daftar}",
       "Kami telah menyaring menu sesuai pilihan Anda: {daftar}",
       "Pilihan yang cocok untuk kebutuhan tersebut: {daftar}"]},

    {"kode": "harga", "nama": "Menu berdasarkan harga", "jenis": "info", "frasa_kanonik": "Tampilkan menu berdasarkan harga",
     "pola": ["harga", "menu murah", "menu mahal", "menu hemat", "budget", "anggaran", "rentang harga", "di bawah", "di atas", "kurang dari", "lebih dari"],
     "template": [
       "Berikut menu berdasarkan rentang harga: {daftar}",
       "Sesuai anggaran Anda, kami menyarankan menu berikut: {daftar}",
       "Pilihan menu menurut harga: {daftar}"]},

    {"kode": "pairing", "nama": "Informasi pairing", "jenis": "info", "frasa_kanonik": "Apa saja pairing wine dan non-alkohol?",
     "pola": ["pairing", "wine", "anggur", "wine pairing", "pasangan wine", "minuman pendamping", "minuman", "mocktail", "tanpa alkohol", "teh", "jus"],
     "template": [
       "Berikut pairing minuman untuk hidangan kami: {daftar}",
       "Untuk melengkapi hidangan, kami merekomendasikan minuman ini: {daftar}",
       "Pasangan minuman yang kami sarankan untuk hidangan kami: {daftar}"]},

    {"kode": "penutup", "nama": "Penutup", "jenis": "sosial", "frasa_kanonik": null,
     "pola": ["terima kasih", "makasih", "thanks", "thank you", "sampai jumpa", "dadah", "bye", "cukup sekian", "sudah cukup", "selesai"],
     "template": [
       "Terima kasih telah berkunjung. Kami menantikan kedatangan Anda.",
       "Sampai jumpa, semoga hidangan kami berkesan bagi Anda.",
       "Dengan senang hati, kami tunggu kehadiran Anda di meja kami."]},

    {"kode": "fallback", "nama": "Fallback", "jenis": "fallback", "frasa_kanonik": null,
     "pola": [],
     "template": [
       "Mohon maaf, kami belum menangkap maksud pertanyaan Anda.",
       "Maaf, pertanyaan tersebut belum dapat kami jawab.",
       "Mohon maaf, kami belum mengerti. Bisa dijelaskan dengan cara lain?"]}
  ]
}
```

Catatan desain seed:

- Kata “roti” sengaja tidak dipakai sebagai pola teknik karena bentrok dengan kata Indonesia untuk bread.
- Pola `tanpa seafood` cukup satu; varian “non seafood” dan “bebas seafood” ditangani sinonim di `lexicon.json`.
- Setiap `frasa_kanonik` harus diklasifikasikan ke intent-nya sendiri; ini menjadi tes otomatis karena tombol saran mengirim frasa tersebut.

### 13.2 `seed/lexicon.json`

Bobot kata hanya menyimpan pengecualian: 3 untuk kata pembeda, 1 untuk kata umum; kata lain otomatis bobot 2. Token frasa mengikuti hasil penggabungan otomatis dari glosarium (mis. `a_la_carte`, `sous_vide`).

```json
{
  "stopword": ["yang", "di", "ke", "dari", "dan", "atau", "untuk", "dengan", "pada", "ini", "itu", "apa", "apakah", "bagaimana", "berapa",
    "bisa", "boleh", "mau", "ingin", "saya", "aku", "kami", "anda", "kak", "dong", "deh", "ya", "nih", "tolong", "mohon", "saja", "sih",
    "buat", "tentang", "soal", "info", "informasi", "tampilkan", "lihat", "tunjukkan", "ada", "adakah"],

  "sinonim": {
    "gak": "tidak", "nggak": "tidak", "ngga": "tidak", "ga": "tidak", "tdk": "tidak",
    "bgmn": "bagaimana", "gmn": "bagaimana", "jt": "juta", "rb": "ribu",
    "thx": "thanks", "tks": "thanks", "terimakasih": "terima kasih",
    "reservation": "reservasi", "veggie": "vegetarian", "vegetaria": "vegetarian",
    "non seafood": "non_seafood", "tanpa seafood": "non_seafood", "bebas seafood": "non_seafood",
    "non alkohol": "tanpa alkohol"
  },

  "token_weight": {
    "vegetarian": 3, "halal": 3, "non_seafood": 3, "wine": 3, "anggur": 3, "pairing": 3, "mocktail": 3, "alkohol": 3,
    "prix_fixe": 3, "carte_blanche": 3, "a_la_carte": 3, "chef_pick": 3, "set_course": 3, "chef": 3,
    "les_entrees": 3, "les_plats": 3, "les_fromages": 3, "les_desserts": 3, "degustation": 3, "gourmand": 3,
    "reservasi": 3, "harga": 3, "budget": 3, "anggaran": 3, "teknik": 3,
    "sous_vide": 3, "confit": 3, "braise": 3, "poele": 3, "saute": 3, "pocher": 3, "flambe": 3, "gratiner": 3, "deglacer": 3, "meuniere": 3,
    "halo": 3, "hai": 3, "hallo": 3, "permisi": 3, "assalamualaikum": 3, "thanks": 3, "bye": 3, "dadah": 3,
    "menu": 1, "hidangan": 1, "makanan": 1, "minuman": 1, "pilihan": 1, "daftar": 1, "cara": 1, "selamat": 1
  }
}
```

### 13.3 `seed/glossary.json`

Istilah multi-kata di sini otomatis menjadi frasa satu token saat normalisasi. Makna ditulis satu kalimat pendek karena dipakai dua kali: sebagai isi daftar teknik dan sebagai anotasi dalam tanda kurung (R11).

```json
{
  "istilah": [
    {"istilah": "sous-vide", "makna": "memasak dalam kantong vakum dengan air bersuhu rendah yang stabil", "jenis": "teknik"},
    {"istilah": "confit", "makna": "memasak perlahan dalam lemak hingga empuk", "jenis": "teknik"},
    {"istilah": "braisé", "makna": "menumis sebentar lalu memasak perlahan dalam sedikit cairan", "jenis": "teknik"},
    {"istilah": "poêlé", "makna": "memasak dengan wajan dan sedikit lemak hingga kecokelatan", "jenis": "teknik"},
    {"istilah": "sauté", "makna": "menumis cepat dengan api besar dan sedikit minyak", "jenis": "teknik"},
    {"istilah": "pocher", "makna": "merebus perlahan dalam cairan di bawah titik didih", "jenis": "teknik"},
    {"istilah": "flambé", "makna": "menyiram hidangan dengan alkohol lalu membakarnya sebentar", "jenis": "teknik"},
    {"istilah": "gratiner", "makna": "memanggang hingga permukaannya berkerak keemasan", "jenis": "teknik"},
    {"istilah": "déglacer", "makna": "melarutkan sisa masakan di wajan dengan cairan untuk dijadikan saus", "jenis": "teknik"},
    {"istilah": "meunière", "makna": "membalur dengan tepung lalu memasak dengan mentega", "jenis": "teknik"},

    {"istilah": "prix fixe", "makna": "menu paket dengan harga tetap", "jenis": "umum"},
    {"istilah": "carte blanche", "makna": "hidangan yang sepenuhnya dipilihkan oleh chef", "jenis": "umum"},
    {"istilah": "à la carte", "makna": "memesan hidangan satuan dari daftar menu", "jenis": "umum"},
    {"istilah": "chef pick", "makna": "pilihan khusus dari chef", "jenis": "umum"},
    {"istilah": "set course", "makna": "rangkaian hidangan yang disajikan berurutan", "jenis": "umum"},
    {"istilah": "les entrées", "makna": "hidangan pembuka", "jenis": "umum"},
    {"istilah": "les plats", "makna": "hidangan utama", "jenis": "umum"},
    {"istilah": "les fromages", "makna": "hidangan keju", "jenis": "umum"},
    {"istilah": "les desserts", "makna": "hidangan penutup", "jenis": "umum"},
    {"istilah": "dégustation", "makna": "menu cicip beberapa hidangan berukuran kecil", "jenis": "umum"},
    {"istilah": "gourmand", "makna": "menu lengkap dengan beberapa tahap hidangan", "jenis": "umum"}
  ]
}
```

### 13.4 `seed/fixed_text.json`

```json
{
  "diet_disclaimer": "Informasi ini berdasarkan label menu. Untuk alergi berat, mohon konfirmasi langsung kepada staf kami.",
  "tebakan": "Mungkin maksud Anda: {intent}?",
  "kosong": "Mohon maaf, belum ada menu yang cocok dengan kriteria tersebut.",
  "jelajah": "Anda juga dapat menelusuri informasi berikut:"
}
```

### 13.5 `seed/menu.json`

Label diet hanya diberikan bila diyakini benar (label afirmatif); hidangan tanpa label berarti belum berlabel, bukan berarti tidak aman. Urutan hidangan dalam `paket` adalah urutan sajian. Harga `1200000` pada satu hidangan sengaja dipakai untuk menguji batas ≤ 1.200.000.

```json
{
  "label_diet": [
    {"kode": "vegetarian", "nama": "Vegetarian"},
    {"kode": "halal", "nama": "Halal"},
    {"kode": "non_seafood", "nama": "Tanpa seafood"}
  ],

  "kategori": [
    {"nama": "Les Entrées", "urutan": 1},
    {"nama": "Les Plats", "urutan": 2},
    {"nama": "Les Fromages", "urutan": 3},
    {"nama": "Les Desserts", "urutan": 4}
  ],

  "hidangan": [
    {"nama": "Velouté de Champignons", "kategori": "Les Entrées", "harga": 285000,
     "deskripsi": "Sup krim jamur yang halus", "diet": ["vegetarian", "halal", "non_seafood"]},
    {"nama": "Salade de Chèvre Chaud", "kategori": "Les Entrées", "harga": 310000,
     "deskripsi": "Salad dengan keju kambing hangat", "diet": ["vegetarian", "non_seafood"]},
    {"nama": "Tartare de Saumon", "kategori": "Les Entrées", "harga": 365000,
     "deskripsi": "Salmon mentah cincang dengan bumbu segar", "diet": ["halal"]},
    {"nama": "Foie Gras Poêlé", "kategori": "Les Entrées", "harga": 520000,
     "deskripsi": "Hati bebek panggang dengan kulit kecokelatan", "diet": ["non_seafood"]},

    {"nama": "Boeuf Bourguignon", "kategori": "Les Plats", "harga": 890000,
     "deskripsi": "Daging sapi dimasak pelan dalam saus anggur merah", "diet": ["non_seafood"]},
    {"nama": "Risotto aux Truffes", "kategori": "Les Plats", "harga": 760000,
     "deskripsi": "Nasi risotto krim dengan truffle", "diet": ["vegetarian", "halal", "non_seafood"]},
    {"nama": "Canard Confit", "kategori": "Les Plats", "harga": 840000,
     "deskripsi": "Paha bebek yang dimasak pelan dalam lemaknya", "diet": ["non_seafood"]},
    {"nama": "Bar Rôti, Beurre Blanc", "kategori": "Les Plats", "harga": 1250000,
     "deskripsi": "Ikan bar panggang dengan saus mentega putih", "diet": []},
    {"nama": "Filet de Boeuf Rossini", "kategori": "Les Plats", "harga": 1200000,
     "deskripsi": "Fillet sapi dengan foie gras dan saus truffle", "diet": ["non_seafood"]},
    {"nama": "Homard Thermidor", "kategori": "Les Plats", "harga": 1650000,
     "deskripsi": "Lobster panggang dengan saus krim", "diet": []},

    {"nama": "Plateau de Fromages Affinés", "kategori": "Les Fromages", "harga": 320000,
     "deskripsi": "Seleksi keju matang dengan pelengkap", "diet": ["vegetarian", "non_seafood"]},
    {"nama": "Camembert Rôti au Miel", "kategori": "Les Fromages", "harga": 295000,
     "deskripsi": "Camembert panggang dengan madu", "diet": ["vegetarian", "non_seafood"]},

    {"nama": "Tarte Tatin", "kategori": "Les Desserts", "harga": 210000,
     "deskripsi": "Tart apel karamel yang dibalik", "diet": ["vegetarian", "halal", "non_seafood"]},
    {"nama": "Soufflé au Grand Marnier", "kategori": "Les Desserts", "harga": 260000,
     "deskripsi": "Soufflé ringan beraroma likuer jeruk", "diet": ["vegetarian", "non_seafood"]},
    {"nama": "Crème Brûlée", "kategori": "Les Desserts", "harga": 230000,
     "deskripsi": "Krim vanila dengan lapisan karamel renyah", "diet": ["vegetarian", "halal", "non_seafood"]}
  ],

  "paket": [
    {
      "tipe": "prix_fixe",
      "nama": "Menu Dégustation",
      "deskripsi": "Perjalanan cicip 3 tahap yang dirancang sebagai pengantar klasik gastronomi Prancis. Mengusung konsep harmoni esensial, course ini menyajikan transisi rasa dari kelembutan gurih beraroma earthy (Velouté), kedalaman rasa daging dengan saus anggur merah pekat (Boeuf Bourguignon), hingga penutup manis-legit karamel apel renyah (Tarte Tatin).",
      "harga": 1100000,
      "durasi_menit": 90,
      "hidangan": ["Velouté de Champignons", "Boeuf Bourguignon", "Tarte Tatin"]
    },
    {
      "tipe": "prix_fixe",
      "nama": "Menu Gourmand",
      "deskripsi": "Eksplorasi rasa 4 tahap yang memanjakan selera pencinta kuliner Prancis. Mengusung konsep pesta tekstur dan kekayaan terroir, menghadirkan kontras segar-gurih keju kambing hangat, dilanjutkan paha bebek empuk kaya rempah confit, seleksi keju artisanal dengan kedalaman rasa fermentasi, dan ditutup karamel renyah di atas krim vanila lembut dingin.",
      "harga": 1450000,
      "durasi_menit": 120,
      "hidangan": ["Salade de Chèvre Chaud", "Canard Confit", "Plateau de Fromages Affinés", "Crème Brûlée"]
    },
    {
      "tipe": "carte_blanche",
      "nama": "Carte Blanche",
      "deskripsi": "Pengalaman kuliner puncak 5 tahap dengan konsep 'kertas putih', di mana chef bebas mengekspresikan kreativitas harian berdasarkan pasokan bahan musiman terbaik hari ini. Menghadirkan simfoni rasa tak terduga—mulai dari kemewahan luks foie gras, kesegaran tartare laut, keagungan fillet Rossini bertabur truffle, hingga keju lumer dan soufflé hangat beraroma likuer.",
      "harga": 2250000,
      "durasi_menit": 150,
      "hidangan": ["Foie Gras Poêlé", "Tartare de Saumon", "Filet de Boeuf Rossini", "Camembert Rôti au Miel", "Soufflé au Grand Marnier"]
    }
  ]
}
```

### 13.6 `seed/pairing.json`

Pairing ditulis per hidangan agar mudah dibaca; `seed.py` membaliknya menjadi baris `pairing`. Setiap minuman non-alkohol dipakai minimal satu kali, sehingga tamu yang tidak minum alkohol selalu mendapat pilihan.

```json
{
  "minuman": [
    {"nama": "Chablis", "jenis": "wine", "deskripsi": "Anggur putih kering yang segar dengan aroma mineral"},
    {"nama": "Sancerre", "jenis": "wine", "deskripsi": "Anggur putih berasam segar dengan aroma sitrus"},
    {"nama": "Bourgogne Pinot Noir", "jenis": "wine", "deskripsi": "Anggur merah ringan dengan aroma buah beri"},
    {"nama": "Saint-Émilion", "jenis": "wine", "deskripsi": "Anggur merah berbadan penuh dengan tanin lembut"},
    {"nama": "Champagne Brut", "jenis": "wine", "deskripsi": "Anggur bersoda kering dengan gelembung halus"},
    {"nama": "Sauternes", "jenis": "wine", "deskripsi": "Anggur putih manis dengan aroma madu dan aprikot"},
    {"nama": "Teh Hijau Jasmine", "jenis": "non_alkohol", "deskripsi": "Teh hijau beraroma melati yang ringan"},
    {"nama": "Jus Apel Sparkling", "jenis": "non_alkohol", "deskripsi": "Jus apel bersoda yang manis dan segar"},
    {"nama": "Mocktail Sitrus Elderflower", "jenis": "non_alkohol", "deskripsi": "Minuman tanpa alkohol berpadu sitrus dan bunga elder"}
  ],

  "pairing": [
    {"hidangan": "Velouté de Champignons", "minuman": ["Chablis", "Teh Hijau Jasmine"]},
    {"hidangan": "Salade de Chèvre Chaud", "minuman": ["Sancerre"]},
    {"hidangan": "Tartare de Saumon", "minuman": ["Champagne Brut", "Mocktail Sitrus Elderflower"]},
    {"hidangan": "Foie Gras Poêlé", "minuman": ["Sauternes"]},
    {"hidangan": "Boeuf Bourguignon", "minuman": ["Bourgogne Pinot Noir"]},
    {"hidangan": "Risotto aux Truffes", "minuman": ["Chablis", "Mocktail Sitrus Elderflower"]},
    {"hidangan": "Canard Confit", "minuman": ["Bourgogne Pinot Noir"]},
    {"hidangan": "Bar Rôti, Beurre Blanc", "minuman": ["Sancerre"]},
    {"hidangan": "Filet de Boeuf Rossini", "minuman": ["Saint-Émilion"]},
    {"hidangan": "Homard Thermidor", "minuman": ["Champagne Brut"]},
    {"hidangan": "Plateau de Fromages Affinés", "minuman": ["Sauternes"]},
    {"hidangan": "Camembert Rôti au Miel", "minuman": ["Jus Apel Sparkling"]},
    {"hidangan": "Tarte Tatin", "minuman": ["Jus Apel Sparkling", "Sauternes"]},
    {"hidangan": "Soufflé au Grand Marnier", "minuman": ["Champagne Brut"]},
    {"hidangan": "Crème Brûlée", "minuman": ["Teh Hijau Jasmine", "Sauternes"]}
  ]
}
```

### 13.7 `seed/reservasi.json`

Semua isi berikut adalah placeholder yang ditandai “(contoh)”; ganti dengan data restoran sebelum dipakai.

```json
{
  "info": [
    {"label": "Jam operasional", "isi": "Selasa sampai Minggu, pukul 18.00–23.00 (contoh)", "urutan": 1},
    {"label": "Cara reservasi", "isi": "Melalui telepon atau WhatsApp restoran (contoh)", "urutan": 2},
    {"label": "Kontak", "isi": "0812-0000-0000 (contoh, ganti dengan nomor restoran)", "urutan": 3},
    {"label": "Kebijakan pembatalan", "isi": "Pembatalan paling lambat 24 jam sebelum kedatangan (contoh)", "urutan": 4},
    {"label": "Dress code", "isi": "Smart casual (contoh)", "urutan": 5},
    {"label": "Ketentuan Carte Blanche", "isi": "Dipesan oleh seluruh tamu dalam satu meja (contoh)", "urutan": 6}
  ]
}
```

### 13.8 Pemeriksaan seed terhadap aturan data

Pemeriksaan ini dilakukan manual karena `validate_seed.py` belum ada; skrip itu harus mengulangnya secara otomatis.

| Aturan (5.6) | Hasil pada seed |
| --- | --- |
| Harga integer Rupiah > 0 | Lolos: 15 hidangan dan 3 paket |
| Nama hidangan unik | Lolos |
| Label diet hanya yang diyakini benar | Lolos; hidangan seafood sengaja tanpa label `non_seafood` |
| Paket berisi ≥ 1 hidangan yang ada, bernomor 1 sampai n, durasi > 0 | Lolos: paket berisi 3, 4, dan 5 hidangan |
| Intent `info` punya 3 template dengan satu `{daftar}`; `sosial` dan `fallback` 3 template tanpa placeholder | Lolos: 33 template |
| Istilah Prancis di nama kategori, paket, dan template ada di glosarium | Lolos: kategori, `dégustation`, `gourmand`, `carte blanche`, `prix fixe`, `à la carte` |
| Pola tidak kosong setelah normalisasi dan tidak identik antar intent | Lolos pada pemeriksaan manual; skrip perlu memeriksa ulang setelah stopword dan sinonim diterapkan |
| Setiap `frasa_kanonik` diklasifikasikan ke intent-nya sendiri | **Belum teruji**; menunggu engine |

## 14. Knowledge mapping

### 14.1 Peta intent ke pengetahuan

| Intent | Token pembeda (bobot 3) | Entity | Sumber data | Isi `{daftar}` |
| --- | --- | --- | --- | --- |
| `sapaan` | halo, hai, permisi, salam | — | `response_template` | — |
| `reservasi` | reservasi | — | `reservation_info` (6 baris) | Baris “• label: isi” berurutan |
| `carte_blanche` | carte\_blanche, chef\_pick, chef | — | `menu_package` tipe `carte_blanche` → `menu_package_item` → `menu_item` | Nama paket, harga, durasi, hidangan bernomor |
| `a_la_carte` | a\_la\_carte, les\_entrees, les\_plats, les\_fromages, les\_desserts | — | `menu_category` → `menu_item` | Per kategori: nama — deskripsi — harga |
| `prix_fixe` | prix\_fixe, set\_course, degustation, gourmand | — | `menu_package` tipe `prix_fixe` → `menu_package_item` → `menu_item` | Tiap paket: nama, harga, durasi, hidangan bernomor |
| `teknik` | teknik, sous\_vide, confit, braise, poele, saute, pocher, flambe, gratiner, deglacer, meuniere | — | `glossary_term` jenis `teknik` (10 istilah) | “• istilah — makna” |
| `diet` | vegetarian, halal, non\_seafood | Label diet (irisan), harga (opsional) | `menu_item` + `menu_item_diet` + `diet_label` | Hidangan per label, lalu `diet_disclaimer` |
| `harga` | harga, budget, anggaran | Angka, arah (≤ atau >), label diet (opsional) | `menu_item.harga` | Satu kelompok sesuai arah, atau dua kelompok bila tanpa arah |
| `pairing` | pairing, wine, anggur, mocktail, alkohol | — | `pairing` → `beverage` + `menu_item` | “• hidangan: minuman — deskripsi minuman” |
| `penutup` | thanks, bye, dadah | — | `response_template` | — |
| `fallback` | — (hasil keputusan, tidak dinilai) | — | `intent` (tombol saran) + `fixed_text` | Pembuka, tebakan, 8 tombol intent `info` |

```text
sapaan, penutup ────────────► response_template
reservasi ──────────────────► reservation_info
carte_blanche ─┐
prix_fixe ─────┴────────────► menu_package ─► menu_package_item ─► menu_item
a_la_carte ─────────────────► menu_category ─► menu_item
diet ──┐ (label + harga: satu fungsi filter bersama)
harga ─┴────────────────────► menu_item ◄─ menu_item_diet ◄─ diet_label
teknik ─────────────────────► glossary_term (jenis = teknik)
pairing ────────────────────► pairing ─► beverage, menu_item
fallback ───────────────────► intent (tombol saran) + fixed_text
semua intent ───────────────► glossary_term (anotasi makna, R11)
```

### 14.2 Peta hidangan

Label: **V** = vegetarian, **H** = halal, **NS** = tanpa seafood. Kelompok harga mengikuti keputusan PRD: ≤ Rp1.200.000 atau di atasnya.

| Hidangan | Kategori | Harga (Rp) | Kelompok | Label | Paket | Pairing |
| --- | --- | --- | --- | --- | --- | --- |
| Velouté de Champignons | Les Entrées | 285.000 | ≤ | V, H, NS | Menu Dégustation | Chablis, Teh Hijau Jasmine |
| Salade de Chèvre Chaud | Les Entrées | 310.000 | ≤ | V, NS | Menu Gourmand | Sancerre |
| Tartare de Saumon | Les Entrées | 365.000 | ≤ | H | Carte Blanche | Champagne Brut, Mocktail Sitrus Elderflower |
| Foie Gras Poêlé | Les Entrées | 520.000 | ≤ | NS | Carte Blanche | Sauternes |
| Boeuf Bourguignon | Les Plats | 890.000 | ≤ | NS | Menu Dégustation | Bourgogne Pinot Noir |
| Risotto aux Truffes | Les Plats | 760.000 | ≤ | V, H, NS | — | Chablis, Mocktail Sitrus Elderflower |
| Canard Confit | Les Plats | 840.000 | ≤ | NS | Menu Gourmand | Bourgogne Pinot Noir |
| Bar Rôti, Beurre Blanc | Les Plats | 1.250.000 | > | — | — | Sancerre |
| Filet de Boeuf Rossini | Les Plats | 1.200.000 | ≤ (batas) | NS | Carte Blanche | Saint-Émilion |
| Homard Thermidor | Les Plats | 1.650.000 | > | — | — | Champagne Brut |
| Plateau de Fromages Affinés | Les Fromages | 320.000 | ≤ | V, NS | Menu Gourmand | Sauternes |
| Camembert Rôti au Miel | Les Fromages | 295.000 | ≤ | V, NS | Carte Blanche | Jus Apel Sparkling |
| Tarte Tatin | Les Desserts | 210.000 | ≤ | V, H, NS | Menu Dégustation | Jus Apel Sparkling, Sauternes |
| Soufflé au Grand Marnier | Les Desserts | 260.000 | ≤ | V, NS | Carte Blanche | Champagne Brut |
| Crème Brûlée | Les Desserts | 230.000 | ≤ | V, H, NS | Menu Gourmand | Teh Hijau Jasmine, Sauternes |

### 14.3 Peta paket

| Paket | Tipe | Harga (Rp) | Durasi | Konsep, Maksud & Pengalaman Rasa | Urutan sajian |
| --- | --- | --- | --- | --- | --- |
| Menu Dégustation | Prix Fixe | 1.100.000 | 90 menit | Pengantar klasik berkonsep harmoni esensial; alur rasa bertransisi dari kelembutan gurih earthy, kedalaman daging saus anggur merah pekat, hingga manis-legit karamel apel renyah. | 1 Velouté de Champignons → 2 Boeuf Bourguignon → 3 Tarte Tatin |
| Menu Gourmand | Prix Fixe | 1.450.000 | 120 menit | Eksplorasi terroir dan pesta tekstur; alur rasa kontras segar-gurih keju kambing hangat, paha bebek confit kaya rempah, keju artisanal fermentasi pekat, dan karamel vanila renyah-lembut. | 1 Salade de Chèvre Chaud → 2 Canard Confit → 3 Plateau de Fromages Affinés → 4 Crème Brûlée |
| Carte Blanche | Carte Blanche | 2.250.000 | 150 menit | Konsep 'kertas putih' rekomendasi spontan chef hari ini berdasarkan bahan musiman tersegar; simfoni rasa luks tak terduga dari foie gras, kesegaran laut tartare, daging Rossini umami bertruffle, keju lumer, dan soufflé hangat berlikuer. | 1 Foie Gras Poêlé → 2 Tartare de Saumon → 3 Filet de Boeuf Rossini → 4 Camembert Rôti au Miel → 5 Soufflé au Grand Marnier |

### 14.4 Kueri contoh dan hasil yang diharapkan

Hasil dihitung manual dari seed dan akan menjadi golden test setelah engine ada; belum dijalankan.

| Kueri | Intent | Entity | Hasil dari seed |
| --- | --- | --- | --- |
| menu vegetarian di bawah 1,2 juta | `diet` | V; harga ≤ 1.200.000 | 8 hidangan: Velouté, Salade de Chèvre, Risotto, Plateau de Fromages, Camembert, Tarte Tatin, Soufflé, Crème Brûlée |
| menu halal | `diet` | H | 5 hidangan: Velouté, Tartare, Risotto, Tarte Tatin, Crème Brûlée |
| vegetarian dan halal | `diet` | V + H (irisan) | 4 hidangan: Velouté, Risotto, Tarte Tatin, Crème Brûlée |
| menu di bawah 1,2 juta | `harga` | harga ≤ 1.200.000 | 13 hidangan, termasuk Filet de Boeuf Rossini di batas Rp1.200.000 |
| menu di atas 1.200.000 | `harga` | harga > 1.200.000 | 2 hidangan: Bar Rôti dan Homard Thermidor |
| menu tanpa seafood di atas 1.200.000 | `diet` atau `harga` (handler sama) | NS; harga > 1.200.000 | Kosong, sehingga teks `kosong` tampil (kedua hidangan di atas batas tidak berlabel) |
| resrvasi meja | `reservasi` (typo) | — | 6 baris informasi reservasi |
| berapa lama set course | `prix_fixe` | — | 2 paket Prix Fixe dengan durasi 90 dan 120 menit |
