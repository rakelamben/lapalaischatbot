"""
Antarmuka Baris Perintah (CLI) Interaktif LaPalaisChatBot:
Memungkinkan pengujian alur percakapan, rotasi template respon, saran fallback,
dan inspeksi kalkulasi skor NLU langsung melalui terminal sebelum peluncuran web.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path
from typing import Any

# Konfigurasi encoding UTF-8 untuk konsol Windows agar karakter aksen Prancis
# (misal: purée, flambé, à la carte) dan simbol format tercetak sempurna.
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stdin and hasattr(sys.stdin, "reconfigure"):
    sys.stdin.reconfigure(encoding="utf-8")

from app.config import Config
from app.engine.params import EngineParams
from app.engine.snapshot import NluSnapshot
from app.services.chat_service import ChatService


# --- Fungsi Format Tampilan Konsol Terminal ---
# Menata format pencetakan teks pesan, saran kanonik, dan tabel rincian debug NLU
# agar mudah dibaca oleh evaluator di lingkungan terminal.
def print_banner() -> None:
    print("=" * 66)
    print("       LA PALAIS RESTAURANT — VIRTUAL CONCIERGE TERMINAL")
    print("=" * 66)
    print(" Perintah khusus:")
    print("   /debug  - Mengaktifkan / menonaktifkan rincian NLU")
    print("   /reset  - Mengosongkan riwayat template percakapan")
    print("   /help   - Menampilkan panduan bantuan ini")
    print("   /exit   - Keluar dari sesi interaktif (atau ketik 'exit')")
    print("=" * 66 + "\n")


def print_debug_info(debug_data: dict[str, Any]) -> None:
    print("\n" + "-" * 28 + " [NLU DEBUG] " + "-" * 28)
    dec = debug_data.get("decision", {})
    latency = debug_data.get("latency_ms", 0.0)
    print(f" * Keputusan Intent : {dec.get('intent')} (Alasan: {dec.get('alasan')})")
    print(f" * Parameter        : tau={dec.get('tau')}, delta={dec.get('delta')}, rho={dec.get('rho')}")
    print(f" * Latensi Engine   : {latency} ms")

    tokens = debug_data.get("tokens", [])
    print(f" * Token Bersih     : {tokens}")

    entities = debug_data.get("entities", {})
    if entities:
        print(f" * Entitas          : {entities}")

    print("\n   Peringkat 10 Intent:")
    print("   " + "-" * 58)
    print(f"   {'Intent':<20} | {'Skor':<7} | {'Jaccard':<8} | {'Fuzzy':<7} | {'Cakupan':<7}")
    print("   " + "-" * 58)
    for r in debug_data.get("ranking", []):
        highlight = " <-- DIPILIH" if r.get("intent") == dec.get("intent") else ""
        print(
            f"   {r.get('intent'):<20} | {r.get('skor'):<7.4f} | "
            f"{r.get('jaccard'):<8.4f} | {r.get('fuzzy'):<7.4f} | "
            f"{r.get('cakupan'):<7.4f}{highlight}"
        )
    print("   " + "-" * 58)
    print("-" * 66 + "\n")


# --- Inisialisasi Layanan & Siklus Utama REPL ---
# Membuka basis data SQLite, memuat snapshot konfigurasi NLU ke memori,
# dan menjalankan perulangan baca-evaluasi-cetak (REPL) untuk interaksi pesan tamu.
def main() -> None:
    db_path = Config.DB_PATH
    if not db_path.exists():
        print(f"[ERROR] Database tidak ditemukan di: {db_path}")
        print("Jalankan skrip seeding terlebih dahulu: python scripts/seed.py --reset")
        sys.exit(1)

    print("Memuat model dan data NLU La Palais...")
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        snapshot = NluSnapshot.from_db(conn)
    finally:
        conn.close()

    params_path = Config.ENGINE_CONFIG_PATH
    params = EngineParams.from_file(params_path) if params_path.exists() else EngineParams()
    chat_service = ChatService(snapshot=snapshot, params=params, db_path=db_path)

    print_banner()

    is_debug = False
    prev_template_id: int | None = None

    while True:
        try:
            prompt_label = "Tamu [DEBUG]" if is_debug else "Tamu"
            raw_input = input(f"{prompt_label} > ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\nAu revoir! Terima kasih telah mengunjungi La Palais.")
            break

        if not raw_input:
            continue

        # Evaluasi perintah terminal khusus
        cmd = raw_input.lower()
        if cmd in ("/exit", "exit", "quit", ":q"):
            print("\nAu revoir! Sampai jumpa di La Palais.")
            break

        if cmd == "/debug":
            is_debug = not is_debug
            status = "AKTIF" if is_debug else "NON-AKTIF"
            print(f"\n[SISTEM] Mode Debug NLU sekarang: {status}\n")
            continue

        if cmd == "/reset":
            prev_template_id = None
            print("\n[SISTEM] Sesi percakapan direset (rotasi template dikosongkan).\n")
            continue

        if cmd == "/help":
            print_banner()
            continue

        # Eksekusi pesan melalui ChatService
        try:
            result = chat_service.handle_message(
                message=raw_input,
                prev_template_id=prev_template_id,
                is_debug=is_debug,
            )
        except Exception as exc:
            print(f"\n[ERROR SISTEM] Gagal memproses pesan: {exc}\n")
            continue

        # Tampilkan balasan concierge
        print(f"\nLa Palais Concierge:\n{result.get('reply')}\n")

        # Tampilkan saran tombol jika tersedia (misal saat intent fallback)
        suggestions = result.get("suggestions", [])
        if suggestions:
            print("Saran Pertanyaan:")
            for s in suggestions:
                print(f"  • {s.get('label')}: \"{s.get('frasa')}\"")
            print()

        # Tampilkan panel inspeksi NLU jika debug aktif
        if is_debug and "debug" in result:
            print_debug_info(result["debug"])

        # Perbarui ID template terakhir untuk mencegah repetisi kalimat pembuka
        prev_template_id = result.get("template_id")


if __name__ == "__main__":
    main()
