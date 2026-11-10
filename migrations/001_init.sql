PRAGMA foreign_keys = ON;
PRAGMA user_version = 1;

-- NLU: intent, pola, template, teks tetap
CREATE TABLE IF NOT EXISTS intent (
  id            INTEGER PRIMARY KEY,
  kode          TEXT NOT NULL UNIQUE,            -- 'diet', 'harga', ...
  nama          TEXT NOT NULL,                   -- label tombol dan debug
  jenis         TEXT NOT NULL CHECK (jenis IN ('info','sosial','fallback')),
  frasa_kanonik TEXT,                            -- dikirim tombol saran
  CHECK ((jenis = 'info') = (frasa_kanonik IS NOT NULL))
);

CREATE TABLE IF NOT EXISTS intent_pattern (
  id        INTEGER PRIMARY KEY,
  intent_id INTEGER NOT NULL REFERENCES intent(id) ON DELETE CASCADE,
  pola      TEXT NOT NULL,
  UNIQUE (intent_id, pola)
);

CREATE TABLE IF NOT EXISTS response_template (
  id        INTEGER PRIMARY KEY,
  intent_id INTEGER NOT NULL REFERENCES intent(id) ON DELETE CASCADE,
  isi       TEXT NOT NULL,                       -- info: memuat {daftar}
  UNIQUE (intent_id, isi)
);

CREATE TABLE IF NOT EXISTS fixed_text (
  kunci TEXT PRIMARY KEY,
  isi   TEXT NOT NULL
);

-- Leksikon
CREATE TABLE IF NOT EXISTS stopword (
  kata TEXT PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS synonym (
  varian  TEXT PRIMARY KEY,
  kanonik TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS token_weight (       -- hanya pengecualian; default 2
  token TEXT PRIMARY KEY,
  bobot INTEGER NOT NULL CHECK (bobot IN (1, 3))
);

CREATE TABLE IF NOT EXISTS glossary_term (
  id      INTEGER PRIMARY KEY,
  istilah TEXT NOT NULL UNIQUE COLLATE NOCASE,
  makna   TEXT NOT NULL,                         -- satu kalimat pendek
  jenis   TEXT NOT NULL DEFAULT 'umum' CHECK (jenis IN ('umum','teknik'))
);

-- Menu
CREATE TABLE IF NOT EXISTS menu_category (
  id     INTEGER PRIMARY KEY,
  nama   TEXT NOT NULL UNIQUE,
  urutan INTEGER NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS menu_item (
  id          INTEGER PRIMARY KEY,
  nama        TEXT NOT NULL UNIQUE COLLATE NOCASE,
  deskripsi   TEXT NOT NULL,                     -- bahasa Indonesia
  kategori_id INTEGER NOT NULL REFERENCES menu_category(id),
  harga       INTEGER NOT NULL CHECK (harga > 0) -- Rupiah
);

CREATE TABLE IF NOT EXISTS diet_label (
  id   INTEGER PRIMARY KEY,
  kode TEXT NOT NULL UNIQUE,                     -- vegetarian, halal, non_seafood
  nama TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS menu_item_diet (
  item_id INTEGER NOT NULL REFERENCES menu_item(id)  ON DELETE CASCADE,
  diet_id INTEGER NOT NULL REFERENCES diet_label(id) ON DELETE CASCADE,
  PRIMARY KEY (item_id, diet_id)
) WITHOUT ROWID;

CREATE TABLE IF NOT EXISTS menu_package (
  id           INTEGER PRIMARY KEY,
  tipe         TEXT NOT NULL CHECK (tipe IN ('prix_fixe','carte_blanche')),
  nama         TEXT NOT NULL UNIQUE,
  deskripsi    TEXT NOT NULL,                             -- konsep, tujuan, & pengalaman rasa
  harga        INTEGER NOT NULL CHECK (harga > 0),        -- Rupiah
  durasi_menit INTEGER NOT NULL CHECK (durasi_menit > 0)  -- durasi total course
);

CREATE TABLE IF NOT EXISTS menu_package_item (
  package_id INTEGER NOT NULL REFERENCES menu_package(id) ON DELETE CASCADE,
  item_id    INTEGER NOT NULL REFERENCES menu_item(id),
  urutan     INTEGER NOT NULL CHECK (urutan > 0),         -- urutan sajian
  PRIMARY KEY (package_id, item_id),
  UNIQUE (package_id, urutan)
) WITHOUT ROWID;

CREATE TABLE IF NOT EXISTS beverage (
  id        INTEGER PRIMARY KEY,
  nama      TEXT NOT NULL UNIQUE,
  deskripsi TEXT NOT NULL,                                -- bahasa Indonesia
  jenis     TEXT NOT NULL CHECK (jenis IN ('wine','non_alkohol'))
);

CREATE TABLE IF NOT EXISTS pairing (
  item_id     INTEGER NOT NULL REFERENCES menu_item(id) ON DELETE CASCADE,
  beverage_id INTEGER NOT NULL REFERENCES beverage(id)  ON DELETE CASCADE,
  PRIMARY KEY (item_id, beverage_id)
) WITHOUT ROWID;

CREATE TABLE IF NOT EXISTS reservation_info (
  id     INTEGER PRIMARY KEY,
  label  TEXT NOT NULL UNIQUE,                   -- 'Jam operasional', ...
  isi    TEXT NOT NULL,
  urutan INTEGER NOT NULL
);

-- Log (P1)
CREATE TABLE IF NOT EXISTS chat_log (
  id          INTEGER PRIMARY KEY,
  dibuat_pada TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
  pesan       TEXT NOT NULL,
  intent_id   INTEGER NOT NULL REFERENCES intent(id),  -- hasil keputusan
  skor        TEXT NOT NULL CHECK (json_valid(skor)),  -- semua intent + komponen
  entitas     TEXT CHECK (entitas IS NULL OR json_valid(entitas))
);

CREATE INDEX IF NOT EXISTS ix_menu_item_kategori ON menu_item(kategori_id);
CREATE INDEX IF NOT EXISTS ix_menu_item_harga    ON menu_item(harga);
CREATE INDEX IF NOT EXISTS ix_item_diet_diet     ON menu_item_diet(diet_id);
CREATE INDEX IF NOT EXISTS ix_pkg_item_item      ON menu_package_item(item_id);
CREATE INDEX IF NOT EXISTS ix_pairing_beverage   ON pairing(beverage_id);
CREATE INDEX IF NOT EXISTS ix_pattern_intent     ON intent_pattern(intent_id);
CREATE INDEX IF NOT EXISTS ix_template_intent    ON response_template(intent_id);
