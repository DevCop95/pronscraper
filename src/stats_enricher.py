"""
stats_enricher.py
Usa DOS fuentes de ClubElo (sin API key, 100% gratis):

1. api.clubelo.com/Fixtures  → partidos de hoy con probabilidades pre-calculadas
                               (win/draw/loss ya computadas por ClubElo)
2. api.clubelo.com/YYYY-MM-DD → ratings Elo de todos los equipos hoy

Fuzzy matching para nombres con variantes (Dinamo/Dynamo, tildes, etc.)
"""

import re, csv, io, unicodedata, requests
from typing import Any
from datetime import date

FIXTURES_URL = "http://api.clubelo.com/Fixtures"
ELO_URL      = "http://api.clubelo.com/{date}"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; research-bot/1.0)",
    "Accept": "text/csv,*/*",
}

# ─── Normalización y Fuzzy Match ─────────────────────────────────────────────

_ALIASES = {
    "dinamo":     "dynamo",
    "dynamo":     "dynamo",
    "atletico":   "atletico",
    "atlético":   "atletico",
    "lokomotif":  "lokomotiv",
    "lokomotiv":  "lokomotiv",
    "cska":       "cska",
    "spartak":    "spartak",
    "america":    "america",
    "américa":    "america",
}

_STOPS = {
    "fc","cf","sc","ac","if","bk","sk","fk","nk","gk","us","as","ss","sv","fs",
    "united","city","club","sporting","athletic","atletico","deportivo","deportiva",
    "real","royal","olympique","olympia","racing","de","del","la","el","los","las",
    "the","and","y","1948","1903","1921",
}


def _norm(name: str) -> str:
    """Normaliza: minúsculas, sin tildes, alias aplicados, sin stops."""
    name = name.lower().strip()
    # Quitar prefijos basura del parser
    name = re.sub(r"^[\s\-–—]+", "", name)
    # Quitar tildes
    name = unicodedata.normalize("NFD", name)
    name = "".join(c for c in name if unicodedata.category(c) != "Mn")
    # Solo alfanumérico + espacios
    name = re.sub(r"[^a-z0-9\s]", " ", name)
    name = re.sub(r"\s+", " ", name).strip()
    # Aplicar alias
    words = [_ALIASES.get(w, w) for w in name.split()]
    return " ".join(words)


def _score(q: str, c: str) -> float:
    """Score 0-1 entre dos nombres ya normalizados."""
    if q == c:
        return 1.0
    if q in c or c in q:
        return 0.90

    # Sin stop words
    qw = [w for w in q.split() if w not in _STOPS]
    cw = [w for w in c.split() if w not in _STOPS]
    q2, c2 = " ".join(qw), " ".join(cw)
    if q2 and c2:
        if q2 == c2: return 0.97
        if q2 in c2 or c2 in q2: return 0.85

    # Jaccard
    qs, cs = set(q.split()), set(c.split())
    if not qs or not cs: return 0.0
    j = len(qs & cs) / len(qs | cs)
    # Bonus primera palabra
    if q.split()[0] == c.split()[0]:
        j = min(1.0, j + 0.25)
    return j


def _best_match(query: str, candidates: list[str], threshold=0.55) -> str | None:
    q = _norm(query)
    best_s, best_c = 0.0, None
    for c in candidates:
        s = _score(q, _norm(c))
        if s > best_s:
            best_s, best_c = s, c
    return best_c if best_s >= threshold else None


# ─── Fuente 1: Fixtures con probabilidades ───────────────────────────────────

def _load_fixtures() -> list[dict]:
    """
    Descarga api.clubelo.com/Fixtures y parsea probabilidades.
    Devuelve lista de dicts con: home, away, country, date,
    elo_prob_home_win, elo_prob_draw, elo_prob_away_win,
    elo_home, elo_away (si disponibles)
    """
    try:
        r = requests.get(FIXTURES_URL, headers=HEADERS, timeout=15)
        r.raise_for_status()
        reader = csv.DictReader(io.StringIO(r.text))
        fixtures = []
        for row in reader:
            try:
                # Win = suma de GD positivos (GD=1..5 y GD>5)
                gd_pos = sum(float(row.get(f"GD={i}", 0) or 0) for i in range(1, 6))
                gd_pos += float(row.get("GD>5", 0) or 0)
                # Draw = GD=0
                gd_0 = float(row.get("GD=0", 0) or 0)
                # Loss = suma de GD negativos
                gd_neg = sum(float(row.get(f"GD=-{i}", 0) or 0) for i in range(1, 6))
                gd_neg += float(row.get("GD<-5", 0) or 0)

                fixtures.append({
                    "date":               row.get("Date", ""),
                    "country":            row.get("Country", ""),
                    "home":               row.get("Home", ""),
                    "away":               row.get("Away", ""),
                    "elo_prob_home_win":  round(gd_pos * 100, 1),
                    "elo_prob_draw":      round(gd_0   * 100, 1),
                    "elo_prob_away_win":  round(gd_neg * 100, 1),
                })
            except (ValueError, KeyError):
                continue
        today = date.today().isoformat()
        today_fixtures = [f for f in fixtures if f["date"] == today]
        print(f"   ✓ ClubElo Fixtures: {len(today_fixtures)} partidos hoy (de {len(fixtures)} totales)")
        return today_fixtures
    except Exception as ex:
        print(f"   ⚠ ClubElo Fixtures no disponible: {ex}")
        return []


