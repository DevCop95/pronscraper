"""
parser_logic.py
Convierte horas del sitio (CET, UTC+1) a hora Colombia (UTC-5, -6h).
"""

import re
from bs4 import BeautifulSoup, Tag
from typing import Any
from datetime import datetime, timezone, timedelta


# ── Zona horaria ─────────────────────────────────────────────
# El sitio pronosticosfutbol365.com usa CET (UTC+1)
# Colombia = UTC-5 → diferencia: -6 horas

SITE_UTC_OFFSET  = +1   # CET
COL_UTC_OFFSET   = -5   # America/Bogota
HOUR_DIFF        = COL_UTC_OFFSET - SITE_UTC_OFFSET  # = -6


def _to_colombia_time(hora_str: str) -> str:
    """
    Convierte 'HH:MM' del sitio (CET/UTC+1) a hora Colombia (UTC-5).
    Si falla el parseo, devuelve el original sin modificar.
    Ejemplos:
      '16:10' CET → '10:10' COL
      '00:30' CET → '18:30' COL (día anterior)
    """
    hora_str = hora_str.strip()
    m = re.match(r"^(\d{1,2}):(\d{2})$", hora_str)
    if not m:
        return hora_str  # no es HH:MM puro, devolver tal cual

    h = int(m.group(1))
    mins = int(m.group(2))
    total_mins = h * 60 + mins + HOUR_DIFF * 60

    # Manejar cambio de día
    total_mins = total_mins % (24 * 60)
    if total_mins < 0:
        total_mins += 24 * 60

    new_h   = total_mins // 60
    new_min = total_mins % 60
    return f"{new_h:02d}:{new_min:02d}"


def _txt(node: Any) -> str:
    return node.get_text(" ", strip=True) if node else ""


def _numbers_from_coefrow(coefrow: Tag) -> list[int]:
    values: list[int] = []
    for child in coefrow.children:
        if not isinstance(child, Tag):
            continue
        classes = child.get("class") or []
        if "ownheader" in classes:
            continue
        if "coefbox" in classes:
            raw = child.get_text(" ", strip=True)
            m = re.search(r"\b(\d{1,3})\b", raw)
            if m:
                n = int(m.group(1))
                if 10 <= n <= 100:
                    values.append(n)
    return values


_LABELS = [
    "prob_1", "prob_x", "prob_2",
    "prob_ht1", "prob_htx", "prob_ht2",
    "prob_over_15", "prob_over_25", "prob_over_35",
    "prob_btts_yes", "prob_btts_no",
]


def _get_metrics(block: Tag) -> dict[str, int]:
    metrics = {k: 0 for k in _LABELS}
    inforow = block.select_one(".inforow")
    if not inforow:
        return metrics

    for coefrow in inforow.select(".coefrow"):
        vals = _numbers_from_coefrow(coefrow)
        if len(vals) >= 3:
            for i, v in enumerate(vals[:len(_LABELS)]):
                metrics[_LABELS[i]] = v
            return metrics

    raw = inforow.get_text(" ")
    all_nums = [int(m) for m in re.findall(r"\b(\d{2,3})\b", raw) if 10 <= int(m) <= 100]
    for i, v in enumerate(all_nums[:len(_LABELS)]):
        metrics[_LABELS[i]] = v
    return metrics


def parse_predictions(html: str, source: str) -> list[dict[str, Any]]:
    soup    = BeautifulSoup(html, "html.parser")
    now_iso = datetime.now(timezone.utc).isoformat()
    results: list[dict[str, Any]] = []

    for comp in soup.select("div.competition"):
        comp_name = _txt(comp.select_one(".name"))
        matches   = comp.select("div.match") or comp.select("div.cmatch")
        if not matches:
            continue

        for match in matches:
            # ── Hora: extraer y convertir a Colombia ──
            hora_node = match.select_one(".time")
            hora_raw  = re.sub(r"\s+", "", _txt(hora_node)).strip() if hora_node else ""

            # Si .time no tiene nada, buscar en texto crudo
            if not hora_raw:
                teams_raw_tmp = _txt(match.select_one(".teams") or match)
                m_h = re.search(r"\b(\d{1,2}):(\d{2})\b", teams_raw_tmp)
                if m_h:
                    hora_raw = f"{m_h.group(1)}:{m_h.group(2)}"

            # Convertir a hora Colombia
            hora_col = _to_colombia_time(hora_raw) if hora_raw else ""
            # Guardar ambas por si se necesitan en debug
            hora_display = f"{hora_col} COL" if hora_col else ""

            # ── Pronóstico ──
            pred_node = (
                match.select_one(".tip .type3") or
                match.select_one(".tip .value") or
                match.select_one(".type3")
            )
            pronostico = _txt(pred_node)

            # ── Equipos ──
            teams_raw = _txt(match.select_one(".teams"))
            teams_txt = re.sub(r"^\d{4}-\d{2}-\d{2}\s+[\d\s:]+", "", teams_raw).strip()
            teams_txt = re.sub(r"\s*[▸►→▶]\s*", " - ", teams_txt).strip()
            teams_txt = re.sub(r"\s{2,}", " ", teams_txt).strip()

            equipo_local = equipo_visitante = ""
            for sep in (" - ", " – ", " vs "):
                if sep in teams_txt:
                    parts = [p.strip() for p in teams_txt.split(sep, 1)]
                    equipo_local    = parts[0]
                    equipo_visitante = parts[1] if len(parts) > 1 else ""
                    break
            if not equipo_local:
                equipo_local = teams_txt

            metrics = _get_metrics(match)
            if metrics["prob_1"] == 0 and metrics["prob_2"] == 0:
                metrics = _get_metrics(comp)

            if not teams_txt:
                continue

            results.append({
                "competicion":       comp_name,
                "hora":              hora_display,   # ← "HH:MM COL"
                "hora_original":     hora_raw,       # ← hora CET del sitio (debug)
                "pronostico":        pronostico,
                "equipos":           teams_txt,
                "equipo_local":      equipo_local,
                "equipo_visitante":  equipo_visitante,
                **{k: metrics[k] for k in _LABELS},
                "origen":            source,
                "scraped_at":        now_iso,
            })

    return results


def to_rows(items: list[dict[str, Any]]) -> tuple[list[dict], list[str]]:
    columns = [
        "competicion", "hora", "hora_original", "pronostico",
        "equipo_local", "equipo_visitante", "equipos",
        "prob_1", "prob_x", "prob_2",
        "prob_ht1", "prob_htx", "prob_ht2",
        "prob_over_15", "prob_over_25", "prob_over_35",
        "prob_btts_yes", "prob_btts_no",
        "origen", "scraped_at",
    ]
    return [{k: it.get(k, "") for k in columns} for it in items], columns