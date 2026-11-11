# LaPalaisChatBot

Chatbot informasi untuk restoran fine dining Prancis La Palais. Aplikasi mengenali maksud pesan dengan NLU rule-based (tanpa model ML/LLM), mengambil informasi dari SQLite, lalu menyusun jawaban dari template.

## Fitur

- Menjawab pertanyaan tentang sapaan, reservasi, Carte Blanche, menu à la carte, Prix Fixe, teknik masak, diet, harga, pairing, dan penutup.
- Menormalisasi aksen, sinonim, frasa kuliner, angka harga, serta toleransi typo.
- Memeringkat intent menggunakan gabungan skor Jaccard, fuzzy, dan cakupan berbobot; intent yang tidak memenuhi ambang akan diarahkan ke fallback.
- Mengambil menu dan informasi restoran dari SQLite yang dibangun dari file JSON di `seed/`.
- Menampilkan antarmuka chat web, serta halaman debug dan analitik yang dapat diaktifkan secara terpisah.

Chatbot memproses setiap pesan secara mandiri. Bot memberikan informasi reservasi, tetapi tidak membuat booking. Label diet bukan jaminan keamanan alergi; tamu tetap perlu mengonfirmasi kebutuhan alergi kepada staf.

## Persyaratan

- Python 3.11 atau lebih baru
- pip

## Menyiapkan dan menjalankan

Jalankan perintah berikut dari direktori utama proyek. Contoh aktivasi virtual environment ini menggunakan PowerShell di Windows:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Validasi file seed, lalu bangun database SQLite:

```powershell
python scripts/validate_seed.py
python scripts/seed.py
```

Database default dibuat di `data/lapalais.db`. Jalankan antarmuka web lokal:

```powershell
python wsgi.py
```

Buka <http://127.0.0.1:5000/>. Untuk percakapan melalui terminal, gunakan `python cli.py`; perintah `/debug` mengaktifkan atau menonaktifkan rincian analisis, `/reset` mengosongkan ID template sebelumnya, dan `/help` menampilkan bantuan.

> **Perhatian:** `scripts/seed.py` mengisi ulang tabel data dan menghapus riwayat `chat_log`. Opsi `--reset` menghapus file database pada path yang dituju sebelum membuatnya kembali. Jangan gunakan opsi tersebut pada database yang berisi data yang ingin dipertahankan.

## Konfigurasi

Salin `.env.example` menjadi `.env`, lalu sesuaikan nilainya bila perlu:

| Variabel | Fungsi | Default |
| --- | --- | --- |
| `DB_PATH` | Lokasi file database SQLite | `data/lapalais.db` |
| `ENABLE_DEBUG` | Mendaftarkan halaman dan API debug/analitik | `0` (nonaktif) |
| `ENGINE_CONFIG_PATH` | Lokasi parameter scoring NLU | `config/engine.json` |
| `SECRET_KEY` | Kunci sesi Flask | Nilai pengembangan dari aplikasi |

`ENABLE_DEBUG=1` membuka halaman `/debug` dan `/analytic`, serta API internal yang menampilkan skor dan data analisis. Aktifkan hanya di lingkungan lokal atau tepercaya; biarkan nonaktif pada deployment publik. File `config/engine.json` mengatur bobot skor, ambang penerimaan intent (`tau`), margin antarperingkat (`delta`), batas tebakan fallback (`rho`), dan parameter terkait.

Catatan: `.env.example` mengatur `ENABLE_DEBUG=1` untuk penggunaan lokal. Ubah nilainya menjadi `0` sebelum menjalankan aplikasi di lingkungan publik.

## API

Endpoint publik:

- `GET /healthz` — pemeriksaan kesiapan layanan dan koneksi database.
- `POST /api/chat` — menerima JSON dengan `message` (atau alias `pesan`) dan `prev_template_id` opsional.

Contoh permintaan:

```json
{
  "message": "Ada menu vegetarian?"
}
```

Respons chat berisi `reply`, `template_id`, `suggestions`, dan `content`. Hasil terstruktur dapat menyertakan `content_type`. Pesan harus berisi teks dan maksimal 500 karakter.

Jika `ENABLE_DEBUG=1`, endpoint tambahan tersedia:

- `POST /api/debug/chat` — respons chat beserta token, entitas, ranking intent, dan alasan keputusan.
- `POST /api/debug/reload` — memuat ulang snapshot NLU dari database.
- `GET /analytic/summary` dan `GET /analytic/logs?limit=50` — ringkasan serta riwayat analitik.

## Data dan alur pemrosesan

File JSON di `seed/` adalah sumber data untuk intent, leksikon, glosarium, menu, pairing, reservasi, dan teks tetap. `scripts/validate_seed.py` memeriksa konsistensi file tersebut; `scripts/seed.py` memuatnya ke SQLite.

Untuk setiap pesan, engine menormalisasi teks dan mengekstrak entitas harga/diet, menghitung ranking intent, lalu memutuskan intent atau fallback. Handler intent mengambil data yang sesuai melalui repository SQLite. Responder memilih template dan mengembalikan teks serta data terstruktur. `Analysis` adalah objek hasil analisis NLU yang memuat pesan asli, token, entitas, ranking, keputusan, dan latensi; objek ini juga digunakan oleh handler dan mode debug.

## Pengujian

Instal dependensi pengembangan dan jalankan test suite:

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest
```

Test menggunakan database sementara yang di-seed dari data proyek, sehingga tidak memerlukan database lokal produksi.

## Struktur proyek

```text
app/
  api/          Endpoint chat, validasi, debug, dan analitik
  data/         Koneksi dan query SQLite
  engine/       Normalisasi, scoring, keputusan, entitas, handler, respons
  services/     Orkestrasi layanan chat
  static/       CSS, JavaScript, dan aset antarmuka
  templates/    Halaman HTML
config/         Parameter engine NLU
migrations/     Skema database SQLite
scripts/        Validasi seed dan pembuatan database
seed/           Sumber data JSON
tests/          Unit test dan test integrasi API
```

Dokumen kebutuhan dan rancangan teknis lebih rinci tersedia di [PRD — LaPalaisChatBot.md](./PRD%20%E2%80%94%20LaPalaisChatBot.md) dan [System Design — LaPalaisChatBot.md](./System%20Design%20%E2%80%94%20LaPalaisChatBot.md).
