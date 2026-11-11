"""
Kontrak dasar untuk Handler Intent.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.data.repository import Repository
from app.engine.snapshot import NluSnapshot
from app.engine.types import Analysis


# --- Struktur Data Hasil Eksekusi Handler ---
# HandlerResult menampung luaran dari masing-masing handler intent:
# - content: data terstruktur dari handler info atau teks yang dipakai handler fallback.
# - protected_spans: nama-nama hidangan atau minuman yang dilindungi agar tidak teranotasi ganda oleh glosarium.
# - is_empty: flag penanda jika hasil filter tidak menghasilkan baris data apa pun.
# - suggestions: daftar tombol saran kanonik yang dihasilkan untuk intent fallback.
@dataclass
class HandlerResult:
    content: list[dict[str, Any]] | str | None = None
    protected_spans: list[str] = field(default_factory=list)
    is_empty: bool = False
    suggestions: list[dict[str, str]] = field(default_factory=list)


# --- Antarmuka Kontrak Handler Intent ---
# Setiap handler intent wajib mengimplementasikan method handle() yang menerima
# objek Analysis, Repository SQLite, dan NluSnapshot, lalu mengembalikan HandlerResult.
class BaseHandler:
    def handle(
        self,
        analysis: Analysis,
        repo: Repository,
        snapshot: NluSnapshot,
    ) -> HandlerResult:
        raise NotImplementedError
