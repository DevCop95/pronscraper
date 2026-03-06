"""
scraper.py — Descarga HTML con cloudscraper para evitar bloqueos 403.
cloudscraper imita un navegador real y maneja protecciones Cloudflare/bot.
"""

import time
import cloudscraper
from urllib.parse import urlparse

ALLOWED_URL = "https://pronosticosfutbol365.com/predicciones-de-futbol/"

HEADERS = {
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Referer": "https://pronosticosfutbol365.com/",
    "DNT": "1",
}


def fetch_html(url: str, retries: int = 4, delay: float = 2.0) -> str:
    parsed = urlparse(url)
    allowed = urlparse(ALLOWED_URL)
    if parsed.netloc != allowed.netloc or parsed.path != allowed.path:
        raise ValueError(f"URL no permitida: {url}")

    scraper = cloudscraper.create_scraper(
        browser={"browser": "chrome", "platform": "windows", "mobile": False}
    )
    scraper.headers.update(HEADERS)

    last_err = None
    for attempt in range(1, retries + 1):
        try:
            resp = scraper.get(url, timeout=30)
            resp.raise_for_status()
            if len(resp.text) < 500:
                raise ValueError("Respuesta demasiado corta — posible bloqueo")
            return resp.text
        except Exception as ex:
            last_err = ex
            print(f"  ⚠ Intento {attempt}/{retries} falló: {ex}")
            if attempt < retries:
                time.sleep(delay * attempt)

    raise RuntimeError(f"No se pudo descargar después de {retries} intentos: {last_err}")