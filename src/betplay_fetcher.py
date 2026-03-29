"""
betplay_fetcher.py
BetPlay Colombia usa Kambi como plataforma de sportsbook.
La API pública Kambi no requiere autenticación.
"""

import re
import requests
from datetime import datetime, timezone
from difflib import SequenceMatcher

# Kambi endpoints para BetPlay Colombia
KAMBI_BASE    = "https://eu-offering-api.kambicdn.com/offering/v2018/betplay"
EVENTS_URL    = f"{KAMBI_BASE}/listView/football.json"
BETOFFER_URL  = f"{KAMBI_BASE}/betoffer/event/{{event_id}}.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept": "application/json",
    "Referer": "https://betplay.com.co/",
    "Origin":  "https://betplay.com.co",
}

PARAMS = {
    "lang":       "es_CO",
    "market":     "CO",
    "client_id":  "2",
    "channel_id": "1",
    "ncid":       "1",
}


def _get(url: str, params: dict = {}) -> dict | None:
    try:
        r = requests.get(url, headers=HEADERS, params={**PARAMS, **params}, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None          # ← siempre retorna algo


def fetch_football_events() -> list[dict]:
    data = _get(EVENTS_URL)
    if not data:
        return []
    events: list[dict] = []
    for group in data.get("group", []):
        for event in group.get("event", []):
            odds_1x2: dict[str, float] = {}
            for bo in event.get("betOffer", []):
                if bo.get("criterion", {}).get("label", "").lower() in ("match", "1x2", "resultado"):
                    for outcome in bo.get("outcome", []):
                        lbl = outcome.get("label", "").upper()
                        odds = outcome.get("odds", 0) / 1000
                        if lbl == "1" or "HOME" in lbl:
                            odds_1x2["odds_1"] = round(odds, 2)
                        elif lbl == "X" or "DRAW" in lbl:
                            odds_1x2["odds_x"] = round(odds, 2)
                        elif lbl == "2" or "AWAY" in lbl:
                            odds_1x2["odds_2"] = round(odds, 2)
            events.append({
                "event_id":   event.get("id"),
                "home":       event.get("homeName", ""),
                "away":       event.get("awayName", ""),
                "start":      event.get("start", ""),
                "competition":group.get("name", ""),
                "odds_1":     odds_1x2.get("odds_1"),
                "odds_x":     odds_1x2.get("odds_x"),
                "odds_2":     odds_1x2.get("odds_2"),
            })
    return events            # ← siempre retorna la lista (vacía o no)


def _clean(name: str) -> str:
    """Limpia nombres de equipos para mejor matching."""
    n = name.lower()
    n = re.sub(r'\b(atletico|at\.|atl\.)\b', 'atl', n)
    n = re.sub(r'\b(f\.c\.|fc)\b', '', n)
    n = re.sub(r'\b(deportivo|dep\.)\b', 'dep', n)
    n = re.sub(r'\s+', ' ', n).strip()
    return n

def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, _clean(a), _clean(b)).ratio()


def match_betplay_odds(prediction: dict, betplay_events: list[dict],
                       threshold: float = 0.55) -> dict | None:
    """
    Intenta hacer match entre un partido de pronosticosfutbol365
    y un evento de BetPlay por similitud de nombre de equipos.
    Devuelve el evento BetPlay más similar si supera el threshold.
    """
    local = prediction.get("equipo_local", "")
    visitante = prediction.get("equipo_visitante", "")
    if not local:
        return None

    best_score = 0
    best_event = None
    for ev in betplay_events:
        score = (
            _similarity(local, ev["home"]) * 0.5 +
            _similarity(visitante, ev["away"]) * 0.5
        )
        if score > best_score:
            best_score = score
            best_event = ev

    return best_event if best_score >= threshold else None


def enrich_with_betplay(predictions: list[dict]) -> list[dict]:
    """
    Agrega odds de BetPlay a cada predicción si hay match.
    Agrega: betplay_odds_1, betplay_odds_x, betplay_odds_2,
            betplay_impl_prob_1, betplay_impl_prob_2, betplay_event_id
    """
    print("  → Consultando BetPlay (Kambi API)...")
    events = fetch_football_events()
    if not events:
        print("  ⚠ BetPlay no disponible o sin partidos.")
        return predictions

    enriched = []
    matches_found = 0
    for pred in predictions:
        ev = match_betplay_odds(pred, events)
        p = dict(pred)
        if ev and ev.get("odds_1") and ev.get("odds_2"):
            # Probabilidad implícita = 1/cuota (sin margen)
            o1, ox, o2 = ev["odds_1"], ev.get("odds_x",0), ev["odds_2"]
            total = (1/o1 if o1 else 0) + (1/ox if ox else 0) + (1/o2 if o2 else 0)
            p["betplay_odds_1"]      = o1
            p["betplay_odds_x"]      = ox
            p["betplay_odds_2"]      = o2
            p["betplay_impl_prob_1"] = round((1/o1)/total*100, 1) if o1 and total else 0
            p["betplay_impl_prob_x"] = round((1/ox)/total*100, 1) if ox and total else 0
            p["betplay_impl_prob_2"] = round((1/o2)/total*100, 1) if o2 and total else 0
            p["betplay_event_id"]    = ev["event_id"]
            p["betplay_matched"]     = True
            matches_found += 1
        else:
            p["betplay_odds_1"]      = None
            p["betplay_odds_x"]      = None
            p["betplay_odds_2"]      = None
            p["betplay_impl_prob_1"] = 0
            p["betplay_impl_prob_x"] = 0
            p["betplay_impl_prob_2"] = 0
            p["betplay_event_id"]    = None
            p["betplay_matched"]     = False
        enriched.append(p)

    print(f"  ✓ {matches_found}/{len(predictions)} partidos con odds de BetPlay")
    return enriched