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

  function listOrEmpty(items, empty) {
    if (!items || !items.length) return `<li>${escapeHtml(empty)}</li>`;
    return items.map((x) => `<li>${escapeHtml(x)}</li>`).join("");
  }

  function render(data) {
    results.hidden = false;
    document.getElementById("stats").innerHTML = [
      ["Belge türü", data.belge_turu || "—"],
      ["Karakter", data.karakter ?? "—"],
    ]
      .map(([k, v]) => `<span class="chip">${k}: <b>${escapeHtml(String(v))}</b></span>`)
      .join("");

    document.getElementById("kisa").textContent = data.kisa_ozet || "Özet üretilemedi.";
    document.getElementById("noktalar").innerHTML = listOrEmpty(
      data.ana_noktalar,
      "Ana nokta yok."
    );
    document.getElementById("kararlar").innerHTML = listOrEmpty(
      data.kararlar_veya_sonuclar,
      "Belirgin karar/sonuç yok."
    );
    document.getElementById("uyarilar").innerHTML = listOrEmpty(
      data.uyarilar,
      "Uyarı yok."
    );
    document.getElementById("disc").textContent = data.disclaimer || "";
    results.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    runBtn.disabled = true;
    results.hidden = true;
    showStatus("Özetleniyor…");

    const fd = new FormData();
    if (fileInput.files[0]) fd.append("file", fileInput.files[0]);
    fd.append("text", textEl.value || "");

    try {
      const res = await fetch("/api/summarize", { method: "POST", body: fd });
      const data = await res.json();
      if (!res.ok) {
        showStatus(data.error || "Özetleme başarısız.", true);
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
