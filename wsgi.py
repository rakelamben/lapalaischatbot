"""
Titik Masuk WSGI Server: Menyediakan instance aplikasi callable untuk server produksi
seperti Gunicorn, uWSGI, atau server lokal Python.
"""

from __future__ import annotations

from app import create_app

# --- Inisialisasi Instance Aplikasi WSGI ---
# Membuat objek aplikasi tunggal menggunakan konfigurasi default lingkungan.
app = create_app()

if __name__ == "__main__":
    # Menjalankan server pengembangan jika dipanggil langsung via python wsgi.py
    app.run(host="127.0.0.1", port=5000, debug=True)
