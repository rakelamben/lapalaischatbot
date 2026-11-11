"""
Pengujian Integrasi API Flask LaPalaisChatBot:
Memverifikasi fungsionalitas endpoint publik (/api/chat, /healthz, /),
isolasi fisik rute debug (/api/debug/*, /debug) via konfigurasi ENABLE_DEBUG,
validasi error input, serta persistensi pencatatan log ke chat_log.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
import pytest
from flask.testing import FlaskClient

from app import create_app
from app.config import Config


# --- Fixture Konfigurasi Pengujian Aplikasi Flask ---
# Menyiapkan dua varian instance aplikasi:
# 1. app_debug: ENABLE_DEBUG=True (memuat blueprint debug untuk pengujian alat inspeksi internal).
# 2. app_no_debug: ENABLE_DEBUG=False (memastikan endpoint debug benar-benar 404 Not Found di mode publik).
@pytest.fixture
def app_debug(temp_db_path: Path):
    class DebugConfig(Config):
        TESTING = True
        ENABLE_DEBUG = True
        DB_PATH = temp_db_path

    return create_app(config_class=DebugConfig)


@pytest.fixture
def app_no_debug(temp_db_path: Path):
    class ProdConfig(Config):
        TESTING = True
        ENABLE_DEBUG = False
        DB_PATH = temp_db_path

    return create_app(config_class=ProdConfig)


@pytest.fixture
def client_debug(app_debug) -> FlaskClient:
    return app_debug.test_client()


@pytest.fixture
def client_no_debug(app_no_debug) -> FlaskClient:
    return app_no_debug.test_client()


# --- Pengujian Endpoint Kesiapan & Halaman Publik ---
# Memastikan /healthz mengembalikan status ok dan beranda (/) merender HTML antarmuka tamu.
def test_healthz(client_no_debug: FlaskClient) -> None:
    resp = client_no_debug.get("/healthz")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data == {"status": "ok"}


def test_index_page(client_no_debug: FlaskClient) -> None:
    resp = client_no_debug.get("/")
    assert resp.status_code == 200
    assert "La Palais" in resp.get_data(as_text=True)


# --- Pengujian Percakapan Publik & Isolasi Kebocoran Data Debug ---
# Memastikan /api/chat merespons dengan format standar (reply, template_id, suggestions)
# dan TIDAK PERNAH membocorkan field 'debug' atau nilai bobot kalkulasi kepada tamu publik.
def test_chat_success_without_debug_leak(client_no_debug: FlaskClient) -> None:
    payload = {"pesan": "halo selamat malam"}
    resp = client_no_debug.post("/api/chat", json=payload)

    assert resp.status_code == 200
    data = resp.get_json()
    assert "reply" in data
    assert len(data["reply"]) > 0
    assert "template_id" in data
    assert "suggestions" in data
    assert "debug" not in data, "Endpoint publik dilarang keras membocorkan metadata debug"


def test_chat_structured_content_has_renderer_type(client_no_debug: FlaskClient) -> None:
    resp = client_no_debug.post("/api/chat", json={"pesan": "tampilkan menu a la carte"})

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["content_type"] == "a_la_carte"
    assert isinstance(data["content"], list)
    assert "kategori" in data["content"][0]


# --- Pengujian Validasi Input & Kode Error Terstandarisasi ---
# Menguji skenario input abnormal (pesan kosong, spasi semata, string > 500 karakter,
# serta format payload JSON yang salah) menghasilkan HTTP 400 dengan struktur error standar.
def test_chat_validation_errors(client_no_debug: FlaskClient) -> None:
    # 1. Pesan kosong
    resp = client_no_debug.post("/api/chat", json={"pesan": ""})
    assert resp.status_code == 400
    err = resp.get_json()["error"]
    assert err["code"] == "pesan_kosong"

    # 2. Pesan hanya spasi putih
    resp = client_no_debug.post("/api/chat", json={"pesan": "    \t\n  "})
    assert resp.status_code == 400
    assert resp.get_json()["error"]["code"] == "pesan_kosong"

    # 3. Pesan melebihi batas 500 karakter
    long_msg = "a" * 501
    resp = client_no_debug.post("/api/chat", json={"pesan": long_msg})
    assert resp.status_code == 400
    assert resp.get_json()["error"]["code"] == "pesan_terlalu_panjang"

    # 4. JSON tidak valid atau bukan dict
    resp = client_no_debug.post(
        "/api/chat",
        data="bukan json",
        content_type="application/json",
    )
    assert resp.status_code == 400
    assert resp.get_json()["error"]["code"] == "json_tidak_valid"


# --- Pengujian Isolasi Fisik Rute Debug & Analitik (ENABLE_DEBUG=0) ---
# Memastikan saat ENABLE_DEBUG=False, seluruh rute internal (/api/debug/chat, /api/debug/reload,
# halaman /debug, halaman /analytic, dan API /analytic/***) mengembalikan 404 Not Found secara mutlak.
def test_debug_endpoints_disabled_when_flag_off(client_no_debug: FlaskClient) -> None:
    resp_chat = client_no_debug.post("/api/debug/chat", json={"pesan": "halo"})
    assert resp_chat.status_code == 404

    resp_reload = client_no_debug.post("/api/debug/reload")
    assert resp_reload.status_code == 404

    resp_debug_page = client_no_debug.get("/debug")
    assert resp_debug_page.status_code == 404

    resp_analytic_page = client_no_debug.get("/analytic")
    assert resp_analytic_page.status_code == 404

    resp_analytic_summary = client_no_debug.get("/analytic/summary")
    assert resp_analytic_summary.status_code == 404

    resp_analytic_logs = client_no_debug.get("/analytic/logs")
    assert resp_analytic_logs.status_code == 404


# --- Pengujian Fungsionalitas Debug Saat Aktif (ENABLE_DEBUG=1) ---
# Memastikan /api/debug/chat menyediakan rincian komprehensif engine NLU
# (ranking 10 intent, token bersih, ekstraksi entitas, parameter tau/delta/rho, dan latensi),
# serta /api/debug/reload berhasil memuat ulang konfigurasi tanpa restart.
def test_debug_endpoints_enabled(client_debug: FlaskClient) -> None:
    # 1. Uji /api/debug/chat
    payload = {"pesan": "ada menu apa saja"}
    resp = client_debug.post("/api/debug/chat", json=payload)
    assert resp.status_code == 200

    data = resp.get_json()
    assert "reply" in data
    assert "debug" in data

    debug_info = data["debug"]
    assert "ranking" in debug_info
    assert len(debug_info["ranking"]) == 10
    assert "decision" in debug_info
    assert "tau" in debug_info["decision"]
    assert "delta" in debug_info["decision"]
    assert "rho" in debug_info["decision"]
    assert "latency_ms" in debug_info
    assert "tokens" in debug_info
    assert "entities" in debug_info

    # 2. Uji /api/debug/reload
    reload_resp = client_debug.post("/api/debug/reload")
    assert reload_resp.status_code == 200
    assert reload_resp.get_json() == {"status": "reloaded"}

    # 3. Uji /debug halaman web
    page_resp = client_debug.get("/debug")
    assert page_resp.status_code == 200
    assert "Debug" in page_resp.get_data(as_text=True)


# --- Pengujian Persistensi Log Percakapan (chat_log) ---
# Memverifikasi bahwa setiap interaksi pada /api/chat tersimpan dengan benar di tabel chat_log
# mencakup teks pesan, relasi foreign key intent_id, serta JSON valid pada kolom skor dan entitas.
def test_chat_logging_persists_to_db(client_no_debug: FlaskClient, temp_db_path: Path) -> None:
    # Kirim pesan reservasi
    msg = "saya mau reservasi meja untuk besok"
    resp = client_no_debug.post("/api/chat", json={"pesan": msg})
    assert resp.status_code == 200

    # Periksa tabel chat_log di database
    conn = sqlite3.connect(temp_db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM chat_log ORDER BY id DESC LIMIT 1;")
    row = cur.fetchone()
    conn.close()

    assert row is not None
    assert row["pesan"] == msg
    assert row["intent_id"] is not None

    # Validasi bahwa kolom skor dan entitas tersimpan sebagai JSON valid
    scores = json.loads(row["skor"])
    assert isinstance(scores, list)
    assert len(scores) == 10
    assert "intent" in scores[0]
    assert "skor" in scores[0]


# --- Pengujian Endpoint & Halaman Analitik Saat Aktif (ENABLE_DEBUG=1) ---
# Memastikan /analytic merender antarmuka visual dashboard analitik,
# serta API /analytic/summary dan /analytic/logs mengembalikan data teragregasi yang valid.
def test_analytic_page_and_api_endpoints_enabled(client_debug: FlaskClient) -> None:
    # 1. Kirim obrolan uji agar chat_log memiliki setidaknya 1 baris data
    client_debug.post("/api/chat", json={"pesan": "rekomendasi wine untuk steak"})

    # 2. Uji Halaman HTML /analytic
    page_resp = client_debug.get("/analytic")
    assert page_resp.status_code == 200
    assert "Analitik" in page_resp.get_data(as_text=True)

    # 3. Uji Endpoint Ringkasan Statistik /analytic/summary
    summary_resp = client_debug.get("/analytic/summary")
    assert summary_resp.status_code == 200
    data = summary_resp.get_json()

    assert "total_chat" in data
    assert data["total_chat"] >= 1
    assert "success_rate" in data
    assert "intent_distribution" in data
    assert len(data["intent_distribution"]) >= 10
    assert "table_counts" in data
    assert data["table_counts"]["menu_item"] > 0
    assert data["table_counts"]["glossary_term"] > 0

    # 4. Uji Endpoint Log Riwayat /analytic/logs
    logs_resp = client_debug.get("/analytic/logs?limit=10")
    assert logs_resp.status_code == 200
    logs_data = logs_resp.get_json()
    assert "logs" in logs_data
    assert len(logs_data["logs"]) >= 1
    assert "pesan" in logs_data["logs"][0]
    assert "intent_kode" in logs_data["logs"][0]
