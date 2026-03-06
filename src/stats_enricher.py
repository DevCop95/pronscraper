"""
stats_enricher.py — Enriquece partidos con ratings Club Elo.
Descarga el CSV de clubelo.com y hace fuzzy matching de nombres.
"""

import re, csv, io, unicodedata, requests
from typing import Any
from datetime import date

_ALIASES = {
    'dinamo':    'dynamo',  'dynamo':    'dynamo',
    'atletico':  'atletico','atlético':  'atletico',
    'lokomotif': 'lokomotiv','lokomotiv':'lokomotiv',
    'spartak':   'spartak', 'cska':      'cska',
}


def _normalize(name: str) -> str:
    name = name.lower().strip()
    name = unicodedata.normalize("NFD", name)
    name = "".join(c for c in name if unicodedata.category(c) != "Mn")
    name = re.sub(r"[^a-z0-9\s]", " ", name)
    name = re.sub(r"\s+", " ", name).strip()
    words = [_ALIASES.get(w, w) for w in name.split()]
    return " ".join(words)


def _remove_common_words(name: str) -> str:
    stops = {
        "fc","cf","sc","ac","if","bk","sk","fk","nk","gk","us","as","ss","sv","fs",
        "united","city","club","sporting","athletic","atletico","deportivo","deportiva",
        "real","royal","olympique","olympia","racing","de","del","la","el","los","las",
        "the","and","y",
    }
    words = [w for w in name.split() if w not in stops]
    return " ".join(words) if words else name


def _score_match(query: str, candidate: str) -> float:
    q = _normalize(query)
    c = _normalize(candidate)
    if q == c: return 1.0
    q2 = _remove_common_words(q)
    c2 = _remove_common_words(c)
    if q2 and c2 and q2 == c2: return 0.98
    if q in c or c in q: return 0.88
    if q2 and c2 and (q2 in c2 or c2 in q2): return 0.82
    qw = set(q.split()); cw = set(c.split())
    if not qw or not cw: return 0.0
    jaccard = len(qw & cw) / len(qw | cw)
    if q.split()[0] == c.split()[0]:
        jaccard = min(1.0, jaccard + 0.2)
    return jaccard


def _load_elo_table() -> dict[str, float]:
    url = f"http://api.clubelo.com/{date.today().isoformat()}"
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        reader = csv.DictReader(io.StringIO(resp.text))
        table: dict[str, float] = {}
        for row in reader:
            club = (row.get("Club") or "").strip()
            elo  = row.get("Elo") or row.get("elo") or ""
            if club and elo:
                try: table[club] = float(elo)
                except ValueError: pass
        print(f"   ✓ Club Elo: {len(table)} equipos cargados")
        return table
    except Exception as ex:
        print(f"   ⚠ No se pudo cargar Club Elo: {ex}")
        return {}


def _find_elo(team_name: str, elo_table: dict[str, float],
              threshold: float = 0.60) -> float | None:
    if not team_name or not elo_table: return None
    team_name = re.sub(r"^[\s\-–—]+", "", team_name).strip()
    best_score, best_elo = 0.0, None
    for club, elo in elo_table.items():
        score = _score_match(team_name, club)
        if score > best_score:
            best_score = score
            best_elo   = elo
    return best_elo if best_score >= threshold else None


def enrich_with_stats(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    print("   → Cargando Club Elo ratings...")
    elo_table = _load_elo_table()
    enriched = []
    found = 0
    for it in items:
        e = dict(it)
        local  = e.get("equipo_local",    "")
        visita = e.get("equipo_visitante", "")
        elo_l  = _find_elo(local,  elo_table)
        elo_v  = _find_elo(visita, elo_table)
        e["elo_local"]     = round(elo_l, 1) if elo_l else None
        e["elo_visitante"] = round(elo_v, 1) if elo_v else None
        if elo_l and elo_v:
            diff = elo_l - elo_v
            e["elo_diff"]     = round(diff, 1)
            e["elo_favorito"] = "PAREJO" if abs(diff) < 20 else ("LOCAL" if diff > 0 else "VISITANTE")
            found += 1
        else:
            e["elo_diff"]     = None
            e["elo_favorito"] = None
        enriched.append(e)
    print(f"   ✓ Elo completo en {found}/{len(items)} partidos")
    return enriched