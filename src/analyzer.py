"""
analyzer.py — Analiza TODOS los partidos del día, incluyendo mercados de goles.
Pick types soportados:
  1 / 2 / X        → resultado
  1X / X2 / 12     → doble oportunidad
  OVER_15/25/35    → goles
  BTTS             → ambos anotan
  UNK              → desconocido
"""

import re
from datetime import datetime
from typing import Any


# ── Clasificación de pronóstico ──────────────────────────────

def pick_type(pronostico: str) -> str:
    p = (pronostico or "").lower().strip()

    # Dobles primero (para no confundir con simples)
    if re.search(r"\b12\b",  p): return "12"
    if re.search(r"\b1x\b",  p): return "1X"
    if re.search(r"\bx2\b",  p): return "X2"

    # Resultado simple
    if re.match(r"^1[\s—\-]",  p) or p == "1": return "1"
    if re.match(r"^2[\s—\-]",  p) or p == "2": return "2"
    if re.match(r"^x[\s—\-]",  p) or p == "x": return "X"
    if "empate" in p or "draw" in p:            return "X"

    # Mercado de goles — MUY COMUNES en este sitio
    if re.search(r"m[aá]s\s+de\s+3[.,]5|over\s*3[.,]5|\+3[.,]5", p): return "OVER_35"
    if re.search(r"m[aá]s\s+de\s+2[.,]5|over\s*2[.,]5|\+2[.,]5", p): return "OVER_25"
    if re.search(r"m[aá]s\s+de\s+1[.,]5|over\s*1[.,]5|\+1[.,]5", p): return "OVER_15"
    if re.search(r"menos\s+de|under",                               p): return "UNDER"
    if re.search(r"ambos\s+anotan|btts|both\s+teams",               p): return "BTTS"

    return "UNK"


# ── Filtro temporal ──────────────────────────────────────────

def filter_today(items: list[dict]) -> list[dict]:
    today = datetime.now().strftime("%d/%m")
    out = []
    for it in items:
        h = (it.get("hora") or "").strip()
        if not h:
            out.append(it)   # sin hora → asumir hoy
            continue
        m = re.search(r"\b(\d{1,2}/\d{1,2})\b", h)
        if m:
            if m.group(1) == today:
                out.append(it)
        else:
            out.append(it)
    return out


# ── Scoring por tipo de mercado ──────────────────────────────

def _score_resultado(prob_win: int, prob_rival: int, pick: str,
                     elo_diff: "float | None", bp_prob: float) -> int:
    """Score para picks de resultado: 1, 2, 1X, X2, 12."""
    margin  = max(0, prob_win - prob_rival)
    clarity = {"1": 1.0, "2": 1.0, "1X": 0.75, "X2": 0.75, "12": 0.65}.get(pick, 0.55)
    score   = (prob_win * 0.60) + (min(margin, 50) * 0.40) + (clarity * 20)

    if elo_diff is not None:
        bonus = min(8, abs(float(elo_diff)) / 40)
        if (elo_diff > 0 and pick in ("1","1X","12")) or \
           (elo_diff < 0 and pick in ("2","X2","12")):
            score += bonus
        else:
            score -= bonus * 0.5

    if bp_prob > 0:
        diff = abs(prob_win - bp_prob)
        if diff <= 8:    score += 8
        elif diff <= 15: score += 4
        else:            score -= 4

    return min(100, max(0, round(score)))


def _score_goles(prob_over: int, pick: str) -> int:
    """Score para picks de mercado de goles."""
    if pick == "OVER_15":
        # Muy probable si > 75%, sospechoso si < 60%
        score = (prob_over - 50) * 1.5 + 20
    elif pick == "OVER_25":
        score = (prob_over - 45) * 1.8 + 15
    elif pick == "OVER_35":
        score = (prob_over - 40) * 2.0 + 10
    else:
        score = (prob_over - 45) * 1.5 + 15
    return min(100, max(0, round(score)))


def _score_btts(prob_btts: int) -> int:
    return min(100, max(0, round((prob_btts - 40) * 1.8 + 20)))


def _tier(confidence: int) -> str:
    if confidence >= 65: return "ÉLITE"
    if confidence >= 50: return "ALTA"
    if confidence >= 35: return "MEDIA"
    return "BAJA"


def _is_value_bet(confidence: int, prob_main: int, margin: int = 0) -> bool:
    return confidence >= 55 and prob_main >= 50 and (margin >= 15 or prob_main >= 65)


# ── Análisis principal ───────────────────────────────────────

