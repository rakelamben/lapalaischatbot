# PRD — LaPalaisChatBot

**Chatbot rule-based untuk menu digital restoran fine dining Prancis** · Pemilik: Jas · Draf v0.3 · 9 November 2026

> Ringkasan satu kalimat: LaPalaisChatBot menjawab pertanyaan tamu tentang reservasi, menu, teknik masak, diet/alergen, harga, dan pairing wine dengan mengenali **intent** lewat skor matematis (Jaccard + Fuzzy + Cakupan), lalu membalas dengan **variasi kalimat** yang isi datanya selalu sama. Tanpa flow percakapan.

## 1. Problem Statement

Tamu restoran fine dining Prancis sering bingung dengan istilah menu (*Carte Blanche*, *Prix Fixe*, *Les Fromages*, teknik seperti *sous-vide* atau *confit*) dan butuh jawaban cepat soal diet, alergen, harga, serta pairing wine sebelum atau saat memesan. Informasi ini biasanya tersebar di PDF menu atau hanya bisa ditanyakan ke staf, sehingga lambat dan bergantung pada ketersediaan orang. Tanpa kanal tanya-jawab yang konsisten, tamu bisa salah memilih menu (misalnya tidak halal atau mengandung seafood) dan restoran kehilangan kesempatan menjual menu bernilai tinggi.

Proyek ini juga berfungsi sebagai studi kasus teknis: membuktikan bahwa pengenalan intent berbasis aturan dan kemiripan teks (tanpa data latih dan tanpa model ML) cukup akurat untuk domain sempit dengan 11 intent.

## 2. Goals

**Tujuan pengguna**

1. Tamu mendapat jawaban yang benar untuk pertanyaan menu dalam satu kali tanya, tanpa harus melewati alur bertahap.
2. Tamu dengan kebutuhan diet/alergen (vegetarian, halal, non-seafood) bisa menemukan menu yang sesuai dengan cepat.

**Tujuan teknis/proyek**

3. Pengenalan intent akurat: **≥ 85%** pada set uji held-out (stretch: 92%).
4. Pesan di luar topik ditangani rapi: **≥ 90%** pesan out-of-scope jatuh ke fallback, dan **≤ 10%** pesan valid salah jatuh ke fallback.
5. Konsistensi data: **100%** variasi respons dalam satu intent memuat daftar data yang identik (diverifikasi tes otomatis).
6. Hasil evaluasi bisa dilaporkan secara ilmiah: ada ablation (tiap komponen skor vs gabungan) dan confusion matrix.

## 3. Non-Goals

- **Flow / dialog multi-turn.** Tiap pesan diproses mandiri, tanpa konteks pesan sebelumnya. Alasan: batasan desain proyek; fokus pada kualitas intent dan variasi output.
- **Transaksi reservasi atau pemesanan.** Bot hanya memberi informasi reservasi (jam, kontak, ketentuan), tidak membuat booking. Alasan: butuh sistem eksternal dan flow.
- **Jawaban generatif (LLM) atau model ML terlatih.** Alasan: tujuan proyek adalah pendekatan matematis yang bisa dijelaskan.
- **Rekomendasi personal atau memori tamu.** Alasan: butuh state dan data pengguna.
- **Nasihat alergi medis.** Bot hanya mencocokkan label menu (vegetarian, halal, non-seafood). Alasan: risiko kesehatan, selalu diarahkan konfirmasi ke staf.

## 4. User Stories

**Tamu umum**

- Sebagai tamu, saya ingin disapa dan dijawab dengan ramah supaya merasa disambut.
- Sebagai tamu, saya ingin tahu cara dan ketentuan reservasi supaya bisa datang tanpa antre atau ditolak.
- Sebagai tamu, saya ingin melihat menu *à la carte* per kategori (Les Entrées, Les Plats, Les Fromages, Les Desserts) supaya bisa memilih sesuai selera.
- Sebagai tamu yang bingung memilih, saya ingin memahami paket Prix Fixe (set course terstruktur dengan harmoni rasa terencana) serta Carte Blanche (rekomendasi kejutan chef hari ini dengan kreasi bebas bahan musiman) agar paham konsep dan pengalaman rasa yang akan dinikmati.
- Sebagai tamu yang awam, saya ingin penjelasan istilah teknik masak supaya paham yang saya pesan.
- Sebagai tamu, saya ingin tahu pairing wine untuk menu supaya pengalaman makan terasa lengkap.

