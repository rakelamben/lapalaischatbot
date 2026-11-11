"""
Repository data SQLite untuk LaPalaisChatBot.
Satu-satunya modul dalam sistem yang memuat kueri SQL.
"""

from __future__ import annotations

import json
import sqlite3
from typing import Any


class Repository:
    # --- Inisialisasi Koneksi ---
    # Memastikan row_factory selalu sqlite3.Row agar data baris dapat diakses via nama kolom.
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn
        self.conn.row_factory = sqlite3.Row

    # --- Kueri Menu À La Carte & Kategori ---
    # Mengambil seluruh kategori menu berurutan dan mengelompokkan hidangan di bawah tiap kategori.
    def get_menu_categories(self) -> list[dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute("SELECT id, nama, urutan FROM menu_category ORDER BY urutan ASC;")
        return [dict(r) for r in cur.fetchall()]

    def get_menu_items_grouped_by_category(self) -> dict[str, list[dict[str, Any]]]:
        cur = self.conn.cursor()
        cur.execute("""
            SELECT i.id, i.nama, i.deskripsi, i.harga, c.nama AS kategori
            FROM menu_item i
            JOIN menu_category c ON c.id = i.kategori_id
            ORDER BY c.urutan ASC, i.harga ASC;
        """)
        grouped: dict[str, list[dict[str, Any]]] = {}
        for row in cur.fetchall():
            d = dict(row)  # Ubah sqlite3.Row menjadi dictionary untuk payload service/API.
            kat = d["kategori"]  # Nama kategori menjadi kunci pengelompokan hidangan.
            if kat not in grouped:
                grouped[kat] = []
            grouped[kat].append(d)
        return grouped

    # --- Kueri Filter Harga dan Diet (Relasional) ---
    # Menggabungkan filter harga (batas_le / batas_gt) dan irisan label diet.
    # Jika beberapa label diet diminta (misal vegetarian + halal), kueri menggunakan json_each
    # dan klausa HAVING COUNT(DISTINCT l.kode) = :n_label untuk memastikan hidangan memenuhi SEMUA label tersebut.
    def filter_menu_items(
        self,
        batas_le: int | None = None,
        batas_gt: int | None = None,
        diet_codes: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        cur = self.conn.cursor()
        diet_list = diet_codes or []
        n_label = len(diet_list)  # Jumlah label yang harus dipenuhi sekaligus oleh satu hidangan.
        kode_label_json = json.dumps(diet_list)  # Dikirim sebagai JSON agar dapat dibaca fungsi SQLite json_each.

        query = """
            SELECT i.id, i.nama, i.deskripsi, i.harga, c.nama AS kategori
            FROM menu_item i
            JOIN menu_category c ON c.id = i.kategori_id
            WHERE (:batas_le IS NULL OR i.harga <= :batas_le)
              AND (:batas_gt IS NULL OR i.harga > :batas_gt)
              AND (:n_label = 0 OR i.id IN (
                    SELECT d.item_id
                    FROM menu_item_diet d
                    JOIN diet_label l ON l.id = d.diet_id
                    WHERE l.kode IN (SELECT value FROM json_each(:kode_label))
                    GROUP BY d.item_id
                    HAVING COUNT(DISTINCT l.kode) = :n_label
              ))
            ORDER BY c.urutan ASC, i.harga ASC;
        """
        cur.execute(
            query,
            {
                "batas_le": batas_le,
                "batas_gt": batas_gt,
                "n_label": n_label,
                "kode_label": kode_label_json,
            },
        )
        return [dict(r) for r in cur.fetchall()]

    # --- Kueri Paket Course (Prix Fixe & Carte Blanche) ---
    # Mengambil paket course beserta narasi konsep, maksud, profil rasa, durasi,
    # dan seluruh daftar hidangan di dalamnya yang terurut berdasarkan urutan sajian (1..n).
    def get_packages(self, tipe: str | None = None) -> list[dict[str, Any]]:
        cur = self.conn.cursor()
        if tipe:
            cur.execute(
                "SELECT id, tipe, nama, deskripsi, harga, durasi_menit FROM menu_package WHERE tipe = ? ORDER BY harga ASC;",
                (tipe,),
            )
        else:
            cur.execute("SELECT id, tipe, nama, deskripsi, harga, durasi_menit FROM menu_package ORDER BY harga ASC;")

        packages: list[dict[str, Any]] = []
        for pkg_row in cur.fetchall():
            pkg = dict(pkg_row)
            cur.execute(
                """
                SELECT i.id, i.nama, i.deskripsi, i.harga, pi.urutan
                FROM menu_package_item pi
                JOIN menu_item i ON i.id = pi.item_id
                WHERE pi.package_id = ?
                ORDER BY pi.urutan ASC;
                """,
                (pkg["id"],),
            )
            pkg["hidangan"] = [dict(r) for r in cur.fetchall()]
            packages.append(pkg)
        return packages

    # --- Kueri Pairing Minuman & Hidangan ---
    # Mengambil pasangan hidangan dengan minuman (anggur dan non-alkohol) beserta deskripsinya.
    def get_pairings(self) -> list[dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute("""
            SELECT i.nama AS hidangan, b.nama AS minuman, b.deskripsi AS deskripsi_minuman, b.jenis
            FROM pairing p
            JOIN menu_item i ON i.id = p.item_id
            JOIN beverage b ON b.id = p.beverage_id
            JOIN menu_category c ON c.id = i.kategori_id
            ORDER BY c.urutan ASC, i.id ASC, b.jenis DESC;
        """)
        return [dict(r) for r in cur.fetchall()]

    # --- Kueri Informasi Reservasi & Istilah Teknik ---
    # Mengambil ketentuan reservasi terurut dan glosarium istilah teknik memasak Prancis.
    def get_reservation_info(self) -> list[dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute("SELECT id, label, isi, urutan FROM reservation_info ORDER BY urutan ASC;")
        return [dict(r) for r in cur.fetchall()]

    def get_technique_terms(self) -> list[dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute("SELECT id, istilah, makna FROM glossary_term WHERE jenis = 'teknik' ORDER BY istilah ASC;")
        return [dict(r) for r in cur.fetchall()]

    # --- Kueri Saran Tombol Kanonik & Intent ---
    # Mengambil daftar frasa kanonik intent info untuk tombol penjelajahan topik saat fallback.
    def get_info_suggestions(self, exclude_kode: str | None = None) -> list[dict[str, str]]:
        cur = self.conn.cursor()
        cur.execute("""
            SELECT kode, nama, frasa_kanonik
            FROM intent
            WHERE jenis = 'info' AND frasa_kanonik IS NOT NULL
            ORDER BY id ASC;
        """)
        results: list[dict[str, str]] = []
        for row in cur.fetchall():
            d = dict(row)
            if exclude_kode and d["kode"] == exclude_kode:
                continue
            results.append({"kode": d["kode"], "label": d["nama"], "frasa": d["frasa_kanonik"]})
        return results

    def get_intent_by_code(self, kode: str) -> dict[str, Any] | None:
        cur = self.conn.cursor()
        cur.execute("SELECT id, kode, nama, jenis, frasa_kanonik FROM intent WHERE kode = ?;", (kode,))
        row = cur.fetchone()
        return dict(row) if row else None

    # --- Logging Riwayat Percakapan ---
    # Menyimpan pesan pengguna, keputusan intent, serta skor dan entitas dalam bentuk JSON valid ke tabel chat_log.
    def log_chat(
        self,
        pesan: str,
        intent_id: int,
        skor_json: str,
        entitas_json: str | None = None,
    ) -> int:
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO chat_log (pesan, intent_id, skor, entitas)
            VALUES (?, ?, ?, ?);
            """,
            (pesan, intent_id, skor_json, entitas_json),
        )
        self.conn.commit()
        return cur.lastrowid

    # --- Kueri Agregasi Analitik & Monitoring Database ---
    # Menghitung metrik ringkasan interaksi (total chat, rasio sukses vs fallback,
    # distribusi frekuensi 10 intent, dan jumlah record tabel master restoran).
    def get_analytics_summary(self) -> dict[str, Any]:
        cur = self.conn.cursor()

        # 1. Total chat dan rasio klasifikasi
        cur.execute("""
            SELECT 
                COUNT(cl.id) AS total_chat,
                COALESCE(SUM(CASE WHEN i.kode = 'fallback' THEN 1 ELSE 0 END), 0) AS total_fallback,
                COALESCE(SUM(CASE WHEN i.kode != 'fallback' THEN 1 ELSE 0 END), 0) AS total_success
            FROM chat_log cl
            JOIN intent i ON i.id = cl.intent_id;
        """)
        row = cur.fetchone()
        # Nilai agregat dipisahkan supaya persentase fallback dan keberhasilan konsisten saat belum ada log.
        total_chat = row["total_chat"] if row else 0
        total_fallback = row["total_fallback"] if row else 0
        total_success = row["total_success"] if row else 0
        success_rate = round((total_success / total_chat * 100), 1) if total_chat > 0 else 100.0

        # 2. Distribusi 10 intent
        cur.execute("""
            SELECT i.kode, i.nama, COUNT(cl.id) AS jumlah
            FROM intent i
            LEFT JOIN chat_log cl ON cl.intent_id = i.id
            GROUP BY i.id, i.kode, i.nama
            ORDER BY jumlah DESC;
        """)
        intent_distribution: list[dict[str, Any]] = []
        for r in cur.fetchall():
            cnt = r["jumlah"]  # Banyaknya log yang menunjuk intent ini.
            pct = round((cnt / total_chat * 100), 1) if total_chat > 0 else 0.0  # Porsi intent terhadap seluruh log.
            intent_distribution.append({
                "kode": r["kode"],
                "nama": r["nama"],
                "jumlah": cnt,
                "persen": pct,
            })

        # 3. Hitungan entri data master restoran
        table_counts: dict[str, int] = {}
        for tbl in ["menu_item", "menu_package", "beverage", "pairing", "glossary_term", "reservation_info"]:
            cur.execute(f"SELECT COUNT(*) AS total FROM {tbl};")
            table_counts[tbl] = cur.fetchone()["total"]

        return {
            "total_chat": total_chat,
            "total_success": total_success,
            "total_fallback": total_fallback,
            "success_rate": success_rate,
            "intent_distribution": intent_distribution,
            "table_counts": table_counts,
        }

    # --- Kueri Riwayat Log Percakapan Terbaru ---
    # Mengambil daftar catatan interaksi dari tabel chat_log terurut dari yang terbaru
    # beserta data relasi intent dan metadata skor/entitas.
    def get_recent_chat_logs(self, limit: int = 50) -> list[dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT 
                cl.id, 
                cl.dibuat_pada, 
                cl.pesan, 
                cl.intent_id,
                i.kode AS intent_kode, 
                i.nama AS intent_nama, 
                cl.skor, 
                cl.entitas
            FROM chat_log cl
            JOIN intent i ON i.id = cl.intent_id
            ORDER BY cl.id DESC
            LIMIT ?;
            """,
            (limit,),
        )
        return [dict(r) for r in cur.fetchall()]
