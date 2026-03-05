"""
scraper.py — HTTP fetcher con reintentos y validación de URL.
Solo permite la URL canónica de pronosticosfutbol365.
"""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

ALLOWED_URL = "https://pronosticosfutbol365.com/predicciones-de-futbol/"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Connection": "keep-alive",
    "Referer": "https://www.google.com/",
}


def _build_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=4,
        backoff_factor=0.8,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "HEAD", "OPTIONS"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def fetch_html(url: str, timeout: int = 25, extra_headers: dict | None = None) -> str:
    """Descarga el HTML de la URL permitida. Lanza ValueError si es otra URL."""
    if url.strip().rstrip("/") != ALLOWED_URL.rstrip("/"):
        raise ValueError(
            f"URL no permitida.\n"
            f"  Esperada : {ALLOWED_URL}\n"
            f"  Recibida : {url}"
        )
    session = _build_session()
    hdrs = HEADERS.copy()
    if extra_headers:
        hdrs.update(extra_headers)
    resp = session.get(url, headers=hdrs, timeout=timeout)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding or "utf-8"
    return resp.text
