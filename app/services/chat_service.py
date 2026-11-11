"""
Layanan ChatService: Menghubungkan antarmuka API dengan engine NLU dan database SQLite.
Mengorkestrasikan pemrosesan pesan masuk, rotasi template respon, pencatatan log interaksi ke tabel chat_log,
serta pembentukan payload respon untuk klien reguler dan konsol debug internal.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path
from typing import Any

from app.data.repository import Repository
from app.engine import process_message
from app.engine.params import EngineParams
from app.engine.snapshot import NluSnapshot

logger = logging.getLogger(__name__)


class ChatService:
    # --- Inisialisasi Layanan Chat ---
    # Menerima snapshot NLU in-memory, parameter konfigurasi scoring, dan path database SQLite.
    def __init__(
        self,
        snapshot: NluSnapshot,
        params: EngineParams,
        db_path: Path | str,
    ) -> None:
        self.snapshot = snapshot
        self.params = params
        self.db_path = Path(db_path)

    # --- Pemuatan Ulang Snapshot (Hot Reload) ---
    # Digunakan oleh endpoint debug /api/debug/reload untuk memperbarui cache snapshot
    # tanpa mematikan atau me-restart aplikasi server.
    def reload_snapshot(self) -> None:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            self.snapshot = NluSnapshot.from_db(conn)
        finally:
            conn.close()

    # --- Pemrosesan Pesan Tamu ---
    # 1. Membuka koneksi database jangka pendek per request (thread-safe).
    # 2. Menjalankan engine NLP dan handler bisnis melalui process_message.
    # 3. Menyimpan riwayat percakapan ke tabel chat_log secara fail-safe (error log tidak membatalkan respon pengguna).
    # 4. Menyusun format keluaran JSON (mode publik tanpa debug vs mode debug internal).
    def handle_message(
        self,
        message: str,
        prev_template_id: int | None = None,
        is_debug: bool = False,
    ) -> dict[str, Any]:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            repo = Repository(conn)
            reply = process_message(
                message=message,
                snapshot=self.snapshot,
                params=self.params,
                repo=repo,
                prev_template_id=prev_template_id,
            )

            # Simpan log chat secara fail-safe (PRD Logging P1)
            self._log_chat_safe(repo, message, reply)

            # Format respon untuk klien publik
            response_data: dict[str, Any] = {
                "reply": reply.text,
                "template_id": reply.template_id,
                "suggestions": reply.suggestions,
                "content": reply.content,  # Data mentah dari handler intent (misal: daftar reservasi)
            }
            if isinstance(reply.content, list) and reply.analysis:
                response_data["content_type"] = reply.analysis.decision.intent

            # Tambahkan blok debug jika request berasal dari endpoint debug internal
            if is_debug and reply.analysis:
                response_data["debug"] = reply.analysis.to_debug_dict(self.params)

            return response_data
        finally:
            conn.close()

    # --- Pencatatan Log Riwayat Percakapan (Fail-Safe) ---
    # Ekstraksi metadata intent, skor, dan entitas ke tabel chat_log.
    # Dibungkus blok try-except agar kegagalan I/O atau serialisasi database
    # tidak pernah menyebabkan error 500 pada pengalaman tamu restoran.
    def _log_chat_safe(self, repo: Repository, message: str, reply: Any) -> None:
        if not reply.analysis:
            return

        try:
            decision_intent = reply.analysis.decision.intent
            intent_obj = self.snapshot.intents.get(decision_intent)
            if intent_obj:
                intent_id = intent_obj.id
            else:
                fallback_obj = self.snapshot.intents.get("fallback")
                intent_id = fallback_obj.id if fallback_obj else 1

            skor_data = [r.to_dict() for r in reply.analysis.ranking]
            skor_json = json.dumps(skor_data, ensure_ascii=False)

            entitas_data = reply.analysis.entities.to_dict()
            entitas_json = json.dumps(entitas_data, ensure_ascii=False) if entitas_data else None

            repo.log_chat(
                pesan=message,
                intent_id=intent_id,
                skor_json=skor_json,
                entitas_json=entitas_json,
            )
        except Exception as exc:
            logger.warning("Gagal mencatat log obrolan ke chat_log: %s", exc)

    # --- Pengambilan Data Analitik & Monitoring Database ---
    # Membuka koneksi database jangka pendek untuk mengumpulkan ringkasan statistik
    # dan daftar log percakapan terbaru untuk dashboard /analytic.
    def get_analytics_summary(self) -> dict[str, Any]:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            repo = Repository(conn)
            return repo.get_analytics_summary()
        finally:
            conn.close()

    def get_recent_logs(self, limit: int = 50) -> list[dict[str, Any]]:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            repo = Repository(conn)
            return repo.get_recent_chat_logs(limit=limit)
        finally:
            conn.close()
