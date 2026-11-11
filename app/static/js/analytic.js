/**
 * Modul JavaScript Dashboard Analitik & Monitoring Database: La Palais
 * Mengambil metrik dari /analytic/summary dan /analytic/logs,
 * merender grafik batang distribusi intent, rasio keberhasilan klasifikasi,
 * tabel master database, serta tabel live chat logs dengan modal inspeksi JSON.
 */

document.addEventListener("DOMContentLoaded", () => {
  const refreshBtn = document.getElementById("refresh-btn");
  const lastUpdatedEl = document.getElementById("last-updated");

  // Elemen KPI Cards
  const kpiTotalChat = document.getElementById("kpi-total-chat");
  const kpiSuccessRate = document.getElementById("kpi-success-rate");
  const kpiFallbackCount = document.getElementById("kpi-fallback-count");
  const kpiTotalMaster = document.getElementById("kpi-total-master");

  // Elemen Distribusi & Master Data
  const intentBarsContainer = document.getElementById("intent-bars-container");
  const masterDataGrid = document.getElementById("master-data-grid");

  // Elemen Tabel Log & Modal
  const logsTableBody = document.getElementById("logs-table-body");
  const logsCountBadge = document.getElementById("logs-count-badge");
  const jsonModal = document.getElementById("json-modal");
  const jsonModalBody = document.getElementById("json-modal-body");
  const jsonModalClose = document.getElementById("json-modal-close");

  let isLoading = false;

  // --- Fungsi Format Waktu Jam:Menit:Detik ---
  function getTimestamp() {
    return new Date().toLocaleTimeString();
  }

  // --- Fungsi Pengambilan Seluruh Data Analitik ---
  async function fetchAnalytics() {
    if (isLoading) return;
    isLoading = true;
    refreshBtn.disabled = true;
    refreshBtn.textContent = "Memperbarui...";

    try {
      // 1. Ambil ringkasan statistik
      const summaryResp = await fetch("/analytic/summary");
      const summaryData = await summaryResp.json();

      // 2. Ambil riwayat log percakapan terbaru
      const logsResp = await fetch("/analytic/logs?limit=50");
      const logsData = await logsResp.json();

      if (summaryResp.ok) {
        renderSummary(summaryData);
      }
      if (logsResp.ok) {
        renderLogs(logsData.logs || []);
      }

      lastUpdatedEl.textContent = "Pembaruan: " + getTimestamp();
    } catch (err) {
      console.error("Gagal memuat analitik:", err);
    } finally {
      isLoading = false;
      refreshBtn.disabled = false;
      refreshBtn.textContent = "⟳ Refresh Data";
    }
  }

  // --- Fungsi Render KPI Cards & Grafik Batang Distribusi ---
  function renderSummary(data) {
    // 1. KPI Cards
    kpiTotalChat.textContent = Number(data.total_chat || 0).toLocaleString();
    kpiSuccessRate.textContent = (data.success_rate || 0) + "%";
    kpiFallbackCount.textContent = Number(data.total_fallback || 0).toLocaleString();

    let totalMasterRows = 0;
    if (data.table_counts) {
      Object.values(data.table_counts).forEach((cnt) => (totalMasterRows += cnt));
    }
    kpiTotalMaster.textContent = totalMasterRows.toLocaleString();

    // 2. Grafik Batang Distribusi 10 Intent
    intentBarsContainer.innerHTML = "";
    const intents = data.intent_distribution || [];

    if (intents.length === 0) {
      intentBarsContainer.innerHTML = `<div style="color:#64748b; font-size:0.8rem;">Belum ada interaksi percakapan yang tercatat.</div>`;
    } else {
      intents.forEach((it) => {
        const item = document.createElement("div");
        item.className = "intent-bar-item";

        const isFallback = it.kode === "fallback";
        item.innerHTML = `
          <div class="intent-bar-labels">
            <span class="intent-name-code">${it.nama} <small style="color:#64748b;">(${it.kode})</small></span>
            <span class="intent-count-pct">${it.jumlah} query (${it.persen}%)</span>
          </div>
          <div class="intent-bar-track">
            <div class="intent-bar-fill ${isFallback ? "fallback" : ""}" style="width: ${Math.max(it.persen, 1)}%;"></div>
          </div>
        `;
        intentBarsContainer.appendChild(item);
      });
    }

    // 3. Status Record Master Data Restoran
    masterDataGrid.innerHTML = "";
    const tables = data.table_counts || {};
    const tableLabels = {
      menu_item: "menu_item (Hidangan)",
      menu_package: "menu_package (Paket)",
      beverage: "beverage (Minuman)",
      pairing: "pairing (Paduan)",
      glossary_term: "glossary_term (Istilah)",
      reservation_info: "reservation_info (Aturan)",
    };

    Object.entries(tables).forEach(([tblKey, count]) => {
      const el = document.createElement("div");
      el.className = "master-data-item";
      el.innerHTML = `
        <span class="master-table-name">${tableLabels[tblKey] || tblKey}</span>
        <span class="master-table-count">${count}</span>
      `;
      masterDataGrid.appendChild(el);
    });
  }

  // --- Fungsi Render Tabel Live Chat Logs ---
  function renderLogs(logs) {
    logsCountBadge.textContent = `${logs.length} entri`;
    logsTableBody.innerHTML = "";

    if (logs.length === 0) {
      logsTableBody.innerHTML = `
        <tr>
          <td colspan="6" style="text-align:center; color:#64748b; padding:24px;">
            Belum ada data riwayat chat_log di database.
          </td>
        </tr>
      `;
      return;
    }

    logs.forEach((log) => {
      const row = document.createElement("tr");

      // Format tanggal/jam
      const dateStr = log.dibuat_pada ? log.dibuat_pada.replace("T", " ").replace("Z", "") : "-";

      // Parse skor JSON untuk mengambil skor intent teratas
      let topScoreText = "-";
      try {
        const scores = JSON.parse(log.skor);
        if (Array.isArray(scores) && scores.length > 0) {
          const top = scores.find((s) => s.intent === log.intent_kode) || scores[0];
          topScoreText = Number(top.skor).toFixed(3);
        }
      } catch (e) {}

      const isFallback = log.intent_kode === "fallback";

      row.innerHTML = `
        <td style="font-family:var(--font-mono); color:#64748b;">#${log.id}</td>
        <td class="table-time">${dateStr}</td>
        <td style="max-width:320px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${log.pesan}">
          "${log.pesan}"
        </td>
        <td>
          <span class="table-badge-intent ${isFallback ? "fallback" : ""}">
            ${log.intent_nama} (${log.intent_kode})
          </span>
        </td>
        <td style="font-family:var(--font-mono);">${topScoreText}</td>
        <td>
          <button type="button" class="action-inspect-btn" data-id="${log.id}">
            Inspeksi JSON
          </button>
        </td>
      `;

      // Event listener tombol inspeksi modal
      const inspectBtn = row.querySelector(".action-inspect-btn");
      inspectBtn.addEventListener("click", () => {
        openJsonModal(log);
      });

      logsTableBody.appendChild(row);
    });
  }

  // --- Penanganan Modal Detail JSON Mentah ---
  function openJsonModal(log) {
    let parsedSkor = log.skor;
    let parsedEntitas = log.entitas;

    try { parsedSkor = JSON.parse(log.skor); } catch (e) {}
    try { parsedEntitas = JSON.parse(log.entitas); } catch (e) {}

    const payload = {
      id: log.id,
      waktu: log.dibuat_pada,
      pesan: log.pesan,
      intent: { kode: log.intent_kode, nama: log.intent_nama },
      skor_breakdown: parsedSkor,
      entitas: parsedEntitas,
    };

    jsonModalBody.textContent = JSON.stringify(payload, null, 2);
    jsonModal.classList.add("open");
  }

  jsonModalClose.addEventListener("click", () => {
    jsonModal.classList.remove("open");
  });

  jsonModal.addEventListener("click", (e) => {
    if (e.target === jsonModal) {
      jsonModal.classList.remove("open");
    }
  });

  // Tombol Refresh Manual
  refreshBtn.addEventListener("click", fetchAnalytics);

  // Panggilan awal saat halaman dimuat
  fetchAnalytics();
});
