"""
Mesin keputusan NLU sesuai PRD R3 dan System Design Bagian 6.4.
Evaluasi ambang tau, margin delta, ambang rho (tebakan), dan aturan prioritas.
"""

from __future__ import annotations

from app.engine.params import EngineParams
from app.engine.snapshot import NluSnapshot
from app.engine.types import Decision, Ranking


# --- Resolusi Aturan Prioritas ---
# Dijalankan saat selisih skor antara peringkat 1 dan 2 sangat tipis (< delta 0.10):
# (a) Sosial (sapaan/penutup) berprioritas terendah jika intent informasi lolos tau.
# (b) Pasangan diet dan harga dijawab bersama sebagai satu intent dengan filter menu.
# (c) Pemenang adalah intent yang memiliki jumlah kata pembeda (bobot 3) terbanyak dalam pesan.
# (d) Jika masih seri, pemenang ditentukan secara deterministik berdasarkan ID intent terkecil.
def resolve_priority(
    top: Ranking,
    second: Ranking,
    snapshot: NluSnapshot,
    params: EngineParams,
    msg_tokens: frozenset[str] | None = None,
) -> Decision:
    top_intent_data = snapshot.intents.get(top.intent)
    second_intent_data = snapshot.intents.get(second.intent)

    top_jenis = top_intent_data.jenis if top_intent_data else "info"
    second_jenis = second_intent_data.jenis if second_intent_data else "info"

    # Aturan (a): Sapaan dan penutup (sosial) berprioritas terendah jika info lolos tau
    if top_jenis == "sosial" and second_jenis == "info" and second.skor >= params.tau:
        return Decision(second.intent, alasan="prioritas_info_kalahkan_sosial")
    if second_jenis == "sosial" and top_jenis == "info":
        return Decision(top.intent, alasan="prioritas_info_kalahkan_sosial")

    # Aturan (b): Pasangan diet dan harga dijawab bersama lewat filter bersama
    pair = {top.intent, second.intent}
    if pair == {"diet", "harga"}:
        return Decision(top.intent, alasan="prioritas_filter_menu_bersama")

    # Aturan (c): Kata kunci pembeda berbobot lebih tinggi (bobot 3) menang
    if msg_tokens:
        top_pats_tokens = set().union(*(p.tokens for p in (top_intent_data.patterns if top_intent_data else [])))
        second_pats_tokens = set().union(*(p.tokens for p in (second_intent_data.patterns if second_intent_data else [])))

        top_hits = len({t for t in (msg_tokens & top_pats_tokens) if snapshot.token_weights.get(t) == 3})
        second_hits = len({t for t in (msg_tokens & second_pats_tokens) if snapshot.token_weights.get(t) == 3})

        if top_hits > second_hits:
            return Decision(top.intent, alasan="bobot_pembeda_unggul")
        elif second_hits > top_hits:
            return Decision(second.intent, alasan="bobot_pembeda_unggul")

    # Aturan (d): Jika masih seri, intent dengan ID terkecil menang
    top_id = top_intent_data.id if top_intent_data else 999
    second_id = second_intent_data.id if second_intent_data else 999
    if top_id <= second_id:
        return Decision(top.intent, alasan="seri_id_terkecil")
    else:
        return Decision(second.intent, alasan="seri_id_terkecil")


# --- Mesin Keputusan Utama ---
# Menentukan intent akhir dari daftar peringkat skor:
# 1. Jika skor tertinggi < tau (0.45) -> fallback. Jika skor >= rho (0.15), berikan tebakan intent.
# 2. Jika selisih peringkat 1 dan 2 >= delta (0.10) -> peringkat 1 menang meyakinkan.
# 3. Jika selisih tipis (< delta) -> jalankan resolve_priority.
def decide(
    ranking: list[Ranking],
    snapshot: NluSnapshot,
    params: EngineParams,
    msg_tokens: frozenset[str] | None = None,
) -> Decision:
    if not ranking:
        return Decision("fallback", alasan="tanpa_skor")

    top = ranking[0]
    second = ranking[1] if len(ranking) > 1 else Ranking("none", 0.0, 0.0, 0.0, 0.0)

    # 1. Cek ambang batas tau
    if top.skor < params.tau:
        guess = top if top.skor >= params.rho else None
        return Decision("fallback", alasan="di_bawah_tau", tebakan=guess)

    # 2. Cek margin delta
    if (top.skor - second.skor) >= params.delta:
        return Decision(top.intent, alasan="ambang")

    # 3. Jalankan aturan prioritas
    return resolve_priority(top, second, snapshot, params, msg_tokens)