**Tamu dengan kebutuhan khusus dan anggaran**

- Sebagai tamu vegetarian/halal/non-seafood, saya ingin daftar menu yang sesuai supaya aman memesan.
- Sebagai tamu dengan anggaran terbatas, saya ingin melihat menu sampai dengan Rp1.200.000 supaya tidak melebihi budget.
- Sebagai tamu yang ingin pengalaman premium, saya ingin melihat menu di atas Rp1.200.000.

**Kasus tepi**

- Sebagai tamu yang salah ketik ("resrvasi", "vegetarain"), saya tetap ingin dimengerti.
- Sebagai tamu yang bertanya di luar topik, saya ingin dijawab sopan dan diberi contoh pertanyaan yang bisa dijawab bot.
- Sebagai tamu yang menulis dua hal sekaligus ("halo, mau reservasi"), saya ingin tetap mendapat jawaban yang relevan.

## 5. Katalog Intent (11 intent)

Setiap intent punya **3 variasi kalimat** dengan data yang sama. Contoh pola hanya ilustrasi; daftar pola lengkap disusun dari seed data.

| # | Intent | Contoh pola | Variasi | Data tetap |
| --- | --- | --- | --- | --- |
| 1 | Sapaan | halo, selamat malam, hai | 3 | — |
| 2 | Informasi reservasi | reservasi, booking meja, jam buka | 3 | Jam, kontak, ketentuan reservasi (dari seed data) |
| 3 | Carte Blanche (chef pick) | carte blanche, pilihan chef, chef pick | 3 | Menu rekomendasi chef hari ini, beserta konsep kejutan 'kertas putih', tujuan, dan pengalaman rasa musiman |
| 4 | Menu à la carte | menu satuan, entrée, plat, fromage, dessert | 3 | Menu 4 kategori |
| 5 | Set course (Prix Fixe) | prix fixe, set course, paket menu | 3 | Daftar set course beserta konsep, tujuan alur sajian, durasi, dan pengalaman rasa terstruktur |
| 6 | Teknik masakan | teknik masak, sous vide, confit, apa itu | 3 | Daftar 8–12 istilah beserta definisi satu kalimat |
| 7 | Diet/alergen | vegetarian, halal, tanpa seafood | 3 | Daftar menu per label |
| 8 | Menu berdasarkan harga | di bawah 1,2 juta, di atas 1.200.000, budget | 3 | Daftar menu per rentang (≤ dan > Rp1.200.000) |
| 9 | Informasi pairing (wine dan non-alkohol) | wine, pairing, anggur, mocktail, tanpa alkohol, teh, jus | 3 | Daftar pairing wine dan non-alkohol |
| 10 | Penutup | terima kasih, sampai jumpa | 3 | — |
| 11 | Fallback | (skor di bawah ambang) | 3 | Tebakan intent teratas + daftar intent lain untuk ditelusuri |

## 6. Requirements

### Must-Have (P0)

**R1. Preprocessing teks.** Lowercase, hapus aksen (*Entrées* → *entrees*), normalisasi angka ("1.200.000", "1,2 juta", "1.2jt" → 1200000), gabung frasa multi-kata jadi satu token (*prix fixe* → *prix\_fixe*, *carte blanche*, *à la carte*), buang stopword (daftar kecil dan domain-aware: kata "menu" tetap dipakai tetapi berbobot rendah), dan petakan ±20 sinonim informal (mis. gak/nggak, bgmn/bagaimana, jt/juta) termasuk istilah Inggris umum seperti menu, wine, reservation. Daftar frasa multi-kata dihimpun dari seed data (lihat R5), bukan ditetapkan manual; daftar minimum: prix fixe, carte blanche, à la carte, chef pick, set course, les entrées, les plats, les fromages, les desserts.

