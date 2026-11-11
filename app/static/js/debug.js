/**
 * Modul JavaScript Konsol Debug NLU: La Palais
 * Mengelola Base Layout 3-Section:
 * - Section 1 (kiri bawah): Input teks uji
 * - Section 2 (kiri atas): Riwayat kartu hasil NLU
 * - Section 3 (kanan rowspan 2): Collapsible drawer detail analisis kartu NLU terpilih
 */

document.addEventListener("DOMContentLoaded", () => {
  const cardsContainer = document.getElementById("debug-cards-container");
  const emptyState = document.getElementById("cards-empty-state");
  const debugTextarea = document.getElementById("debug-textarea");
  const debugSendBtn = document.getElementById("debug-send-btn");
  const gridMain = document.getElementById("debug-grid-main");
  const drawerToggleBtn = document.getElementById("drawer-toggle-btn");
  const drawerContent = document.getElementById("drawer-content");
  const reloadSnapshotBtn = document.getElementById("reload-snapshot-btn");
  const clearCardsBtn = document.getElementById("clear-cards-btn");

  let cardHistory = []; // Hasil permintaan debug, terbaru disimpan pada indeks pertama.
  let selectedCardIndex = null; // Indeks kartu yang detail analisisnya sedang ditampilkan.
  let isSending = false; // Status pengiriman untuk mencegah permintaan uji bertumpuk.

  // --- Fungsi Format Waktu Jam:Menit:Detik ---
  function getTimeString() {
    const d = new Date();
    return d.toTimeString().split(" ")[0];
  }

  // --- Fungsi Pengiriman Pesan Uji ke /api/debug/chat ---
  async function sendDebugMessage(text) {
    const cleanText = text.trim(); // Normalisasi spasi tepi sebelum dikirim ke endpoint debug.
    if (!cleanText || isSending) return;

    isSending = true;
    debugSendBtn.disabled = true;
    debugSendBtn.textContent = "Memproses...";

    try {
      const resp = await fetch("/api/debug/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: cleanText }),
      });

      const data = await resp.json();

      if (resp.ok) {
        const item = { // Satu entri riwayat berisi pesan uji, waktu kirim, dan payload lengkap API.
          query: cleanText,
          time: getTimeString(),
          response: data,
        };
        cardHistory.unshift(item);
        renderCardList();
        selectCard(0);
        debugTextarea.value = "";
      } else {
        alert("Gagal memproses uji debug: " + (data.error?.message || "Error"));
      }
    } catch (err) {
      alert("Kesalahan jaringan: " + err.message);
    } finally {
      isSending = false;
      debugSendBtn.disabled = false;
      debugSendBtn.textContent = "Uji NLU";
      debugTextarea.focus();
    }
  }

  // --- Fungsi Render Daftar Kartu di Section 2 ---
  function renderCardList() {
    if (cardHistory.length === 0) {
      emptyState.style.display = "block";
      cardsContainer.innerHTML = "";
      cardsContainer.appendChild(emptyState);
      return;
    }

    emptyState.style.display = "none";
    cardsContainer.innerHTML = "";

    cardHistory.forEach((item, idx) => {
      const debugInfo = item.response.debug || {};
      const dec = debugInfo.decision || {};
      const topScore = (debugInfo.ranking && debugInfo.ranking[0]?.skor) || 0; // Skor intent tertinggi untuk ringkasan kartu.
      const latency = debugInfo.latency_ms || 0; // Lama analisis engine yang dilaporkan server.

      const card = document.createElement("div");
      card.className = `nlu-card ${idx === selectedCardIndex ? "active" : ""}`;
      card.innerHTML = `
        <div class="card-top-row">
          <span class="card-query-text" title="${item.query}">"${item.query}"</span>
          <span class="card-time">${item.time}</span>
        </div>
        <div class="card-bottom-row">
          <span class="badge-intent">${dec.intent || "-"}</span>
          <span class="badge-score">Skor: ${Number(topScore).toFixed(3)}</span>
          <span class="badge-latency">${latency} ms</span>
        </div>
      `;

      card.addEventListener("click", () => {
        selectCard(idx);
      });

      cardsContainer.appendChild(card);
    });
  }

  // --- Fungsi Memilih Kartu & Membuka Detail di Section 3 ---
  function selectCard(idx) {
    selectedCardIndex = idx;

    // Perbarui status kartu aktif
    const cardEls = cardsContainer.querySelectorAll(".nlu-card");
    cardEls.forEach((c, i) => {
      c.classList.toggle("active", i === idx);
    });

    const item = cardHistory[idx];
    if (!item) return;

    // Buka drawer jika saat ini sedang terlipat
    gridMain.classList.remove("drawer-collapsed");
    drawerToggleBtn.textContent = "»";

    renderDrawerDetails(item);
  }

  // --- Fungsi Render Konten Detail Drawer (Section 3) ---
  function renderDrawerDetails(item) {
    const debug = item.response.debug || {};
    const dec = debug.decision || {};
    const ranking = debug.ranking || []; // Skor semua kandidat intent untuk tabel rincian.
    const tokens = debug.tokens || []; // Token hasil normalisasi pesan yang diperiksa engine.
    const entities = debug.entities || {}; // Filter harga/diet yang berhasil diekstrak dari pesan.

    let rankingRows = ""; // Fragmen baris HTML untuk tabel ranking intent.
    ranking.forEach((r) => {
      const isSelected = r.intent === dec.intent;
      rankingRows += `
        <tr class="${isSelected ? "selected" : ""}">
          <td>${r.intent}${isSelected ? " ★" : ""}</td>
          <td>${Number(r.skor).toFixed(3)}</td>
          <td>${Number(r.jaccard).toFixed(3)}</td>
          <td>${Number(r.fuzzy).toFixed(3)}</td>
          <td>${Number(r.cakupan).toFixed(3)}</td>
        </tr>
      `;
    });

    let entityHtml = `<span style="color:#64748b; font-size:0.75rem;">(Tidak ada entitas terdeteksi)</span>`;
    if (entities.harga || (entities.diet && entities.diet.length > 0)) {
      entityHtml = `<div class="tokens-wrap">`;
      if (entities.harga) {
        entityHtml += `<span class="token-badge">Harga: ${entities.harga.op} Rp${Number(entities.harga.nilai).toLocaleString("id-ID")}</span>`;
      }
      if (entities.diet) {
        entities.diet.forEach((d) => {
          entityHtml += `<span class="token-badge">Diet: ${d}</span>`;
        });
      }
      entityHtml += `</div>`;
    }

    drawerContent.innerHTML = `
      <!-- Ringkasan Balasan -->
      <div class="detail-block">
        <div class="detail-block-title">Balasan Restoran</div>
        <div style="font-size:0.85rem; line-height:1.5; color:#f1f5f9; white-space:pre-wrap;">${item.response.reply || "-"}</div>
      </div>

      <!-- Keputusan & Parameter NLU -->
      <div class="detail-block">
        <div class="detail-block-title">Keputusan & Parameter</div>
        <div style="font-size:0.85rem; margin-bottom:8px;">
          <strong>Intent:</strong> <span style="color:var(--color-gold); font-weight:700;">${dec.intent}</span>
          <span style="color:#94a3b8; font-size:0.78rem;"> (Alasan: ${dec.alasan})</span>
        </div>
        <div class="param-pills">
          <span class="param-pill">tau: ${dec.tau}</span>
          <span class="param-pill">delta: ${dec.delta}</span>
          <span class="param-pill">rho: ${dec.rho}</span>
          <span class="param-pill">latensi: ${debug.latency_ms} ms</span>
        </div>
      </div>

      <!-- Token Normalisasi (R1) -->
      <div class="detail-block">
        <div class="detail-block-title">Token Bersih Normalisasi (R1)</div>
        <div class="tokens-wrap">
          ${tokens.map((t) => `<span class="token-badge">${t}</span>`).join("") || '<span style="color:#64748b; font-size:0.75rem;">(Kosong)</span>'}
        </div>
      </div>

      <!-- Ekstraksi Entitas (R4) -->
      <div class="detail-block">
        <div class="detail-block-title">Ekstraksi Entitas (R4)</div>
        ${entityHtml}
      </div>

      <!-- Tabel Skor 10 Intent (R2 & R3) -->
      <div class="detail-block">
        <div class="detail-block-title">Peringkat 10 Intent</div>
        <table class="intent-table">
          <thead>
            <tr>
              <th>Intent</th>
              <th>Skor</th>
              <th>Jacc</th>
              <th>Fuzz</th>
              <th>Ckp</th>
            </tr>
          </thead>
          <tbody>
            ${rankingRows}
          </tbody>
        </table>
      </div>
    `;
  }

  // --- Toggle Collapse Drawer (Section 3) ke Kanan ---
  drawerToggleBtn.addEventListener("click", () => {
    const isCollapsed = gridMain.classList.toggle("drawer-collapsed");
    drawerToggleBtn.textContent = isCollapsed ? "«" : "»";
  });

  // --- Hot Reload Snapshot ke /api/debug/reload ---
  reloadSnapshotBtn.addEventListener("click", async () => {
    reloadSnapshotBtn.disabled = true;
    reloadSnapshotBtn.textContent = "Memuat...";

    try {
      const resp = await fetch("/api/debug/reload", { method: "POST" });
      const data = await resp.json();
      if (resp.ok && data.status === "reloaded") {
        alert("✅ NluSnapshot berhasil dimuat ulang dari database!");
      } else {
        alert("Gagal me-reload snapshot: " + JSON.stringify(data));
      }
    } catch (e) {
      alert("Error reload snapshot: " + e.message);
    } finally {
      reloadSnapshotBtn.disabled = false;
      reloadSnapshotBtn.innerHTML = `⟳ <span>Reload Snapshot</span>`;
    }
  });

  // --- Reset Daftar Kartu ---
  clearCardsBtn.addEventListener("click", () => {
    cardHistory = [];
    selectedCardIndex = null;
    renderCardList();
    drawerContent.innerHTML = `<div style="margin:auto; text-align:center; color:#64748b; font-size:0.85rem;">Pilih kartu di sebelah kiri untuk melihat rincian NLU</div>`;
  });

  // --- Event Handler Input Composer ---
  debugSendBtn.addEventListener("click", () => {
    sendDebugMessage(debugTextarea.value);
  });

  debugTextarea.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendDebugMessage(debugTextarea.value);
    }
  });
});
