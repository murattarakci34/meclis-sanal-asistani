"""
OpenAI / uygulama ayarları.
API key: ortam değişkeni OPENAI_API_KEY veya yerel .env dosyası.
"""

import os
from pathlib import Path

# Yerel .env yükle (Render'da gerekmez; orada Environment Variables kullanılır)
try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass

APP_NAME = "Meclis Sanal Asistanı"

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "").strip()

# Kullanılacak modeller
CHAT_MODEL = "gpt-4o-mini"  # Daha güçlü için: "gpt-4o"
EMBEDDING_MODEL = "text-embedding-3-small"

# Kaynak klasörü (PDF, Word, TXT, JSON)
KAYNAK_DIR = "kaynak"

# Her chunk yaklaşık karakter sayısı ve örtüşme
CHUNK_SIZE = 1200
CHUNK_OVERLAP = 200

# Soruya en yakın kaç parça LLM'e gönderilsin
TOP_K = 8

# Belge benzerlik eşiği (düşükse internete daha çok dayanır)
MIN_DOC_SCORE = 0.28
