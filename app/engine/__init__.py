"""
Titik masuk utama untuk Engine NLU LaPalaisChatBot.
Fungsi analyze() murni tanpa I/O database.
Fungsi process_message() memadukan analyze, handler data, dan generator respons.
"""

from __future__ import annotations

import time

from app.data.repository import Repository
from app.engine.decision import decide
from app.engine.entities import extract_entities
from app.engine.handlers import get_handler
from app.engine.params import EngineParams
from app.engine.responder import Responder
from app.engine.scoring import rank_intents
from app.engine.snapshot import NluSnapshot
from app.engine.types import Analysis, Reply


# --- Fungsi Analisis NLU Murni (In-Memory) ---
# Menjalankan pemrosesan teks linguistik dari pesan input hingga keputusan intent tanpa I/O disk.
# Fungsi ini dapat dipanggil mandiri oleh skrip evaluasi akurasi (evaluate.py) atau unit test:
# 1. Normalisasi teks (menghapus aksen, mengekstrak angka, mengganti frasa/sinonim, membuang stopword).
# 2. Ekstraksi entitas harga dan diet.
# 3. Perhitungan skor 10 intent (Jaccard + Fuzzy + Cakupan Berbobot).
# 4. Pengambilan keputusan intent akhir berdasarkan ambang tau, margin delta, dan aturan prioritas.
def analyze(
    message: str,
    snapshot: NluSnapshot,
    params: EngineParams,
) -> Analysis:
    start_time = time.perf_counter()

    # 1. Normalisasi teks (R1)
    norm = snapshot.normalizer.normalize(message)

    # 2. Ekstraksi entitas harga & diet (R4)
    entities = extract_entities(norm, snapshot, params)

    # 3. Hitung skor & peringkat intent (R2)
    ranking = rank_intents(norm.score_tokens, snapshot, params)

    # 4. Ambil keputusan (R3, R10)
    decision = decide(ranking, snapshot, params, msg_tokens=norm.score_tokens)

    elapsed_ms = (time.perf_counter() - start_time) * 1000.0

    return Analysis(
        raw_message=message,
        clean_tokens=norm.clean_tokens,
        score_tokens=norm.score_tokens,
        entities=entities,
        ranking=ranking,
        decision=decision,
        latency_ms=round(elapsed_ms, 2),
    )


# --- Fungsi Orkestrasi End-to-End ---
# Titik masuk pemrosesan pesan lengkap yang digunakan oleh layer service backend:
# 1. Menjalankan analyze() untuk memahami maksud dan entitas pesan.
# 2. Memanggil handler intent yang sesuai dari registri handler.
# 3. Handler mengambil data terkait dari SQLite melalui Repository (kueri filter menu, paket, pairing, atau reservasi).
# 4. Responder merakit teks balasan, menyematkan disclaimer jika perlu, dan menganotasi istilah Prancis (R11).
def process_message(
    message: str,
    snapshot: NluSnapshot,
    params: EngineParams,
    repo: Repository,
    prev_template_id: int | None = None,
    rng_seed: int | None = None,
) -> Reply:
    # 1. Jalankan analisis NLU
    analysis = analyze(message, snapshot, params)

    # 2. Ambil handler sesuai keputusan
    handler = get_handler(analysis.decision.intent)

    # 3. Eksekusi handler untuk mengambil data
    handler_result = handler.handle(analysis, repo, snapshot)

    # 4. Generate respons akhir
    responder = Responder(snapshot)
    reply = responder.generate_reply(
        analysis=analysis,
        handler_result=handler_result,
        prev_template_id=prev_template_id,
        rng_seed=rng_seed,
    )

    return reply