- Given pesan "Ada menu Entrées?" When diproses Then token mengandung "entrees" dan tidak mengandung "ada" sebagai kata kunci.
- Given pesan "di bawah 1,2 juta" When diproses Then angka terbaca 1200000.
- Given pesan "Prix Fixe" atau "prix fixe" When diproses Then keduanya menjadi token yang sama.

**R2. Mesin skor intent.** Skor intent = **maks** skor semua pola intent tersebut (bukan menggabung semua pola jadi satu bag). Skor satu pola = 0,4 × Jaccard + 0,3 × Fuzzy + 0,3 × Cakupan, dengan definisi:

- **Jaccard**: irisan kata ÷ gabungan kata (setelah stopword dibuang).
- **Fuzzy**: level **token** — tiap kata pola dicocokkan ke kata pesan terbaik dengan `difflib.SequenceMatcher`; dihitung cocok jika rasio ≥ 0,8; skor = rasio kata pola yang cocok.
- **Cakupan**: seperti Fuzzy tetapi **berbobot** (kata pembeda seperti *vegetarian*, *wine*, *prix\_fixe* bernilai lebih tinggi daripada kata umum seperti *menu*).
- Bobot 0,4/0,3/0,3 adalah baseline; kombinasi lain (mis. 50/20/30, 34/33/33) diuji dan dilaporkan di ablation, dan jika lebih baik di held-out maka dipakai (lihat R8). Bobot kata pada Cakupan manual 3 tingkat: kata pembeda = 3, kata domain = 2, kata umum = 1; IDF otomatis hanya menjadi pembanding di ablation.

Acceptance criteria:

- Given pesan "resrvasi meja" When dihitung Then intent *reservasi* mendapat skor tertinggi walau ada typo.
- Given pesan "menu vegetarian" When dihitung Then intent *diet* mengalahkan *à la carte* dan *Carte Blanche* meski ketiganya memuat kata "menu".
- Skor selalu di rentang 0–1 dan deterministik (pesan sama → skor sama).

**R3. Aturan keputusan.** Pilih intent berskor tertinggi jika **skor ≥ τ** dan **selisih dengan peringkat 2 ≥ δ**. Jika skor < τ → fallback. Jika selisih < δ → gunakan aturan prioritas di bawah. Nilai awal τ = 0,45 dan δ ≈ 0,10 (titik awal); keduanya dioptimalkan lewat tuning dan visualisasi distribusi skor.

- Given pesan "cuaca hari ini bagaimana?" When diproses Then intent = fallback.
- Given pesan "halo" When diproses Then intent = sapaan dengan skor ≥ τ.
- Given dua intent berskor hampir sama When diproses Then keputusan mengikuti aturan prioritas, bukan acak.

**Aturan prioritas** (dipakai saat selisih < δ):

- Sapaan dan penutup berprioritas terendah: jika ada intent informasi yang lolos τ, jawab intent itu.
- Pesan harga atau diet dijawab sebagai satu intent dengan filter entity (R4), bukan dua intent.
- Selain itu, intent dengan kata kunci pembeda berbobot lebih tinggi menang.

**R4. Ekstraksi entity harga dan diet (regex, bukan kemiripan teks).** Deteksi angka dan kata arah ("bawah/kurang/murah" vs "atas/lebih/mahal"), lalu filter daftar menu. Deteksi label diet (vegetarian, halal, non-seafood). Entity dipakai untuk memilih **subset data**, bukan mengubah intent.

- Given pesan "menu di bawah 1,2 juta" When diproses Then yang ditampilkan hanya menu berharga ≤ 1.200.000, dan respons menulis "sampai dengan Rp1.200.000".
- Given pesan "menu di atas 1.200.000" When diproses Then yang ditampilkan hanya menu berharga > 1.200.000.
- Given pesan "menu vegetarian di bawah 1,2 juta" When diproses Then hasil = irisan label vegetarian dan rentang harga tersebut (jika kosong, bot menyatakan tidak ada menu yang cocok, bukan fallback).

