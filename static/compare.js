(() => {
  const form = document.getElementById("form");
  const runBtn = document.getElementById("runBtn");
  const status = document.getElementById("status");
  const results = document.getElementById("results");

  const oldFile = document.getElementById("oldFile");
  const newFile = document.getElementById("newFile");
  const oldText = document.getElementById("oldText");
  const newText = document.getElementById("newText");
  const oldFname = document.getElementById("oldFname");
  const newFname = document.getElementById("newFname");

  oldFile.addEventListener("change", () => {
    oldFname.textContent = oldFile.files[0]?.name || "";
  });
  newFile.addEventListener("change", () => {
    newFname.textContent = newFile.files[0]?.name || "";
  });

  function tipLabel(t) {
    const map = {
      degisti: "Değişti",
      eklendi: "Eklendi",
      kaldirildi: "Kaldırıldı",
      degismedi: "Değişmedi",
    };
    return map[t] || t || "—";
  }

  function tipClass(t) {
    if (["degisti", "eklendi", "kaldirildi", "degismedi"].includes(t)) return t;
    return "degisti";
  }

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

  function render(data) {
    results.hidden = false;
    const st = data.istatistik || {};
    document.getElementById("stats").innerHTML = [
      ["Eski parça", st.eski_parca],
      ["Yeni parça", st.yeni_parca],
      ["Değişen", st.degisen],
      ["Eklenen", st.eklenen],
      ["Kaldırılan", st.kaldirilan],
    ]
      .map(([k, v]) => `<span class="chip">${k}: <b>${v ?? 0}</b></span>`)
      .join("");

    const ozet = data.ozet || [];
    document.getElementById("ozet").innerHTML = ozet.length
      ? ozet.map((x) => `<li>${escapeHtml(x)}</li>`).join("")
      : "<li>Özet üretilemedi.</li>";

    const tablo = data.tablo || [];
    document.getElementById("tablo").innerHTML = tablo.length
      ? tablo
          .map((r) => {
            const tip = r.degisim_tipi || r.change_type || "";
            return `<tr>
            <td>${escapeHtml(r.konu || "")}</td>
            <td>${escapeHtml(r.eski || "—")}</td>
            <td>${escapeHtml(r.yeni || "—")}</td>
            <td><span class="badge ${tipClass(tip)}">${escapeHtml(tipLabel(tip))}</span></td>
          </tr>`;
          })
          .join("")
      : `<tr><td colspan="4">Tablo satırı yok.</td></tr>`;

    const diffs = data.diffs || [];
    document.getElementById("diffs").innerHTML = diffs.length
      ? diffs
          .map(
            (d) => `<div class="diff-card">
          <div class="meta">
            <strong>${escapeHtml(d.topic || "")}</strong>
            <span class="badge ${tipClass(d.change_type)}">${escapeHtml(tipLabel(d.change_type))}</span>
          </div>
          <div class="diff-body">${d.html || ""}</div>
        </div>`
          )
          .join("")
      : "<p>Gösterilecek metin farkı yok (metinler aynı veya hizalanamadı).</p>";

    const etki = data.etki_notlari || [];
    document.getElementById("etki").innerHTML = etki.length
      ? etki.map((x) => `<li>${escapeHtml(x)}</li>`).join("")
      : "<li>Etki notu yok.</li>";

    document.getElementById("guven").textContent =
      "Güven: " + String(data.guven || "orta").toUpperCase();
    const uyarilar = data.uyarilar || [];
    document.getElementById("uyarilar").innerHTML = uyarilar.length
      ? uyarilar.map((x) => `<li>${escapeHtml(x)}</li>`).join("")
      : "<li>Uyarı yok.</li>";
    document.getElementById("disc").textContent = data.disclaimer || "";

    results.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    runBtn.disabled = true;
    results.hidden = true;
    showStatus("Karşılaştırılıyor… (madde hizalama + diff + yapay zekâ analizi)");

    const fd = new FormData();
    if (oldFile.files[0]) fd.append("old_file", oldFile.files[0]);
    if (newFile.files[0]) fd.append("new_file", newFile.files[0]);
    fd.append("old_text", oldText.value || "");
    fd.append("new_text", newText.value || "");

    try {
      const res = await fetch("/api/compare", { method: "POST", body: fd });
      const data = await res.json();
      if (!res.ok) {
        showStatus(data.error || "Karşılaştırma başarısız.", true);
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
