/**
 * Modul JavaScript Antarmuka Tamu: La Palais Concierge Chat
 * Mengelola pengiriman pesan ke /api/chat, render bubble percakapan,
 * penanganan chip saran pertanyaan, auto-scroll, dan dropdown menu hapus obrolan.
 */

document.addEventListener("DOMContentLoaded", () => {
  const chatContainer = document.querySelector(".chat-container");
  const chatMessages = document.getElementById("chat-messages");
  const composerTextarea = document.getElementById("composer-textarea");
  const sendBtn = document.getElementById("send-btn");
  const chipsContainer = document.getElementById("chips-container");
  const threeDotsBtn = document.getElementById("three-dots-btn");
  const optionsDropdown = document.getElementById("options-dropdown");
  const clearChatBtn = document.getElementById("clear-chat-btn");

  const artificialDelayMs = 1000; // Jeda tampilan agar respons tidak terasa muncul terlalu instan.
  let prevTemplateId = null; // ID template terakhir, dikirim agar kalimat pembuka tidak berulang.
  let isPending = false; // Mencegah pengiriman pesan baru sebelum permintaan sebelumnya selesai.

  chatContainer.style.visibility = "hidden";
  setTimeout(() => {
    chatContainer.style.visibility = "visible";
  }, artificialDelayMs);

  // Daftar pertanyaan cepat awal restoran fine dining
  const defaultChips = [
    { label: "Menu Paket", frasa: "ada paket menu apa saja" },
    { label: "A La Carte", frasa: "menu a la carte unggulan" },
    { label: "Pairing Wine", frasa: "rekomendasi pairing wine" },
    { label: "Reservasi", frasa: "cara melakukan reservasi meja" },
    { label: "Teknik Memasak", frasa: "apa itu teknik sous vide" },
  ];

  // --- Fungsi Format Waktu ---
  // Menghasilkan string jam:menit lokal untuk stempel waktu pesan.
  function getFormattedTime() {
    const now = new Date();
    return now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }

  // --- Fungsi Render Bubble Pesan ---
  // Membuat elemen bubble pesan bot atau tamu dan menambahkannya ke kontainer chat.
  function appendMessage(sender, text, content = null, contentType = null) {
    const row = document.createElement("div");
    row.className = `message-row ${sender}`;

    const bubble = document.createElement("div");
    bubble.className = "message-bubble";
    bubble.textContent = text;
    appendStructuredContent(bubble, content, contentType);

    const time = document.createElement("div");
    time.className = "message-time";
    time.textContent = getFormattedTime();

    bubble.appendChild(time);
    row.appendChild(bubble);
    chatMessages.appendChild(row);

    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  function createTextElement(tagName, className, text) {
    const element = document.createElement(tagName);
    element.className = className;
    element.textContent = text == null ? "" : String(text);
    return element;
  }

  function formatPrice(value) {
    const amount = Number(value);
    return Number.isFinite(amount) ? `Rp${amount.toLocaleString("id-ID")}` : String(value ?? "");
  }

  function appendMenuItems(container, items) {
    // Kelompokkan hidangan berdasarkan kategori supaya daftar menu tetap terstruktur.
    const groups = new Map();
    items.forEach((item) => {
      const category = item.kategori || "Menu";
      if (!groups.has(category)) groups.set(category, []);
      groups.get(category).push(item);
    });

    groups.forEach((categoryItems, category) => {
      const group = document.createElement("section");
      group.className = "chat-data-group";
      group.appendChild(createTextElement("h3", "chat-data-heading", category));

      const list = document.createElement("ul");
      list.className = "chat-data-list";
      categoryItems.forEach((item) => {
        const row = document.createElement("li");
        row.className = "chat-data-item";
        row.appendChild(createTextElement("strong", "chat-data-title", item.nama));
        if (item.deskripsi) {
          row.appendChild(createTextElement("p", "chat-data-description", item.deskripsi));
        }
        if (item.harga != null) {
          row.appendChild(createTextElement("span", "chat-data-price", formatPrice(item.harga)));
        }
        list.appendChild(row);
      });

      group.appendChild(list);
      container.appendChild(group);
    });
  }

  function appendStructuredContent(bubble, content, contentType) {
    if (!Array.isArray(content) || content.length === 0) return;

    // content_type menentukan renderer khusus untuk bentuk data dari handler.
    const section = document.createElement("div");
    section.className = "chat-structured-content";

    if (contentType === "reservasi") {
      const details = document.createElement("dl");
      details.className = "chat-data-reservation";
      content.forEach((item) => {
        const row = document.createElement("div");
        row.className = "chat-data-reservation-item";
        row.appendChild(createTextElement("dt", "chat-data-title", item.label));
        row.appendChild(createTextElement("dd", "chat-data-description", item.isi));
        details.appendChild(row);
      });
      section.appendChild(details);
    } else if (contentType === "a_la_carte" || contentType === "diet" || contentType === "harga") {
      appendMenuItems(section, content);
    } else if (contentType === "prix_fixe" || contentType === "carte_blanche") {
      content.forEach((pkg) => {
        const card = document.createElement("section");
        card.className = "chat-data-package";
        card.appendChild(createTextElement("h3", "chat-data-heading", pkg.nama));
        if (pkg.deskripsi) {
          card.appendChild(createTextElement("p", "chat-data-description", pkg.deskripsi));
        }

        const metadata = [];
        if (pkg.harga != null) metadata.push(formatPrice(pkg.harga));
        if (pkg.durasi_menit != null) metadata.push(`Durasi sekitar ${pkg.durasi_menit} menit`);
        if (metadata.length) {
          card.appendChild(createTextElement("p", "chat-data-meta", metadata.join(" · ")));
        }

        if (Array.isArray(pkg.hidangan) && pkg.hidangan.length) {
          const dishes = document.createElement("ol");
          dishes.className = "chat-data-list";
          pkg.hidangan.forEach((dish) => {
            const row = document.createElement("li");
            row.className = "chat-data-item";
            row.appendChild(createTextElement("strong", "chat-data-title", dish.nama));
            if (dish.deskripsi) {
              row.appendChild(createTextElement("p", "chat-data-description", dish.deskripsi));
            }
            dishes.appendChild(row);
          });
          card.appendChild(dishes);
        }
        section.appendChild(card);
      });
    } else if (contentType === "pairing") {
      const grouped = new Map();
      content.forEach((item) => {
        if (!grouped.has(item.hidangan)) grouped.set(item.hidangan, []);
        grouped.get(item.hidangan).push(item);
      });

      grouped.forEach((pairings, dishName) => {
        const group = document.createElement("section");
        group.className = "chat-data-group";
        group.appendChild(createTextElement("h3", "chat-data-heading", dishName));

        const list = document.createElement("ul");
        list.className = "chat-data-list";
        pairings.forEach((pairing) => {
          const row = document.createElement("li");
          row.className = "chat-data-item";
          const drinkName = pairing.jenis
            ? `${pairing.minuman} (${pairing.jenis})`
            : pairing.minuman;
          row.appendChild(createTextElement("strong", "chat-data-title", drinkName));
          if (pairing.deskripsi_minuman) {
            row.appendChild(createTextElement("p", "chat-data-description", pairing.deskripsi_minuman));
          }
          list.appendChild(row);
        });
        group.appendChild(list);
        section.appendChild(group);
      });
    } else if (contentType === "teknik") {
      const list = document.createElement("ul");
      list.className = "chat-data-list";
      content.forEach((item) => {
        const row = document.createElement("li");
        row.className = "chat-data-item";
        row.appendChild(createTextElement("strong", "chat-data-title", item.istilah));
        row.appendChild(createTextElement("p", "chat-data-description", item.makna));
        list.appendChild(row);
      });
      section.appendChild(list);
    } else {
      return;
    }

    bubble.appendChild(section);
  }

  // --- Fungsi Indikator Mengetik ---
  // Menampilkan animasi 3 titik saat menunggu respon dari server.
  function showTypingIndicator() {
    const row = document.createElement("div");
    row.className = "message-row bot typing-indicator-row";
    row.id = "typing-indicator";

    const bubble = document.createElement("div");
    bubble.className = "typing-bubble";
    bubble.innerHTML = `
      <span class="typing-dot"></span>
      <span class="typing-dot"></span>
      <span class="typing-dot"></span>
    `;

    row.appendChild(bubble);
    chatMessages.appendChild(row);
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  function hideTypingIndicator() {
    const el = document.getElementById("typing-indicator");
    if (el) el.remove();
  }

  // --- Fungsi Render Chip Saran Pertanyaan ---
  // Menampilkan deretan tombol chip di atas kolom input yang dapat diklik langsung.
  function renderChips(suggestions) {
    chipsContainer.innerHTML = "";
    const items = (suggestions && suggestions.length > 0) ? suggestions : defaultChips;

    items.forEach((item) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "suggestion-chip";
      btn.textContent = item.frasa;
      btn.addEventListener("click", () => {
        if (!isPending) {
          sendMessage(item.frasa || item.label);
        }
      });
      chipsContainer.appendChild(btn);
    });
  }

  // --- Fungsi Utama Pengiriman Pesan ---
  // Mengirim pesan ke POST /api/chat, menerima respons, dan merotasi template_id.
  async function sendMessage(text) {
    const cleanText = text.trim(); // Hapus spasi tepi sebelum pesan ditampilkan dan dikirim ke API.
    if (!cleanText || isPending) return;

    isPending = true;
    sendBtn.disabled = true;
    composerTextarea.value = "";
    composerTextarea.style.height = "auto";

    appendMessage("user", cleanText);
    showTypingIndicator();

    try {
      const resp = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: cleanText,
          prev_template_id: prevTemplateId,
        }),
      });
      await new Promise((resolve) => setTimeout(resolve, artificialDelayMs));

      const data = await resp.json(); // Payload jawaban, data terstruktur, saran, atau error API.
      hideTypingIndicator();

      if (resp.ok && data.reply) {
        appendMessage("bot", data.reply, data.content, data.content_type);
        prevTemplateId = data.template_id || null; // Simpan pilihan server sebagai konteks rotasi template berikutnya.
        renderChips(data.suggestions);
      } else {
        const errMsg = data.error?.message || "Mohon maaf, terjadi kendala komunikasi dengan pelayan kami.";
        appendMessage("bot", errMsg);
      }
    } catch (err) {
      hideTypingIndicator();
      appendMessage("bot", "Koneksi terputus. Silakan periksa jaringan Anda atau coba sesaat lagi.");
    } finally {
      isPending = false;
      sendBtn.disabled = composerTextarea.value.trim().length === 0;
      chatMessages.scrollTop = chatMessages.scrollHeight;
    }
  }

  // --- Penanganan Dropdown Menu Titik Tiga & Hapus Obrolan ---
  threeDotsBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    optionsDropdown.classList.toggle("open");
  });

  document.addEventListener("click", () => {
    optionsDropdown.classList.remove("open");
  });

  clearChatBtn.addEventListener("click", () => {
    optionsDropdown.classList.remove("open");
    chatMessages.innerHTML = "";
    prevTemplateId = null;
    appendMessage(
      "bot",
      "Bonjour! Selamat datang kembali di La Palais. Silakan tanyakan pilihan menu, filosofi hidangan, atau reservasi meja Anda."
    );
    renderChips(defaultChips);
  });

  // --- Event Handler Input Teks & Tombol Kirim ---
  composerTextarea.addEventListener("input", () => {
    sendBtn.disabled = composerTextarea.value.trim().length === 0;
    composerTextarea.style.height = "auto";
    composerTextarea.style.height = Math.min(composerTextarea.scrollHeight, 110) + "px";
  });

  composerTextarea.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage(composerTextarea.value);
    }
  });

  sendBtn.addEventListener("click", () => {
    sendMessage(composerTextarea.value);
  });

  // Inisialisasi awal
  renderChips(defaultChips);
});
