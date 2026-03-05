"""
analyzer.py — Análisis riguroso de predicciones de fútbol.

Lógica:
  1. Filtrar partidos del día actual.
  2. Detectar tipo de pronóstico: 1 / 2 / X / 1X / X2 / 12 / UNK.
  3. Calcular 'probabilidad de victoria' solo con prob_1 y prob_2.
  4. Calcular 'confianza' (confidence score 0-100) ponderando:
       - Probabilidad de victoria (peso 60%)
       - Ventaja sobre el rival (margen local vs visitante, peso 20%)
       - Claridad del pronóstico (si es 1X/X2 reduce confianza, peso 20%)
  5. Clasificar en tier:
       ÉLITE  → confianza >= 80
       ALTA   → confianza >= 65
       MEDIA  → confianza >= 50
       BAJA   → el resto (estos se excluyen del Top 20)
  6. Detectar "valor" (value bet): cuando el pronóstico coincide con
     la mayor probabilidad Y el margen es >= 20 puntos.
"""

import re
from datetime import datetime
from typing import Any


# ──────────────────────────────────────────────
# Clasificación del pronóstico
# ──────────────────────────────────────────────

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


# ──────────────────────────────────────────────
# Filtro temporal
# ──────────────────────────────────────────────

def filter_today(items: list[dict]) -> list[dict]:
    """
    Si 'hora' tiene fecha dd/mm filtra por hoy.
    Si hora está vacía o sin fecha → asume que es de hoy (comportamiento del sitio).
    """
    today = datetime.now().strftime("%d/%m")
    out = []
    for it in items:
        h = (it.get("hora") or "").strip()
        # Sin hora → asumir que es de hoy
        if not h:
            out.append(it)
            continue
        m = re.search(r"\b(\d{1,2}/\d{1,2})\b", h)
        if m:
            if m.group(1) == today:
                out.append(it)
        else:
            out.append(it)
    return out


# ──────────────────────────────────────────────
# Cálculo de confianza y metadata
# ──────────────────────────────────────────────

def _confidence(prob_win: int, prob_rival: int, pick: str,
                elo_diff: float | None = None,
                betplay_impl_prob: float = 0) -> int:
    margin = max(0, prob_win - prob_rival)
    clarity_map = {"1": 1.0, "2": 1.0, "1X": 0.70, "X2": 0.70, "12": 0.60, "UNK": 0.40}
    clarity = clarity_map.get(pick, 0.50)
    score = (prob_win * 0.50) + (min(margin, 50) * 0.30) + (clarity * 15)

    if elo_diff is not None:  # ← guard explícito antes de operar
        elo_bonus = min(10, abs(elo_diff) / 30)
        if (elo_diff > 0 and pick in ("1", "1X", "12")) or \
           (elo_diff < 0 and pick in ("2", "X2", "12")):
            score += elo_bonus
        else:
            score -= elo_bonus * 0.5

    if betplay_impl_prob > 0:
        diff = abs(prob_win - betplay_impl_prob)
        if diff <= 10:    score += 10
        elif diff <= 20:  score += 5
        else:             score -= 5

    return min(100, max(0, round(score)))


def _tier(confidence: int) -> str:
    if confidence >= 80:
        return "ÉLITE"
    if confidence >= 65:
        return "ALTA"
    if confidence >= 50:
        return "MEDIA"
    return "BAJA"


def _is_value_bet(prob_win: int, prob_rival: int) -> bool:
    """
    'Value' cuando la probabilidad de ganar supera al rival por ≥ 20 puntos
    y está por encima del 60%.
    """
    return prob_win >= 60 and (prob_win - prob_rival) >= 20


# ──────────────────────────────────────────────
# Función principal de análisis
# ──────────────────────────────────────────────

def analyze(items: list[dict[str, Any]], top_n: int = 20) -> dict[str, Any]:
    """
    Recibe la lista completa de predicciones (todas las del día).
    Devuelve un dict con:
      - 'top'       : lista de los mejores N picks enriquecidos
      - 'stats'     : métricas globales del día
    """
    today_items = filter_today(items)

    enriched: list[dict] = []
    for it in today_items:
        pick = pick_type(it.get("pronostico", ""))

        # Pronóstico de empate puro → excluir (no es un equipo ganador)
        if pick == "X":
            continue

        p1 = int(it.get("prob_1", 0) or 0)
        p2 = int(it.get("prob_2", 0) or 0)

        # Determinar favorito y probabilidad de victoria
        favorito = ""
        prob_win = 0
        prob_rival = 0

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

        # Descartar si no hay datos de probabilidad
        if prob_win == 0:
            continue

        confidence = _confidence(prob_win, prob_rival, pick)
        tier = _tier(confidence)
        value = _is_value_bet(prob_win, prob_rival)

        e = dict(it)
        e.update(
            {
                "_favorito": favorito,
                "_prob_win": prob_win,
                "_prob_rival": prob_rival,
                "_prob_empate": int(it.get("prob_x", 0) or 0),
                "_pick": pick,
                "_confidence": confidence,
                "_tier": tier,
                "_value": value,
                "_margin": prob_win - prob_rival,
            }
        )
        enriched.append(e)

    # Ordenar: primero por confianza, luego por prob_win
    enriched.sort(key=lambda x: (x["_confidence"], x["_prob_win"]), reverse=True)

    top = enriched[:top_n]

    # ── Estadísticas del día ──
    total = len(today_items)
    elite_count = sum(1 for e in enriched if e["_tier"] == "ÉLITE")
    alta_count = sum(1 for e in enriched if e["_tier"] == "ALTA")
    value_count = sum(1 for e in enriched if e["_value"])
    avg_conf = round(sum(e["_confidence"] for e in enriched) / len(enriched), 1) if enriched else 0
    competiciones = len({e["competicion"] for e in today_items if e.get("competicion")})

    stats = {
        "total_partidos": total,
        "analizados": len(enriched),
        "elite": elite_count,
        "alta": alta_count,
        "value_bets": value_count,
        "avg_confidence": avg_conf,
        "competiciones": competiciones,
        "fecha": datetime.now().strftime("%d %b %Y"),
        "hora_generacion": datetime.now().strftime("%H:%M:%S"),
    }

    return {"top": top, "stats": stats, "all": enriched}
