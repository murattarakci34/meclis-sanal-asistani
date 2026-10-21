"""
cPanel → Setup Python App → Application startup file: passenger_wsgi.py

Bu dosya Flask uygulamasını Passenger'a bağlar.
"""

import os
import sys

# Proje klasörü
BASE = os.path.dirname(os.path.abspath(__file__))
if BASE not in sys.path:
    sys.path.insert(0, BASE)

os.chdir(BASE)

# cPanel Python App virtualenv'i genelde otomatik aktif olur.
# Gerekirse: os.environ['OPENAI_API_KEY'] = 'sk-...'

from webapp import app as application  # noqa: E402
