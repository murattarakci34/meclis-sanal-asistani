# Meclis Sanal Asistanı — cPanel yayınlama

Bu proje **Flask** ile yayınlanır (Streamlit paylaşımlı cPanel’de çalışmaz).

## 1) Zip oluştur (Windows bilgisayarında)

PowerShell’de proje klasöründe:

```powershell
.\make_publish_zip.ps1
```

Oluşan dosya: `MeclisSanalAsistani-publish.zip`

## 2) cPanel’e yükle

1. cPanel → **File Manager**
2. `public_html` veya alt klasör (ör. `public_html/asistan`) aç
3. Zip’i Upload et → Extract (çıkar)
4. Zip’i silebilirsin

## 3) Python App kur

1. cPanel → **Setup Python App** (veya Application Manager)
2. **Create Application**
   - Python version: **3.10+** (mümkünse 3.11/3.12)
   - Application root: zip’i açtığın klasör (ör. `asistan`)
   - Application URL: domain veya alt yol (`/asistan`)
   - Application startup file: **`passenger_wsgi.py`**
   - Application Entry point: **`application`**
3. **Create**

## 4) Paketleri kur

Python App ekranında **Configuration files** / terminal:

```bash
pip install -r requirements.txt
```

veya cPanel’deki “Run Pip Install” ile `requirements.txt` seç.

## 5) API key

`config.py` içinde `OPENAI_API_KEY` dolu olsun  
veya Python App → Environment variables:

```text
OPENAI_API_KEY=sk-...
```

## 6) Kaynak dosyalar

PDF / DOCX / TXT dosyalarını `kaynak/` klasörüne koy.

## 7) Yeniden başlat

Python App → **Restart**

Tarayıcıda domain adresini aç.

---

## Yerelde test (yayın öncesi)

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python webapp.py
```

Adres: http://127.0.0.1:8080

---

## Sorun giderme

| Sorun | Çözüm |
|---|---|
| 503 / Passenger error | Restart; `passenger_wsgi.py` doğru mu bak |
| Module not found | `pip install -r requirements.txt` tekrar |
| API hatası | `OPENAI_API_KEY` kontrol et |
| Boş cevap | `kaynak/` dolu mu; internet (ddgs) engelli mi |

Destek: Hosting’de **Setup Python App** yoksa paylaşımlı hosting bu uygulamayı çalıştıramaz; VPS gerekir.
