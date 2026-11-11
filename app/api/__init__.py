"""
Inisialisasi paket API: Mengelompokkan blueprint rute publik, rute debug, dan rute analitik database.
"""

from app.api.analytic import analytic_bp
from app.api.chat import chat_bp
from app.api.debug import debug_bp

__all__ = ["chat_bp", "debug_bp", "analytic_bp"]
