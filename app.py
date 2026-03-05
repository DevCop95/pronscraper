"""
app.py — Punto de entrada.
"""

import json
import csv
import sys
from pathlib import Path

from src.scraper         import fetch_html, ALLOWED_URL
from src.parser_logic    import parse_predictions, to_rows
from src.analyzer        import analyze
from src.html_builder    import build as build_html
from src.betplay_fetcher import enrich_with_betplay
from src.stats_enricher  import enrich_with_stats

OUT_DIR       = Path("outputs")
INDEX_HTML    = Path("index.html")
TOP_N         = 20
CREATOR_NAME  = "Yared Henriquez"
CREATOR_IMAGE = "creador.png"
FAVICON       = "favicon.ico"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Descarga
    print("⬇  Descargando predicciones...")
    try:
        html_text = fetch_html(ALLOWED_URL)
    except Exception as ex:
        print(f"✗  Error al descargar: {ex}", file=sys.stderr)
        sys.exit(1)

    # 2. Parseo
    print("🔍 Parseando HTML...")
    items = parse_predictions(html_text, source=ALLOWED_URL)

    if not items:
        print("✗  No se encontraron partidos.", file=sys.stderr)
        sys.exit(1)

    # DEBUG: muestra los primeros 3 con sus probabilidades
    print(f"\n   [DEBUG] {len(items)} partidos. Primeros 3:")
    for it in items[:3]:
        print(f"   {it['equipos']}")
        print(f"     prob_1={it['prob_1']}  prob_x={it['prob_x']}  prob_2={it['prob_2']}")
    print()

    # 3. Enriquecer con BetPlay
    print("🏦 Enriqueciendo con BetPlay...")
    items = enrich_with_betplay(items)

    # 4. Enriquecer con estadísticas históricas (Club Elo + FBref)
    print("📈 Cargando estadísticas históricas...")
    items = enrich_with_stats(items)

    # 5. Guardar JSON y CSV crudos
    (OUT_DIR / "predicciones.json").write_text(
        json.dumps(items, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    rows, cols = to_rows(items)
    with (OUT_DIR / "predicciones.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)

    # 6. Análisis y ranking
    print("📊 Analizando...")
    result = analyze(items, top_n=TOP_N)
    top    = result["top"]
    stats  = result["stats"]

    # 7. Guardar análisis
    (OUT_DIR / "analisis.json").write_text(
        json.dumps({"stats": stats, "top": [
            {k: v for k, v in r.items()
             if not k.startswith("_") or k in (
                 "_favorito", "_prob_win", "_confidence",
                 "_tier", "_value", "_pick", "_margin"
             )}
            for r in top
        ]}, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    # 8. Generar dashboard
    print("🎨 Generando dashboard...")
    build_html(
        top=top,
        stats=stats,
        output_path=str(INDEX_HTML),
        creator_name=CREATOR_NAME,
        creator_image=CREATOR_IMAGE,
        favicon=FAVICON,
    )

    print()
    print("─" * 50)
    print(f"✅  {len(items)} partidos extraídos")
    print(f"✅  {stats['total_partidos']} del día  |  {stats['elite']} Élite  |  {stats['alta']} Alta")
    print(f"✅  {stats['value_bets']} value bets  |  conf. prom. {stats['avg_confidence']}%")
    print("─" * 50)
    print(f"🌐  {INDEX_HTML}  ← abrir en el navegador")
    print()


if __name__ == "__main__":
    main()