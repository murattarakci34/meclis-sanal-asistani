(() => {
  const form = document.getElementById("form");
  const runBtn = document.getElementById("runBtn");
  const status = document.getElementById("status");
  const results = document.getElementById("results");
  const fileInput = document.getElementById("file");
  const textEl = document.getElementById("text");
  const meta = document.getElementById("meta");
  const fname = document.getElementById("fname");
  const thumb = document.getElementById("thumb");
  const modeEl = document.getElementById("mode");
  const countEl = document.getElementById("count");
  const copyBtn = document.getElementById("copyBtn");

  let lastQuestions = [];

  fileInput.addEventListener("change", () => {
    const f = fileInput.files[0];
    if (!f) {
      meta.hidden = true;
      thumb.hidden = true;
      thumb.removeAttribute("src");
      fname.textContent = "";
      return;
    }
    meta.hidden = false;
    fname.textContent = f.name + (f.size ? ` · ${(f.size / 1024).toFixed(0)} KB` : "");
    if (f.type.startsWith("image/")) {
      thumb.src = URL.createObjectURL(f);
      thumb.hidden = false;
    } else {
      thumb.hidden = true;
      thumb.removeAttribute("src");
    }
  });

  function escapeHtml(s) {
    return String(s || "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;");
  }

  function showStatus(msg, isErr) {
    status.hidden = false;
    status.textContent = msg;
    status.classList.toggle("err", !!isErr);
  }

  function catLabel(c) {
    const map = {
      kapsam: "Kapsam",
      mali: "Mali",
      hukuki: "Hukuki",
      uygulama: "Uygulama",
      risk: "Risk",
      surec: "Süreç",
      diger: "Diğer",
    };
    return map[c] || c || "Diğer";
  }

  function render(data) {
    results.hidden = false;
    lastQuestions = data.sorular || [];
    document.getElementById("stats").innerHTML = [
      ["Mod", data.mod_aciklama || data.mod || "—"],
      ["Belge", data.belge_turu || "—"],
      ["Soru", lastQuestions.length],
    ]
      .map(([k, v]) => `<span class="chip">${k}: <b>${escapeHtml(String(v))}</b></span>`)
      .join("");

    const box = document.getElementById("sorular");
    if (!lastQuestions.length) {
      box.innerHTML = `<div class="block"><p>Soru üretilemedi.</p></div>`;
    } else {
      box.innerHTML = lastQuestions
        .map(
          (q, i) => `<article class="q-card">
          <div class="q-top">
            <span class="q-num">#${i + 1}</span>
            <span class="badge degisti">${escapeHtml(catLabel(q.kategori))}</span>
          </div>
          <p class="q-text">${escapeHtml(q.soru)}</p>
          <div class="q-meta">
            ${q.neden_onemli ? `<div><strong>Neden önemli:</strong>${escapeHtml(q.neden_onemli)}</div>` : ""}
            ${q.metinde_ipucu ? `<div><strong>Metinde ipucu:</strong>${escapeHtml(q.metinde_ipucu)}</div>` : ""}
          </div>
        </article>`
        )
        .join("");
    }

    const uyarilar = data.uyarilar || [];
    document.getElementById("uyarilar").innerHTML = uyarilar.length
      ? uyarilar.map((x) => `<li>${escapeHtml(x)}</li>`).join("")
      : "<li>Uyarı yok.</li>";
    document.getElementById("disc").textContent = data.disclaimer || "";
    results.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  copyBtn.addEventListener("click", async () => {
    if (!lastQuestions.length) return;
    const text = lastQuestions
      .map((q, i) => `${i + 1}. [${catLabel(q.kategori)}] ${q.soru}`)
      .join("\n");
    try {
      await navigator.clipboard.writeText(text);
      showStatus("Sorular panoya kopyalandı.");
    } catch {
      showStatus("Kopyalanamadı — metni elle seçin.", true);
    }
  });

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    runBtn.disabled = true;
    results.hidden = true;
    showStatus("Sorular üretiliyor…");

    const fd = new FormData();
    if (fileInput.files[0]) fd.append("file", fileInput.files[0]);
    fd.append("text", textEl.value || "");
    fd.append("mode", modeEl.value);
    fd.append("count", countEl.value);

    try {
      const res = await fetch("/api/questions", { method: "POST", body: fd });
      const data = await res.json();
      if (!res.ok) {
        showStatus(data.error || "Soru üretimi başarısız.", true);
        return;
      }
      showStatus("Tamamlandı.");
      render(data);
    } catch (err) {
      showStatus("Bağlantı hatası: " + err, true);
    } finally {
      runBtn.disabled = false;
    }
  });
})();
