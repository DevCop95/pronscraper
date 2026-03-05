"""
parser_logic.py
La hora en pronosticosfutbol365.com está en un elemento HERMANO
del div.match (no dentro). Estrategia:
  1. Buscar .time dentro del match
  2. Si no, buscar en el hermano anterior
  3. Si no, buscar en el padre
  4. Si no, regex HH:MM en todo el texto del bloque
Convierte CET (UTC+1) → Colombia (UTC-5) = -6h
"""

import re
from bs4 import BeautifulSoup, NavigableString, Tag
from typing import Any
from datetime import datetime, timezone

SITE_UTC_OFFSET = +1   # CET
COL_UTC_OFFSET  = -5   # America/Bogota
HOUR_DIFF       = COL_UTC_OFFSET - SITE_UTC_OFFSET   # -6


def _to_col(hora_str: str) -> str:
    """'HH:MM' CET → 'HH:MM' Colombia."""
    m = re.match(r"^(\d{1,2}):(\d{2})$", hora_str.strip())
    if not m:
        return hora_str
    total = int(m.group(1)) * 60 + int(m.group(2)) + HOUR_DIFF * 60
    total = total % (24 * 60)
    if total < 0:
        total += 24 * 60
    return f"{total // 60:02d}:{total % 60:02d}"


def _txt(node: Any) -> str:
    return node.get_text(" ", strip=True) if node else ""


def _find_time_in(node: Tag) -> str:
    """Busca patrón HH:MM en cualquier elemento dentro de node."""
    # Selectores específicos primero
    for sel in [".time", ".hora", ".match-time", ".kickoff",
                "[class*='time']", "[class*='hour']", "[class*='hora']"]:
        el = node.select_one(sel)
        if el:
            raw = re.sub(r"\s+", "", _txt(el))
            m = re.match(r"(\d{1,2}:\d{2})", raw)
            if m:
                return m.group(1)

    # Regex sobre todo el texto del nodo
    full = _txt(node)
    m = re.search(r"\b(\d{1,2}:\d{2})\b", full)
    if m:
        return m.group(1)
    return ""


def _extract_hora(match: Tag) -> str:
    """
    La hora está en div.date, ofuscada con un span display:none:
      <div class="date">
        22
        <span style="display:none">:</span>
        :00
      </div>
    BeautifulSoup lee "22 : :00" → hay que eliminar el span y limpiar.
    Resultado: "22:00" CET → "16:00 COL"
    """
    import copy
    date_div = match.select_one(".date")
    if date_div:
        d = copy.copy(date_div)
        for hidden in d.find_all("span"):
            style = (hidden.get("style") or "").replace(" ", "")
            if "display:none" in style:
                hidden.decompose()
        raw = re.sub(r"\s+", "", d.get_text())  # "22:00" o "22::00"
        raw = re.sub(r":+", ":", raw)            # "22::00" → "22:00"
        m = re.match(r"(\d{1,2}:\d{2})", raw)
        if m:
            return f"{_to_col(m.group(1))} COL"
    return ""


def _scraped_at_to_col(scraped_at: str) -> str:
    """Convierte scraped_at UTC ISO → hora Colombia (UTC-5)."""
    try:
        from datetime import timedelta
        dt = datetime.fromisoformat(scraped_at)
        col = dt.astimezone(timezone(timedelta(hours=-5)))
        return f"{col.strftime('%H:%M')} COL"
    except Exception:
        return ""


def _to_int(text: str) -> int | None:
    t = text.strip()
    if re.fullmatch(r"\d{1,3}", t):
        return int(t)
    return None


def _coefrow_values(coefrow: Tag) -> list[int]:
    values: list[int] = []
    for child in coefrow.children:
        if not isinstance(child, Tag):
            continue
        classes = child.get("class", [])
        if "ownheader" in classes:
            continue
        if "coefbox" in classes:
            value_node = child.find(class_=re.compile(r"\bvalue\b"))
            raw = _txt(value_node) if value_node else _txt(child)
            n = _to_int(raw)
            if n is not None:
                values.append(n)
    return values


_LABELS = [
    "prob_1", "prob_x", "prob_2",
    "prob_ht1", "prob_htx", "prob_ht2",
    "prob_over_15", "prob_over_25", "prob_over_35",
    "prob_btts_yes", "prob_btts_no",
]