**R5. Knowledge base sebagai sumber data tunggal.** Seluruh menu, harga, label diet, teknik, set course (termasuk deskripsi konsep, tujuan, dan profil pengalaman rasa untuk *Prix Fixe* dan *Carte Blanche*), dan pairing disimpan terstruktur di satu tempat (mis. JSON/dict) dan dibangun dari seed data berupa sample data kecil sesuai model data (scraping dilakukan nanti saat pengembangan, mengikuti aturan model data; seed data memuat informasi reservasi, pairing wine dan non-alkohol, serta 8–12 istilah teknik masakan beserta definisi satu kalimat). Skema atau model data ditentukan di dokumen System Design terpisah, bukan di PRD ini. Template kalimat hanya memuat placeholder (`{daftar}`), tidak memuat data langsung. Khusus untuk *Carte Blanche*, respons template mencerminkan karakter otentik rekomendasi chef hari ini yang spontan dan dinamis berdasarkan bahan musiman terbaik.

- Given data menu berubah di knowledge base When bot dijalankan ulang Then semua variasi respons ikut berubah tanpa mengedit template.
- Tes otomatis memastikan tiap variasi dalam satu intent merender daftar data yang identik.

**R6. Respons bervariasi.** Semua 11 intent (termasuk penutup dan fallback) punya 3 template kalimat dengan susunan kalimat berbeda. Pemilihan acak dengan aturan **tidak mengulang template yang sama dengan balasan sebelumnya** untuk intent yang sama.

- Given intent yang sama dipanggil dua kali berturut-turut When respons dipilih Then template ke-2 berbeda dari yang ke-1 (berlaku juga untuk fallback dan penutup).

**R7. Disclaimer diet/alergen.** Setiap respons intent diet/alergen menyertakan satu kalimat tetap: informasi berdasarkan label menu dan alergi berat sebaiknya dikonfirmasi ke staf.

- Given intent diet/alergen When respons dirender Then kalimat konfirmasi ke staf selalu muncul di semua variasi.

**R8. Set uji dan evaluator.** 20 kalimat uji per intent (≈ 220 total) ditambah 30 kalimat di luar topik, campuran formal, informal, typo, dan multi-intent, dibagi 70% tuning dan 30% held-out. Skrip evaluasi menghasilkan akurasi, confusion matrix, metrik fallback, dan visualisasi distribusi skor per intent (dipakai untuk memilih τ). Bobot komponen, τ, dan δ dicari lewat grid search pada set tuning saja.

- Given set held-out When evaluator dijalankan Then keluar akurasi per intent dan confusion matrix.
- Given konfigurasi berubah When evaluator dijalankan ulang Then hasil dapat direproduksi (seed dan data uji tetap).

**R9. Antarmuka minimal.** Antarmuka web berbasis Flask untuk demo dan uji: menerima teks dan menampilkan balasan.

- Given pengguna mengirim pesan When bot memproses Then balasan tampil dalam < 1 detik.

**R10. Respons fallback yang membantu.** Jika keputusan = fallback, bot membalas dengan kalimat pembuka (3 variasi) lalu dua bagian tetap: (1) tebakan "Mungkin maksud Anda …" untuk intent berskor tertinggi (tebakan disembunyikan jika skor teratas < ρ ≈ 0,15; nilai awal yang dituning), dan (2) daftar jenis intent lain yang bisa ditelusuri, mis. info reservasi, menu set course, dan seterusnya. Daftar ini tampil sebagai tombol yang mengirim satu frasa kanonik per intent (stateless): fungsinya memberi tahu topik yang tersedia, bukan untuk mengetik pilihan, sehingga tidak ada flow.

- Given pesan "cuaca hari ini bagaimana?" When diproses Then respons memuat daftar intent yang bisa ditelusuri.
- Given pesan "mau pesan tempat buat besok" dengan skor tertinggi pada reservasi tetapi < τ When diproses Then respons memuat tebakan "Mungkin maksud Anda: informasi reservasi".
- Given dua fallback berturut-turut When respons dipilih Then kalimat pembukanya berbeda.

**R11. Istilah Prancis selalu disertai makna.** Setiap kemunculan istilah Prancis di respons (mis. *Les Entrées*, *Les Fromages*, *confit*) diikuti makna bahasa Indonesia, bukan hanya saat pertama muncul. Glosarium istilah menjadi bagian dari seed data (R5).

