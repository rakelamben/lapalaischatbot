"""
Registri Handler Intent untuk LaPalaisChatBot.
"""

from __future__ import annotations

from app.engine.handlers.a_la_carte import ALaCarteHandler
from app.engine.handlers.base import BaseHandler
from app.engine.handlers.fallback import FallbackHandler
from app.engine.handlers.menu_filter import MenuFilterHandler
from app.engine.handlers.pairing import PairingHandler
from app.engine.handlers.paket import PackageHandler
from app.engine.handlers.reservasi import ReservasiHandler
from app.engine.handlers.social import SocialHandler
from app.engine.handlers.teknik import TeknikHandler

# --- Pemetaan Handler Intent Sistem ---
# Memetakan masing-masing dari 11 kode intent resmi ke instans kelas handler yang bertanggung jawab.
HANDLERS: dict[str, BaseHandler] = {
    "sapaan": SocialHandler(),
    "penutup": SocialHandler(),
    "reservasi": ReservasiHandler(),
    "carte_blanche": PackageHandler(tipe="carte_blanche"),
    "prix_fixe": PackageHandler(tipe="prix_fixe"),
    "a_la_carte": ALaCarteHandler(),
    "teknik": TeknikHandler(),
    "diet": MenuFilterHandler(),
    "harga": MenuFilterHandler(),
    "pairing": PairingHandler(),
    "fallback": FallbackHandler(),
}


# Mengambil handler berdasarkan kode intent; jika kode tidak dikenal, fallback otomatis digunakan.
def get_handler(intent_code: str) -> BaseHandler:
    return HANDLERS.get(intent_code, HANDLERS["fallback"])
