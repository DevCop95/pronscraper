"""
parser_logic.py
DOM real: .competition > .body > .match > .inforow > .coefrow
  Dentro de .coefrow hay .ownheader (etiquetas) + N .coefbox (valores)
  Los .coefbox pueden contener texto directo o un div hijo con clase rNN.
  Estrategia: leer el coefrow entero como texto y extraer números en orden.
"""

import re
from bs4 import BeautifulSoup, Tag
from typing import Any
from datetime import datetime, timezone


def _txt(node) -> str:
    return node.get_text(" ", strip=True) if node else ""


def _numbers_from_coefrow(coefrow: Tag) -> list[int]:
    """
    Extrae los valores numéricos del coefrow en orden DOM,
    ignorando el bloque ownheader (etiquetas) y descartando
    números que claramente son labels (< 10).
    """
    values: list[int] = []
    for child in coefrow.children:
        if not isinstance(child, Tag):
            continue
        classes = child.get("class", []) if child.get("class") else []
        # Saltar el bloque de etiquetas
        if "ownheader" in classes:
            continue
        if "coefbox" in classes:
            # Extraer TODOS los dígitos del bloque completo
            raw = child.get_text(" ", strip=True)
            # Buscar el primer número entero en el texto
            m = re.search(r"\b(\d{1,3})\b", raw)
            if m:
                n = int(m.group(1))
                # Los valores reales de % van de 10 a 100
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

    # Hay uno o más .coefrow; probar cada uno hasta tener ≥3 valores
    for coefrow in inforow.select(".coefrow"):
        vals = _numbers_from_coefrow(coefrow)
        if len(vals) >= 3:
            for i, v in enumerate(vals[:len(_LABELS)]):
                metrics[_LABELS[i]] = v
            return metrics

    # Fallback: leer todos los números del inforow como texto bruto
    raw_text = inforow.get_text(" ")
    all_nums = [int(m) for m in re.findall(r"\b(\d{2,3})\b", raw_text) if 10 <= int(m) <= 100]
    for i, v in enumerate(all_nums[:len(_LABELS)]):
        metrics[_LABELS[i]] = v

    return metrics


def parse_predictions(html: str, source: str) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    now_iso = datetime.now(timezone.utc).isoformat()
    results: list[dict[str, Any]] = []

    for comp in soup.select("div.competition"):
        comp_name = _txt(comp.select_one(".name"))
        # El sitio usa div.match (confirmado en DevTools)
        matches = comp.select("div.match")
        if not matches:
            matches = comp.select("div.cmatch")
        if not matches:
            continue

        for match in matches:
            # ── Hora ──
            hora_node = match.select_one(".time")
            hora = ""
            if hora_node:
                hora = re.sub(r"\s+", " ", _txt(hora_node)).strip()
            
            # ── Pronóstico ──
            pred_node = (
                match.select_one(".tip .type3") or
                match.select_one(".tip .value") or
                match.select_one(".type3")
            )
            pronostico = _txt(pred_node)

            # ── Equipos ── (el .teams puede incluir hora y caracteres raros)
            teams_raw = _txt(match.select_one(".teams"))
            
            # Limpiar: quitar fecha/hora al inicio (ej: "2026-03-05 21 : 30 ▸ ")
            teams_txt = re.sub(r"^\d{4}-\d{2}-\d{2}\s+[\d\s:]+", "", teams_raw).strip()
            # Limpiar separadores raros (▸, ►, →, etc.) que no sean " - " o " – "
            teams_txt = re.sub(r"\s*[▸►→▶]\s*", " - ", teams_txt).strip()
            # Quitar dobles espacios
            teams_txt = re.sub(r"\s{2,}", " ", teams_txt).strip()
            
            # Si la hora salió vacía, intentar extraerla del texto crudo del bloque
            if not hora:
                m_hora = re.search(r"\b(\d{1,2}\s*:\s*\d{2})\b", teams_raw)
                if m_hora:
                    hora = re.sub(r"\s+", "", m_hora.group(1))

            equipo_local = equipo_visitante = ""
            for sep in (" - ", " – ", " vs "):
                if sep in teams_txt:
                    parts = [p.strip() for p in teams_txt.split(sep, 1)]
                    equipo_local = parts[0]
                    equipo_visitante = parts[1] if len(parts) > 1 else ""
                    break
            if not equipo_local:
                equipo_local = teams_txt

            metrics = _get_metrics(match)

            if not teams_txt:
                continue

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