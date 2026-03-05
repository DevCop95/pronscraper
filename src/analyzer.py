"""
analyzer.py — Análisis de predicciones con thresholds calibrados.
Thresholds ajustados a la realidad del fútbol (prob_win 45-65% es normal).
  ÉLITE  ≥ 65
  ALTA   ≥ 50
  MEDIA  ≥ 35
  BAJA   < 35
"""

import re
from datetime import datetime
from typing import Any


def pick_type(pronostico: str) -> str:
    p = (pronostico or "").lower().replace(" ", "").replace("—", "").replace("-", "")
    if p.startswith("12"):   return "12"
    if p.startswith("1x"):   return "1X"
    if p.startswith("x2"):   return "X2"
    if p.startswith("1"):    return "1"
    if p.startswith("2"):    return "2"
    if p.startswith("x") or "empate" in p or "draw" in p:
        return "X"
    return "UNK"


def filter_today(items: list[dict]) -> list[dict]:
    """
    Filtra partidos que:
    1. Son del día de hoy (hora Colombia)
    2. Aún NO han comenzado (con 10 min de gracia)
    """
    from datetime import timezone, timedelta
    now_col  = datetime.now(timezone(timedelta(hours=-5)))
    today    = now_col.strftime("%d/%m")
    now_mins = now_col.hour * 60 + now_col.minute - 10  # 10 min de gracia

    out = []
    for it in items:
        h = (it.get("hora") or "").strip()

        # Sin hora → incluir (no sabemos cuándo es)
        if not h:
            out.append(it)
            continue

        # Filtro de fecha si hay dd/mm
        m_date = re.search(r"\b(\d{1,2}/\d{1,2})\b", h)
        if m_date and m_date.group(1) != today:
            continue

        # Filtro de hora: descartar partidos que ya pasaron
        m_time = re.search(r"(\d{1,2}):(\d{2})", h)
        if m_time:
            match_mins = int(m_time.group(1)) * 60 + int(m_time.group(2))
            if match_mins < now_mins:
                continue  # ya pasó

        out.append(it)
    return out


def _confidence(prob_win: int, prob_rival: int, pick: str,
                elo_diff: "float | None" = None,
                betplay_impl_prob: float = 0) -> int:
    """
    Score 0-100 calibrado para fútbol real.
    prob_win típico: 40-65%
    """
    margin = max(0, prob_win - prob_rival)
    clarity_map = {"1": 1.0, "2": 1.0, "1X": 0.75, "X2": 0.75, "12": 0.65, "UNK": 0.45}
    clarity = clarity_map.get(pick, 0.55)

    score = (prob_win * 0.60) + (min(margin, 50) * 0.40) + (clarity * 20)

    # Bonus Elo (±8 pts)
    if elo_diff is not None:
        elo_bonus = min(8, abs(float(elo_diff)) / 40)
        if (elo_diff > 0 and pick in ("1", "1X", "12")) or \
           (elo_diff < 0 and pick in ("2", "X2", "12")):
            score += elo_bonus
        else:
            score -= elo_bonus * 0.5

    # Bonus BetPlay (±8 pts)
    if betplay_impl_prob > 0:
        diff = abs(prob_win - betplay_impl_prob)
        if diff <= 8:    score += 8
        elif diff <= 15: score += 4
        else:            score -= 4

    return min(100, max(0, round(score)))


def _tier(confidence: int) -> str:
    if confidence >= 65: return "ELITE"
    if confidence >= 50: return "ALTA"
    if confidence >= 35: return "MEDIA"
    return "BAJA"


def _is_value_bet(prob_win: int, prob_rival: int) -> bool:
    return prob_win >= 50 and (prob_win - prob_rival) >= 15


def analyze(items: list[dict[str, Any]], top_n: int = 20) -> dict[str, Any]:
    today_items = filter_today(items)
    enriched: list[dict] = []

    for it in today_items:
        pick = pick_type(it.get("pronostico", ""))
        if pick == "X":
            continue

        p1 = int(it.get("prob_1", 0) or 0)
        p2 = int(it.get("prob_2", 0) or 0)

        favorito = prob_win = prob_rival = ""
        if pick == "1":
            favorito, prob_win, prob_rival = it.get("equipo_local") or "Local", p1, p2
        elif pick == "2":
            favorito, prob_win, prob_rival = it.get("equipo_visitante") or "Visitante", p2, p1
        elif pick == "1X":
            favorito, prob_win, prob_rival = it.get("equipo_local") or "Local", p1, p2
        elif pick == "X2":
            favorito, prob_win, prob_rival = it.get("equipo_visitante") or "Visitante", p2, p1
        elif pick in ("12", "UNK"):
            if p1 >= p2:
                favorito, prob_win, prob_rival = it.get("equipo_local") or "Local", p1, p2
            else:
                favorito, prob_win, prob_rival = it.get("equipo_visitante") or "Visitante", p2, p1

        if not prob_win or prob_win == 0:
            continue

        elo_diff = it.get("elo_diff")
        bp_prob  = float(it.get("betplay_impl_prob_1", 0) or 0) if pick in ("1","1X") else \
                   float(it.get("betplay_impl_prob_2", 0) or 0)

        confidence = _confidence(int(prob_win), int(prob_rival), pick, elo_diff, bp_prob)
        tier  = _tier(confidence)
        value = _is_value_bet(int(prob_win), int(prob_rival))

        e = dict(it)
        e.update({
            "_favorito":    favorito,
            "_prob_win":    int(prob_win),
            "_prob_rival":  int(prob_rival),
            "_prob_empate": int(it.get("prob_x", 0) or 0),
            "_pick":        pick,
            "_confidence":  confidence,
            "_tier":        tier,
            "_value":       value,
            "_margin":      int(prob_win) - int(prob_rival),
        })
        enriched.append(e)

    enriched.sort(key=lambda x: (x["_confidence"], x["_prob_win"]), reverse=True)
    top = enriched[:top_n]

    total        = len(today_items)
    elite_count  = sum(1 for e in enriched if e["_tier"] == "ELITE")
    alta_count   = sum(1 for e in enriched if e["_tier"] == "ALTA")
    value_count  = sum(1 for e in enriched if e["_value"])
    avg_conf     = round(sum(e["_confidence"] for e in enriched) / len(enriched), 1) if enriched else 0
    competiciones= len({e["competicion"] for e in today_items if e.get("competicion")})

    stats = {
        "total_partidos":   total,
        "analizados":       len(enriched),
        "elite":            elite_count,
        "alta":             alta_count,
        "value_bets":       value_count,
        "avg_confidence":   avg_conf,
        "competiciones":    competiciones,
        "fecha":            datetime.now().strftime("%d %b %Y"),
        "hora_generacion":  datetime.now().strftime("%H:%M:%S"),
    }

    return {"top": top, "stats": stats, "all": enriched}