def _metrics_from_block(block: Tag) -> dict[str, int]:
    metrics = {k: 0 for k in _LABELS}
    inforow = block.select_one(".inforow")
    if not inforow:
        return metrics
    for cr in inforow.select(".coefrow"):
        v = _coefrow_values(cr)
        if len(v) >= 3:
            for i, val in enumerate(v[:len(_LABELS)]):
                metrics[_LABELS[i]] = val
            return metrics
    return metrics


def parse_predictions(html: str, source: str) -> list[dict[str, Any]]:
    soup    = BeautifulSoup(html, "html.parser")
    now_iso = datetime.now(timezone.utc).isoformat()
    results: list[dict[str, Any]] = []

    # DEBUG: mostrar clases únicas para encontrar el elemento de hora
    all_classes: set[str] = set()
    for el in soup.select("[class]")[:200]:
        for c in (el.get("class") or []):
            all_classes.add(c)
    time_like = [c for c in all_classes if any(
        kw in c.lower() for kw in ["time","hora","hour","kick","match"]
    )]
    if time_like:
        print(f"   [DEBUG] Clases relacionadas con hora encontradas: {time_like}")

    for comp in soup.select("div.competition"):
        comp_name = _txt(comp.select_one(".name"))
        matches   = comp.select("div.match") or comp.select("div.cmatch")
        if not matches:
            continue

        for match in matches:
            hora = _extract_hora(match)

            pred_node = (
                match.select_one(".tip .value .type3") or
                match.select_one(".tip .type3") or
                match.select_one(".tip .value") or
                match.select_one(".value .type3") or
                match.select_one(".type3")
            )
            pronostico = _txt(pred_node)

            teams_raw = _txt(match.select_one(".teams"))
            teams_txt = re.sub(r"^\d{4}-\d{2}-\d{2}\s+[\d\s:]+", "", teams_raw).strip()
            teams_txt = re.sub(r"\s*[▸►→▶]\s*", " - ", teams_txt)
            teams_txt = re.sub(r"\s{2,}", " ", teams_txt).strip()

            equipo_local = equipo_visitante = ""
            for sep in (" - ", " – ", " vs ", " VS "):
                if sep in teams_txt:
                    parts = [p.strip() for p in teams_txt.split(sep, 1)]
                    equipo_local, equipo_visitante = (parts + [""])[:2]
                    break
            if not equipo_local:
                equipo_local = teams_txt

            metrics = _metrics_from_block(match)
            if metrics["prob_1"] == 0 and metrics["prob_2"] == 0:
                metrics = _metrics_from_block(comp)

            if not (pronostico or teams_txt):
                continue

            # Fallback: si HTML no tiene hora, convertir scraped_at UTC → Colombia
            if not hora:
                hora = _scraped_at_to_col(now_iso)

            results.append({
                "competicion":      comp_name,
                "hora":             hora,
                "pronostico":       pronostico,
                "equipos":          teams_txt,
                "equipo_local":     equipo_local,
                "equipo_visitante": equipo_visitante,
                **{k: metrics[k] for k in _LABELS},
                "origen":           source,
                "scraped_at":       now_iso,
            })

    # Debug resumen
    con_hora = sum(1 for r in results if r["hora"])
    print(f"   [DEBUG] {len(results)} partidos | {con_hora} con hora | {len(results)-con_hora} sin hora")
    for r in results[:3]:
        print(f"   • {r['hora'] or 'SIN HORA':14s} | {r['equipos'][:35]:35s} | 1={r['prob_1']}")

    return results


def to_rows(items: list[dict[str, Any]]) -> tuple[list[dict], list[str]]:
    columns = [
        "competicion", "hora", "pronostico",
        "equipo_local", "equipo_visitante", "equipos",
        "prob_1", "prob_x", "prob_2",
        "prob_ht1", "prob_htx", "prob_ht2",
        "prob_over_15", "prob_over_25", "prob_over_35",
        "prob_btts_yes", "prob_btts_no",
        "origen", "scraped_at",
    ]
    return [{k: it.get(k, "") for k in columns} for it in items], columns