- Given respons memuat istilah dari glosarium When dirender Then tiap kemunculan istilah diikuti maknanya dalam tanda kurung.
- Tes otomatis memeriksa seluruh template dan data terhadap aturan ini.

### Nice-to-Have (P1)

- **Mode debug**: tampilkan intent terpilih, skor tiap komponen, dan peringkat seluruh 11 intent untuk tiap pesan; tidak ditampilkan di mode biasa.
- **Logging** pesan, skor dan peringkat seluruh intent, serta keputusan akhir (untuk analisis salah klasifikasi).
- **Penanganan multi-intent**: untuk kasus "sapaan + intent lain", bot menjawab intent lain dengan salam singkat di depan.
- **Ablation otomatis**: skrip membandingkan Jaccard saja, Fuzzy saja, Cakupan saja, gabungan, dan pembanding TF-IDF + cosine.

### Future Considerations (P2)

Dirancang agar mudah ditambah nanti, tidak dibangun di v1:

- Pencarian level **hidangan** ("apa itu foie gras?", "harga Boeuf Bourguignon?") dengan entity per menu.
- Dukungan bahasa Inggris dan campuran Indonesia–Inggris.
- Alur reservasi sungguhan atau integrasi booking.
- Konteks multi-turn / flow.
- Dukungan alergen tambahan (kacang, gluten, susu).

## 7. Success Metrics

Target berikut adalah hipotesis awal dan akan dikalibrasi setelah set uji pertama selesai.

**Leading indicators (hari–minggu setelah engine jadi)**

| Metrik | Target sukses | Stretch | Cara ukur |
| --- | --- | --- | --- |
| Akurasi intent (held-out) | ≥ 85% | ≥ 92% | Skrip evaluasi |
| Fallback benar pada out-of-scope | ≥ 90% | ≥ 95% | Skrip evaluasi |
| Salah fallback pada pesan valid | ≤ 10% | ≤ 5% | Skrip evaluasi |
| Ketahanan typo (1 huruf salah per kata kunci) | ≥ 80% benar | ≥ 90% | Set uji typo |
| Konsistensi data antar variasi | 100% | 100% | Tes otomatis |
| Waktu respons | < 1 s | < 100 ms | Pengukuran di antarmuka |

**Lagging indicators (uji pengguna setelah demo)**

| Metrik | Target sukses | Cara ukur |
| --- | --- | --- |
| Task success rate (penguji berhasil mendapat info yang dicari) | ≥ 80% | Uji ke 8–10 orang dengan 5 tugas |
| Kepuasan jawaban (skala 1–5) | ≥ 4,0 | Kuesioner singkat |
| Variasi terasa tidak monoton | ≥ 70% penguji setuju | Kuesioner singkat |

## 8. Open Questions

Semua pertanyaan dari draf v0.1 dan v0.2 sudah dijawab Jas, jadi tidak ada Open Question yang tersisa. Seluruh keputusan dicatat di 8.1.

### 

