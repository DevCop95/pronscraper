"""
scraper.py — Fetcher con cloudscraper (bypass Cloudflare/403).
cloudscraper simula un navegador real y resuelve challenges JS.
"""

import time
import random
import cloudscraper

ALLOWED_URL = "https://pronosticosfutbol365.com/predicciones-de-futbol/"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Cache-Control": "max-age=0",
    "Referer": "https://www.google.com/search?q=pronosticos+futbol+hoy",
}

MAX_RETRIES = 4


def fetch_html(url: str, timeout: int = 45, extra_headers: dict | None = None) -> str:
    if url.strip().rstrip("/") != ALLOWED_URL.rstrip("/"):
        raise ValueError(f"URL no permitida: {url}")

    hdrs = HEADERS.copy()
    if extra_headers:
        hdrs.update(extra_headers)

    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            scraper = cloudscraper.create_scraper(
                browser={
                    "browser": "chrome",
                    "platform": "windows",
                    "desktop": True,
                },
                delay=5,
            )
            scraper.headers.update(hdrs)

            print(f"   Intento {attempt}/{MAX_RETRIES} — {url[:60]}")
            resp = scraper.get(url, timeout=timeout)

            if resp.status_code == 403:
                print(f"   ⚠ 403 recibido en intento {attempt}")
                wait = (2 ** attempt) + random.uniform(1, 3)
                print(f"   ⏳ Esperando {wait:.1f}s antes de reintentar...")
                time.sleep(wait)
                last_error = f"403 Forbidden (intento {attempt})"
                continue

            resp.raise_for_status()
            resp.encoding = resp.apparent_encoding or "utf-8"
            print(f"   ✓ Descarga exitosa ({len(resp.text)} chars)")
            return resp.text

        except Exception as ex:
            last_error = str(ex)
            if attempt < MAX_RETRIES:
                wait = (2 ** attempt) + random.uniform(0.5, 2)
                print(f"   ✗ Error intento {attempt}: {ex} — reintentando en {wait:.1f}s")
                time.sleep(wait)
            else:
                print(f"   ✗ Error final intento {attempt}: {ex}")

    raise RuntimeError(
        f"No se pudo descargar {url} tras {MAX_RETRIES} intentos. "
        f"Último error: {last_error}"
    )