def analyze(items: list[dict[str, Any]], top_n: int = 20) -> dict[str, Any]:
    """
    Analiza TODOS los partidos del día en TODOS los mercados.
    Incluye resultado (1/X/2), doble oportunidad, goles (+1.5/+2.5/+3.5) y BTTS.
    Devuelve los mejores top_n picks ordenados por confianza.
    """
    today_items = filter_today(items)
    enriched: list[dict] = []

    for it in today_items:
        pick = pick_type(it.get("pronostico", ""))

        # Saltar empate puro y desconocidos sin datos
        if pick == "X":
            continue

        p1   = int(it.get("prob_1",   0) or 0)
        p2   = int(it.get("prob_2",   0) or 0)
        px   = int(it.get("prob_x",   0) or 0)
        o15  = int(it.get("prob_over_15", 0) or 0)
        o25  = int(it.get("prob_over_25", 0) or 0)
        o35  = int(it.get("prob_over_35", 0) or 0)
        bty  = int(it.get("prob_btts_yes", 0) or 0)

        elo_diff = it.get("elo_diff")
        is_local = pick in ("1", "1X")
        bp_prob  = float(it.get("betplay_impl_prob_1", 0) or 0) if is_local else \
                   float(it.get("betplay_impl_prob_2", 0) or 0)

        # ── Picks de resultado ──
        if pick in ("1", "2", "1X", "X2", "12"):
            if pick in ("1", "1X"):
                favorito   = it.get("equipo_local") or "Local"
                prob_win   = p1
                prob_rival = p2
            elif pick in ("2", "X2"):
                favorito   = it.get("equipo_visitante") or "Visitante"
                prob_win   = p2
                prob_rival = p1
            else:  # 12
                if p1 >= p2:
                    favorito, prob_win, prob_rival = it.get("equipo_local") or "Local", p1, p2
                else:
                    favorito, prob_win, prob_rival = it.get("equipo_visitante") or "Visitante", p2, p1

            if prob_win == 0:
                continue

            conf   = _score_resultado(prob_win, prob_rival, pick, elo_diff, bp_prob)
            margin = prob_win - prob_rival
            value  = _is_value_bet(conf, prob_win, margin)

        # ── Picks de goles ──
        elif pick in ("OVER_15", "OVER_25", "OVER_35"):
            prob_map  = {"OVER_15": o15, "OVER_25": o25, "OVER_35": o35}
            label_map = {"OVER_15": "+1.5 goles", "OVER_25": "+2.5 goles", "OVER_35": "+3.5 goles"}
            prob_win  = prob_map[pick]
            if prob_win < 30:
                continue
            favorito   = f"{it.get('equipos','')} — {label_map[pick]}"
            prob_rival = 100 - prob_win
            margin     = prob_win - prob_rival
            conf       = _score_goles(prob_win, pick)
            value      = conf >= 60 and prob_win >= 70

        # ── Picks BTTS ──
        elif pick == "BTTS":
            if bty < 30:
                continue
            favorito   = f"{it.get('equipos','')} — Ambos anotan"
            prob_win   = bty
            prob_rival = 100 - bty
            margin     = prob_win - prob_rival
            conf       = _score_btts(bty)
            value      = conf >= 60 and bty >= 65

        # ── UNK: intentar con la prob más alta ──
        elif pick == "UNK":
            best = max((p1, "1", it.get("equipo_local") or "Local", p2),
                       (p2, "2", it.get("equipo_visitante") or "Visitante", p1),
                       key=lambda x: x[0])
            prob_win, pick, favorito, prob_rival = best
            if prob_win < 40:
                continue
            margin = prob_win - prob_rival
            conf   = _score_resultado(int(prob_win), int(prob_rival), str(pick), elo_diff, bp_prob)
            value  = _is_value_bet(conf, int(prob_win), int(margin))
        else:
            continue

        tier = _tier(conf)

        e = dict(it)
        e.update({
            "_favorito":    favorito,
            "_prob_win":    int(prob_win),
            "_prob_rival":  int(prob_rival),
            "_prob_empate": px,
            "_pick":        pick,
            "_confidence":  conf,
            "_tier":        tier,
            "_value":       value,
            "_margin":      int(prob_win) - int(prob_rival),
        })
        enriched.append(e)

    enriched.sort(key=lambda x: (x["_confidence"], x["_prob_win"]), reverse=True)
    top = enriched[:top_n]

    total         = len(today_items)
    elite_count   = sum(1 for e in enriched if e["_tier"] == "ÉLITE")
    alta_count    = sum(1 for e in enriched if e["_tier"] == "ALTA")
    value_count   = sum(1 for e in enriched if e["_value"])
    avg_conf      = round(sum(e["_confidence"] for e in enriched) / max(len(enriched),1), 1)
    competiciones = len({e["competicion"] for e in today_items if e.get("competicion")})

    return {
        "top": top,
        "stats": {
            "total_partidos":  total,
            "analizados":      len(enriched),
            "elite":           elite_count,
            "alta":            alta_count,
            "value_bets":      value_count,
            "avg_confidence":  avg_conf,
            "competiciones":   competiciones,
            "fecha":           datetime.now().strftime("%d %b %Y"),
            "hora_generacion": datetime.now().strftime("%H:%M:%S"),
        },
        "all": enriched,
    }