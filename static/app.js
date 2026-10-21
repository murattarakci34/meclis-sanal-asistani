(() => {
  const APP_NAME = window.APP_NAME || "Meclis Sanal Asistanı";

  const els = {
    sidebar: document.getElementById("sidebar"),
    overlay: document.getElementById("overlay"),
    menuBtn: document.getElementById("menuBtn"),
    btnNew: document.getElementById("btnNew"),
    search: document.getElementById("search"),
    chatList: document.getElementById("chatList"),
    messages: document.getElementById("messages"),
    empty: document.getElementById("empty"),
    topTitle: document.getElementById("topTitle"),
    composer: document.getElementById("composer"),
    input: document.getElementById("input"),
    sendBtn: document.getElementById("sendBtn"),
  };

  let currentChatId = null;
  let busy = false;

  function openSidebar() {
    els.sidebar.classList.add("open");
    els.overlay.classList.add("show");
  }
  function closeSidebar() {
    els.sidebar.classList.remove("open");
    els.overlay.classList.remove("show");
  }

  els.menuBtn.addEventListener("click", openSidebar);
  els.overlay.addEventListener("click", closeSidebar);

  function escapeHtml(s) {
    return String(s)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  function simpleMarkdown(text) {
    const esc = escapeHtml(text);
    return esc
      .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
      .replace(/\n/g, "<br>");
  }

  function setTitle(title) {
    els.topTitle.textContent = title || APP_NAME;
  }

  function renderMessages(messages) {
    els.messages.innerHTML = "";
    if (!messages || !messages.length) {
      els.messages.appendChild(els.empty);
      els.empty.style.display = "";
      setTitle(APP_NAME);
      return;
    }
    els.empty.style.display = "none";
    for (const m of messages) {
      const row = document.createElement("div");
      row.className = `msg ${m.role}`;
      const av = m.role === "user" ? "S" : "M";
      row.innerHTML = `
        <div class="avatar">${av}</div>
        <div class="bubble">${simpleMarkdown(m.content || "")}</div>
      `;
      els.messages.appendChild(row);
    }
    els.messages.scrollTop = els.messages.scrollHeight;
  }

  function showTyping() {
    const t = document.createElement("div");
    t.className = "typing";
    t.id = "typing";
    t.textContent = "Yazıyor…";
    els.messages.appendChild(t);
    els.messages.scrollTop = els.messages.scrollHeight;
  }
  function hideTyping() {
    document.getElementById("typing")?.remove();
  }

  async function loadChatList(q = "") {
    const res = await fetch(`/api/chats?q=${encodeURIComponent(q)}`);
    const data = await res.json();
    const chats = data.chats || [];
    els.chatList.innerHTML = "";
    if (!chats.length) {
      els.chatList.innerHTML = `<div class="chat-empty">Henüz sohbet yok</div>`;
      return;
    }
    for (const c of chats) {
      const row = document.createElement("div");
      row.className = "chat-row" + (c.id === currentChatId ? " active" : "");
      const title = c.title || "Sohbet";
      row.innerHTML = `
        <button type="button" class="open" title="${escapeHtml(title)}">${escapeHtml(title)}</button>
        <button type="button" class="del" title="Sil" data-id="${c.id}">🗑️</button>
      `;
      row.querySelector(".open").addEventListener("click", () => openChat(c.id));
      row.querySelector(".del").addEventListener("click", async (e) => {
        e.stopPropagation();
        await fetch(`/api/chats/${c.id}`, { method: "DELETE" });
        if (currentChatId === c.id) startNew();
        else loadChatList(els.search.value.trim());
      });
      els.chatList.appendChild(row);
    }
  }

  async function openChat(id) {
    const res = await fetch(`/api/chats/${id}`);
    if (!res.ok) return;
    const chat = await res.json();
    currentChatId = chat.id;
    setTitle(chat.title || APP_NAME);
    renderMessages(chat.messages || []);
    loadChatList(els.search.value.trim());
    closeSidebar();
  }

  function startNew() {
    currentChatId = null;
    setTitle(APP_NAME);
    renderMessages([]);
    loadChatList(els.search.value.trim());
    closeSidebar();
    els.input.focus();
  }

  els.btnNew.addEventListener("click", startNew);

  let searchTimer;
  els.search.addEventListener("input", () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => loadChatList(els.search.value.trim()), 200);
  });

  function autosize() {
    els.input.style.height = "auto";
    els.input.style.height = Math.min(els.input.scrollHeight, 160) + "px";
  }
  els.input.addEventListener("input", autosize);

  els.input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      els.composer.requestSubmit();
    }
  });

  els.composer.addEventListener("submit", async (e) => {
    e.preventDefault();
    const message = els.input.value.trim();
    if (!message || busy) return;

    busy = true;
    els.sendBtn.disabled = true;
    els.input.value = "";
    autosize();

    // Optimistic user bubble
    if (!els.messages.querySelector(".msg") && els.empty.parentNode) {
      els.empty.style.display = "none";
    }
    const existing = [...els.messages.querySelectorAll(".msg")].map((n) => ({
      role: n.classList.contains("user") ? "user" : "assistant",
      content: n.querySelector(".bubble")?.innerText || "",
    }));
    existing.push({ role: "user", content: message });
    renderMessages(existing);
    showTyping();

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message, chat_id: currentChatId }),
      });
      const data = await res.json();
      hideTyping();
      if (data.chat_id) currentChatId = data.chat_id;
      setTitle(data.title || APP_NAME);
      renderMessages(data.messages || []);
      await loadChatList(els.search.value.trim());
    } catch (err) {
      hideTyping();
      existing.push({ role: "assistant", content: "Bağlantı hatası. Tekrar deneyin." });
      renderMessages(existing);
    } finally {
      busy = false;
      els.sendBtn.disabled = false;
      els.input.focus();
    }
  });

  // init
  loadChatList();
  renderMessages([]);
  els.input.focus();
})();