# ─── Fuente 2: Elo ratings por fecha ─────────────────────────────────────────

def _load_elo_ratings() -> dict[str, float]:
    """
    Descarga api.clubelo.com/YYYY-MM-DD.
    Devuelve {nombre_club: elo}.
    """
    try:
        url = ELO_URL.format(date=date.today().isoformat())
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        reader = csv.DictReader(io.StringIO(r.text))
        table: dict[str, float] = {}
        for row in reader:
            club = (row.get("Club") or "").strip()
            elo  = row.get("Elo") or ""
            if club and elo:
                try: table[club] = float(elo)
                except ValueError: pass
        print(f"   ✓ ClubElo Ratings: {len(table)} equipos")
        return table
    except Exception as ex:
        print(f"   ⚠ ClubElo Ratings no disponible: {ex}")
        return {}


# ─── Enricher principal ───────────────────────────────────────────────────────

def enrich_with_stats(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    print("   → Cargando datos ClubElo...")
    fixtures   = _load_fixtures()
    elo_ratings = _load_elo_ratings()

    # Índice de fixtures por nombre normalizado
    fixture_index: dict[str, dict] = {}
    for f in fixtures:
        key = f"{_norm(f['home'])} vs {_norm(f['away'])}"
        fixture_index[key] = f

    fixture_names_home = [f["home"] for f in fixtures]
    fixture_names_away = [f["away"] for f in fixtures]
    elo_names = list(elo_ratings.keys())

    enriched = []
    found_fixtures = 0
    found_elo = 0

    for it in items:
        e = dict(it)
        local  = re.sub(r"^[\s\-–—]+", "", e.get("equipo_local",    "") or "").strip()
        visita = re.sub(r"^[\s\-–—]+", "", e.get("equipo_visitante","") or "").strip()

        # ── Intento 1: match en Fixtures (probabilidades pre-calculadas) ──
        matched_fixture = None
        if fixtures:
            best_home = _best_match(local,  fixture_names_home, threshold=0.60)
            if best_home:
                # Buscar el fixture que tenga ese home
                candidates = [f for f in fixtures if f["home"] == best_home]
                for f in candidates:
                    if _best_match(visita, [f["away"]], threshold=0.55):
                        matched_fixture = f
                        break

        if matched_fixture:
            e["elo_prob_home_win"] = matched_fixture["elo_prob_home_win"]
            e["elo_prob_draw"]     = matched_fixture["elo_prob_draw"]
            e["elo_prob_away_win"] = matched_fixture["elo_prob_away_win"]
            found_fixtures += 1
        else:
            e["elo_prob_home_win"] = None
            e["elo_prob_draw"]     = None
            e["elo_prob_away_win"] = None

        # ── Intento 2: Elo ratings individuales ──
        elo_l = elo_v = None
        if elo_ratings:
            best_l = _best_match(local,  elo_names, threshold=0.60)
            best_v = _best_match(visita, elo_names, threshold=0.60)
            elo_l  = round(elo_ratings[best_l], 1) if best_l else None
            elo_v  = round(elo_ratings[best_v], 1) if best_v else None

        e["elo_local"]     = elo_l
        e["elo_visitante"] = elo_v

        if elo_l and elo_v:
            diff = elo_l - elo_v
            e["elo_diff"]     = round(diff, 1)
            e["elo_favorito"] = "PAREJO" if abs(diff) < 20 else ("LOCAL" if diff > 0 else "VISITANTE")
            found_elo += 1
        else:
            e["elo_diff"]     = None
            e["elo_favorito"] = None

        enriched.append(e)

    print(f"   ✓ Fixtures ClubElo: {found_fixtures}/{len(items)} partidos con probabilidades")
    print(f"   ✓ Elo ratings: {found_elo}/{len(items)} partidos con ambos equipos")
    return enriched

# ─── Historial últimos 5 partidos ─────────────────────────────────────────────

_form_cache: dict[str, list[dict]] = {}   # caché en memoria para no pedir 2x el mismo equipo


def _fetch_team_form(club_name: str) -> list[dict]:
    """
    Llama api.clubelo.com/ClubName → obtiene últimos 5 partidos.
    Cada fila del CSV es un período Elo. Cuando cambia entre filas → hubo partido.
    El cambio de Elo nos dice si ganó (+), empató (~0) o perdió (-).
    Devuelve lista de dicts: [{date, elo_before, elo_after, change, result}]
    """
    if club_name in _form_cache:
        return _form_cache[club_name]

    url = f"http://api.clubelo.com/{club_name.replace(' ', '')}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=5)
        r.raise_for_status()
        reader = csv.DictReader(io.StringIO(r.text))
        rows = list(reader)
        if not rows:
            return []

        matches = []
        today_str = date.today().isoformat()
        for i in range(1, len(rows)):
            prev = rows[i - 1]
            curr = rows[i]
            try:
                match_date = curr.get("From", "")
                # Solo partidos pasados
                if not match_date or match_date >= today_str:
                    continue
                elo_before = float(prev.get("Elo") or 0)
                elo_after  = float(curr.get("Elo") or 0)
                change     = round(elo_after - elo_before, 1)
                # Solo filas con cambio real (partidos jugados, no períodos vacíos)
                if abs(change) < 3:
                    continue
                if change > 5:    result = "W"
                elif change < -5: result = "L"
                else:             result = "D"
                matches.append({
                    "date":       match_date,
                    "elo_before": round(elo_before, 1),
                    "elo_after":  round(elo_after,  1),
                    "change":     change,
                    "result":     result,
                })
            except (ValueError, TypeError):
                continue

        # Los últimos 5 (más recientes primero)
        last5 = list(reversed(matches[-5:])) if len(matches) >= 5 else list(reversed(matches))
        _form_cache[club_name] = last5
        return last5

    except Exception:
        _form_cache[club_name] = []
        return []


def _get_form_string(matches: list[dict]) -> str:
    """Convierte lista de resultados a string: 'WDLLW'"""
    return "".join(m["result"] for m in matches)


def enrich_with_form(items: list[dict[str, Any]],
                     elo_names: list[str]) -> list[dict[str, Any]]:
    """
    Agrega forma (últimos 5 partidos) SOLO para equipos con Elo rating.
    Evita hacer 238 requests para equipos que ClubElo no conoce.
    """
    print("   → Obteniendo forma (últimos 5 partidos)...")
    enriched = []
    found = 0

    for it in items:
        e = dict(it)
        local  = re.sub(r"^[\s\-–—]+", "", e.get("equipo_local",    "") or "").strip()
        visita = re.sub(r"^[\s\-–—]+", "", e.get("equipo_visitante","") or "").strip()

        # Solo pedir forma si el equipo YA tiene Elo (está en ClubElo)
        has_elo_l = bool(e.get("elo_local"))
        has_elo_v = bool(e.get("elo_visitante"))

        best_l = _best_match(local,  elo_names, threshold=0.60) if has_elo_l else None
        best_v = _best_match(visita, elo_names, threshold=0.60) if has_elo_v else None

        form_l = _fetch_team_form(best_l) if best_l else []
        form_v = _fetch_team_form(best_v) if best_v else []

        e["local_form"]      = _get_form_string(form_l)
        e["visita_form"]     = _get_form_string(form_v)
        e["local_form_data"] = form_l
        e["visita_form_data"]= form_v

        # Bonus para el analyzer: % victorias en últimos 5
        if form_l:
            e["local_win_rate5"]  = round(form_l.count({"result":"W"}) / len(form_l) * 100 if form_l else 0)
            wins_l = sum(1 for m in form_l if m["result"] == "W")
            e["local_win_rate5"]  = round(wins_l / len(form_l) * 100)
        else:
            e["local_win_rate5"]  = None

        if form_v:
            wins_v = sum(1 for m in form_v if m["result"] == "W")
            e["visita_win_rate5"] = round(wins_v / len(form_v) * 100)
        else:
            e["visita_win_rate5"] = None

        if form_l or form_v:
            found += 1

        enriched.append(e)

    print(f"   ✓ Forma obtenida: {found}/{len(items)} partidos")
    return enriched