| Asal | Topik | Keputusan | Dampak |
| --- | --- | --- | --- |
| v0.1 #1 | Ambang intent τ | 0,45 (bukan 0,35); dioptimalkan lewat tuning dan visualisasi data | R3, R8 |
| v0.1 #2 | Bobot skor | 40/30/30 sebagai baseline; kombinasi lain diuji di ablation | R2 |
| v0.1 #3 | Aturan prioritas | Sapaan dan penutup terendah; harga dan diet = satu intent + filter entity; selain itu kata pembeda berbobot lebih tinggi menang | R3 |
| v0.1 #4 | Bobot kata Cakupan | Manual 3 tingkat (3/2/1); IDF hanya pembanding di ablation | R2 |
| v0.1 #5 | Stopword dan sinonim | Stopword kecil domain-aware ("menu" tetap, berbobot rendah); ±20 sinonim | R1 |
| v0.1 #6 | Frasa multi-kata | Dihimpun dari seed data (sample kecil dulu); model data ditentukan di dokumen System Design | R1, R5 |
| v0.1 #7 | Harga tepat Rp1.200.000 | Masuk kelompok ≤ 1.200.000; respons menulis "sampai dengan Rp1.200.000" | R4 |
| v0.1 #8 | Harga dan diet | Entity (regex), bukan intent terpisah; intent tetap 11 | R3, R4 |
| v0.1 #9 | Pairing non-alkohol | Ditambahkan ke data pairing | Tabel intent, R5 |
| v0.1 #10 | Label diet | Vegetarian, halal, non-seafood; alergen lain di P2 | R7, P2 |
| v0.1 #11 | Informasi reservasi | Isi ditentukan oleh seed data | R5 |
| v0.1 #12 | Teknik masakan | Definisi satu kalimat per istilah; 8–12 istilah | R5 |
| v0.1 #13 | Variasi respons | 3 variasi untuk semua intent, termasuk penutup dan fallback | R6, tabel intent |
| v0.1 #14 | Isi fallback | Dibuat sistem: tebakan "Mungkin maksud Anda …" dari intent berskor tertinggi + daftar intent lain untuk ditelusuri | R10 |
| v0.1 #15 | Nada bot | Sopan dan hangat; istilah Prancis selalu disertai makna Indonesia | R11 |
| v0.1 #16 | Bahasa input | Indonesia; istilah Inggris umum lewat sinonim; Inggris penuh di P2 | R1, P2 |
| v0.1 #18 | Logging dan debug | Tampilkan semua peringkat intent | P1 |
| v0.1 #19 | Kanal demo | Flask | R9 |
| v0.1 #20 | Pembanding metode | TF-IDF + cosine hanya di ablation | P1 |
| OQ-1 | Set uji | 20 kalimat per intent (≈ 220) + 30 out-of-scope; 70% tuning, 30% held-out; campuran formal, informal, typo, multi-intent | R8 |
| OQ-2 | Nama intent 9 | Diganti menjadi "Informasi pairing" (wine dan non-alkohol); pola tambahan mocktail, tanpa alkohol, teh, jus | Tabel intent |
| OQ-3 | Scraping | Ditunda: tetapkan model data dan sample data kecil dulu; scraping dilakukan saat pengembangan mengikuti aturan model data. Scraping hanya sebagai referensi, teks diparafrase, kurs tetap dicatat | R5, Timeline |
| OQ-4 | Opsi pada fallback | Tombol kanonik (stateless) untuk memberi tahu topik yang tersedia, bukan untuk diketik; tetap tanpa flow. Tebakan disembunyikan jika skor teratas < ρ ≈ 0,15 | R10 |
| OQ-5 | Margin δ | ≈ 0,10 sebagai titik awal, dioptimalkan bersama τ lewat grid search | R3 |
| OQ-6 | Peringkat intent | Hanya tampil di mode debug | P1 |

### 8.2 Open Questions tersisa

Tidak ada. Pertanyaan baru dicatat di sini saat dokumen System Design dan implementasi berjalan.

## 9. Timeline Considerations

Belum ada tenggat tetap yang diketahui; urutan berikut adalah usulan fase, bukan jadwal.

- **Fase 0 — Data dan uji (prasyarat).** Tetapkan model data dan isi sample data kecil (menu, harga, label, pairing wine dan non-alkohol, teknik, informasi reservasi), lalu susun set uji. Scraping ditunda ke fase pengembangan. Skema data ditulis di dokumen System Design terpisah.
- **Fase 1 — Engine dasar.** Preprocessing (R1), skor (R2), keputusan (R3), entity (R4), generator respons (R5–R7, R10–R11).
- **Fase 2 — Evaluasi dan tuning.** Evaluator (R8), grid search bobot/τ/δ, ablation, perbaikan pola dari confusion matrix.
- **Fase 3 — Antarmuka dan uji pengguna.** Antarmuka Flask (R9), uji ke 8–10 orang, laporan.

**Dependensi utama:** Fase 1 tidak bisa selesai tanpa knowledge base (Fase 0), dan Fase 2 tidak bisa dimulai tanpa set uji. Kualitas pola intent lebih menentukan akurasi daripada tuning bobot, jadi alokasikan waktu untuk memperkaya pola setelah putaran evaluasi pertama.
