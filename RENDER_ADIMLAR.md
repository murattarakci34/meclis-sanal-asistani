# Render’a ücretsiz yayınlama

Hazır dosyalar: `Procfile`, `render.yaml`, `runtime.txt`, `webapp.py`

## 1) GitHub’a yükle

1. https://github.com → giriş yap → **New repository**
2. Repo adı: `meclis-sanal-asistani` (Public veya Private)
3. **Create repository**
4. Bilgisayarında proje klasöründe PowerShell:

```powershell
cd C:\Users\Murat\Documents\Chat
git init -b main
git add .
git commit -m "Meclis Sanal Asistani Render hazir"
git remote add origin https://github.com/KULLANICI_ADIN/meclis-sanal-asistani.git
git push -u origin main
```

`KULLANICI_ADIN` yerine kendi GitHub kullanıcı adını yaz.

> Not: `.env` GitHub’a gitmez (güvenlik). API key’i Render’a ayrıca gireceksin.

## 2) Render hesabı

1. https://render.com → **Get Started** (GitHub ile giriş önerilir)
2. GitHub hesabını yetkilendir

## 3) Web Service oluştur

1. Dashboard → **New +** → **Web Service**
2. GitHub reposunu seç: `meclis-sanal-asistani`
3. Ayarlar:
   - **Name:** `meclis-sanal-asistani`
   - **Region:** Frankfurt (veya yakın)
   - **Branch:** `main`
   - **Runtime:** Python
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn webapp:app --bind 0.0.0.0:$PORT --workers 1 --threads 2 --timeout 120`
   - **Instance type:** **Free**
4. **Environment Variables** → Add:
   - Key: `OPENAI_API_KEY`
   - Value: OpenAI anahtarın (`sk-...`)
5. **Create Web Service**

## 4) Bitince

Deploy 2–5 dk sürebilir. Yeşil **Live** olunca adres şöyle olur:

`https://meclis-sanal-asistani.onrender.com`

(İsim farklıysa Render’ın verdiği URL’i kullan.)

## Önemli notlar

- Ücretsiz planda site ~15 dk işlemeyince uykuya geçer; ilk açılış 30–60 sn sürebilir.
- `kaynak/` klasöründeki PDF’ler deploy ile birlikte gider.
- Sohbet geçmişi (`sohbetler/`) sunucu yeniden başlayınca silinebilir (ücretsiz disk kalıcı değil).
