# Seed Data — LaPalaisChatBot

Direktori ini berisi data awal (*single source of truth*) untuk membangun basis data SQLite `data/lapalais.db` menggunakan `scripts/seed.py`.

## Daftar File
1. `intents.json`: 11 intent (10 dinilai + fallback), pola pertanyaan alami, dan 3 template respons per intent.
2. `lexicon.json`: Daftar stopword domain-aware, kamus sinonim/normalisasi, dan bobot token khusus (bobot 3 untuk pembeda, bobot 1 untuk umum; default 2).
3. `glossary.json`: Istilah-istilah kuliner Prancis (umum dan teknik) beserta maknanya dalam satu kalimat bahasa Indonesia (digunakan untuk daftar teknik dan anotasi glosarium otomatis R11).
4. `fixed_text.json`: Teks-teks tetap sistem seperti `diet_disclaimer`, format `tebakan`, pesan hasil `kosong`, dan teks ajakan `jelajah`.
5. `menu.json`: Kategori menu, hidangan *à la carte*, penetapan label diet (afirmasi), dan paket course (*Prix Fixe* dan *Carte Blanche*).
6. `pairing.json`: Daftar minuman (wine & non-alkohol) dan hidangan pasangannya.
7. `reservasi.json`: Rincian informasi reservasi (jam, kontak, dress code, ketentuan).

## Aturan Data (Model Data PRD R5 & SD 5.6)
* Harga disimpan dalam integer Rupiah > 0.
* Nama hidangan unik, deskripsi bahasa Indonesia hasil parafrase.
* Label diet hanya diberikan bila terbukti (label afirmatif).
* Setiap paket berdurasi menit > 0, memiliki deskripsi naratif yang menjelaskan konsep, tujuan, dan alur pengalaman rasa, serta berisi hidangan yang valid dengan urutan berurutan (1..n).
* Template intent kategori `info` wajib memiliki tepat satu placeholder `{daftar}`. Template kategori `sosial` dan `fallback` tidak boleh memiliki `{daftar}`.
* Setiap istilah Prancis pada nama kategori, paket, atau template wajib terdaftar di `glossary.json`.
