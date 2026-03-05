"""
stats_enricher.py
"""

import requests
from datetime import datetime
from difflib import SequenceMatcher
from typing import Optional

_elo_cache:   dict[str, float] = {}
_fdata_cache: dict[str, dict]  = {}

HEADERS    = {"User-Agent": "Mozilla/5.0"}
FDATA_BASE = "https://api.football-data.org/v4"
FDATA_KEY  = ""  # opcional: regístrate gratis en football-data.org

LEAGUE_CODES: dict[str, str] = {
    "PREMIER LEAGUE":  "PL",
    "LA LIGA":         "PD",
    "BUNDESLIGA":      "BL1",
    "SERIE A":         "SA",
    "LIGUE 1":         "FL1",
    "CHAMPIONSHIP":    "ELC",
    "PRIMEIRA LIGA":   "PPL",
    "EREDIVISIE":      "DED",
    "CHAMPIONS LEAGUE":"CL",
}


def _sim(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


# ── Club Elo ───────────────────────────────────────────────

def fetch_club_elo() -> dict[str, float]:
    global _elo_cache
    if _elo_cache:
        return _elo_cache
    today = datetime.now().strftime("%Y-%m-%d")
    try:
        r = requests.get(f"http://api.clubelo.com/{today}", headers=HEADERS, timeout=15)
        r.raise_for_status()
        for line in r.text.strip().split("\n")[1:]:
            parts = line.split(",")
            if len(parts) >= 5:
                try:
                    _elo_cache[parts[1].lower().strip()] = float(parts[4])
                except (ValueError, IndexError):
                    pass
        print(f"  ✓ Club Elo: {len(_elo_cache)} equipos")
    except Exception as ex:
        print(f"  ⚠ Club Elo no disponible: {ex}")
    return _elo_cache


def get_team_elo(name: str, elo_data: dict[str, float]) -> Optional[float]:
    if not elo_data or not name:
        return None
    best_score = 0.0
    best_elo: Optional[float] = None
    for k, v in elo_data.items():
        s = _sim(name, k)
        if s > best_score:
            best_score = s
            best_elo = v
    if best_score >= 0.55 and best_elo is not None:
        return round(float(best_elo), 0)
    return None


# ── football-data.org ──────────────────────────────────────

def _fdata_headers() -> dict:
    h = dict(HEADERS)
    if FDATA_KEY:
        h["X-Auth-Token"] = FDATA_KEY
    return h


def fetch_standings(league_code: str) -> dict[str, dict]:
    global _fdata_cache
    if league_code in _fdata_cache:
        return _fdata_cache[league_code]
    try:
        r = requests.get(
            f"{FDATA_BASE}/competitions/{league_code}/standings",
            headers=_fdata_headers(), timeout=15
        )
        if r.status_code in (403, 429):
            return {}
        r.raise_for_status()
        data = r.json()
        result: dict[str, dict] = {}
        for table in data.get("standings", []):
            if table.get("type") != "TOTAL":
                continue
            for row in table.get("table", []):
                name = row.get("team", {}).get("name", "").lower()
                result[name] = {
                    "pos":  row.get("position", 0),
                    "pts":  row.get("points", 0),
                    "gf":   row.get("goalsFor", 0),
                    "ga":   row.get("goalsAgainst", 0),
                    "gd":   row.get("goalDifference", 0),
                    "won":  row.get("won", 0),
                    "draw": row.get("draw", 0),
                    "lost": row.get("lost", 0),
                    "form": row.get("form", ""),
                }
        _fdata_cache[league_code] = result
        print(f"  ✓ football-data [{league_code}]: {len(result)} equipos")
        return result
    except Exception:
        return {}


def get_league_code(competition_raw: str) -> Optional[str]:
    comp = competition_raw.upper()
    for keyword, code in LEAGUE_CODES.items():
        if keyword in comp:
            return code
    return None


def get_team_stats(name: str, standings: dict[str, dict]) -> Optional[dict]:
    if not standings or not name:
        return None
    best_score = 0.0
    best_data: Optional[dict] = None
    for k, v in standings.items():
        s = _sim(name, k)
        if s > best_score:
            best_score = s
            best_data = v
    return best_data if best_score >= 0.55 else None


# ── Enriquecedor principal ─────────────────────────────────

def enrich_with_stats(predictions: list[dict]) -> list[dict]:
    print("  → Cargando Club Elo ratings...")
    elo_data = fetch_club_elo()

    # Pre-cargar standings de las ligas presentes
    league_standings: dict[str, dict] = {}
    for pred in predictions:
        code = get_league_code(pred.get("competicion", ""))
        if code and code not in league_standings:
            league_standings[code] = fetch_standings(code)

    enriched: list[dict] = []

    for pred in predictions:
        p = dict(pred)
        local     = str(pred.get("equipo_local", ""))
        visitante = str(pred.get("equipo_visitante", ""))
        comp      = str(pred.get("competicion", ""))

        # ── Elo ──
        elo_l = get_team_elo(local, elo_data)
        elo_v = get_team_elo(visitante, elo_data)
        p["elo_local"]     = elo_l
        p["elo_visitante"] = elo_v

        if elo_l is not None and elo_v is not None:
            diff = float(elo_l) - float(elo_v)
            p["elo_diff"] = round(diff, 0)
            p["elo_favorito"] = (
                "LOCAL"     if diff > 30  else
                "VISITANTE" if diff < -30 else
                "PAREJO"
            )
        else:
            p["elo_diff"]     = None
            p["elo_favorito"] = None

        # ── Tabla de posiciones ──
        code = get_league_code(comp)
        standings = league_standings.get(code, {}) if code else {}
        sl = get_team_stats(local, standings)
        sv = get_team_stats(visitante, standings)

        p["local_pos"]   = sl["pos"]  if sl else None
        p["local_pts"]   = sl["pts"]  if sl else None
        p["local_form"]  = sl["form"] if sl else None
        p["visita_pos"]  = sv["pos"]  if sv else None
        p["visita_pts"]  = sv["pts"]  if sv else None
        p["visita_form"] = sv["form"] if sv else None

        enriched.append(p)

    return enriched  # ← este return faltaba en el archivo cortado