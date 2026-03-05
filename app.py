"""
app.py — Servidor Flask para Render.
- Se mantiene vivo (no termina como un script normal)
- Refresca datos cada 3 horas automáticamente
- Sirve index.html en la raíz
- Endpoint /refresh para actualizar manualmente
- Endpoint /status para healthcheck
"""

import json
import csv
import sys
import os
import threading
from pathlib import Path
from datetime import datetime

from flask import Flask, send_file, jsonify, Response

from src.scraper      import fetch_html, ALLOWED_URL
from src.parser_logic import parse_predictions, to_rows
from src.analyzer     import analyze
from src.html_builder import build as build_html
from src.betplay_fetcher import enrich_with_betplay
from src.stats_enricher  import enrich_with_stats

# ── Config ───────────────────────────────────────────────────
OUT_DIR       = Path("outputs")
INDEX_HTML    = Path("index.html")
TOP_N         = 20
CREATOR_NAME  = "Yared Henriquez"
CREATOR_IMAGE = "creador.png"
FAVICON       = "favicon.ico"
REFRESH_HOURS = 3   # refrescar cada N horas

# ── Flask app ─────────────────────────────────────────────────
app = Flask(__name__)

# Estado compartido
state = {
    "last_update":  None,
    "total":        0,
    "elite":        0,
    "alta":         0,
    "value_bets":   0,
    "avg_conf":     0,
    "running":      False,
    "error":        None,
}
_lock = threading.Lock()


# ── Lógica principal ──────────────────────────────────────────

def run_pipeline() -> bool:
    """Ejecuta scrape → parse → enrich → analyze → HTML. Devuelve True si OK."""
    with _lock:
        if state["running"]:
            print("⚠ Pipeline ya en ejecución, saltando.")
            return False
        state["running"] = True
        state["error"]   = None

    try:
        OUT_DIR.mkdir(parents=True, exist_ok=True)

        print(f"\n{'─'*50}")
        print(f"🔄 [{datetime.now().strftime('%H:%M:%S')}] Iniciando pipeline...")

        # 1. Scrape
        print("⬇  Descargando predicciones...")
        html_text = fetch_html(ALLOWED_URL)

        # 2. Parse
        print("🔍 Parseando HTML...")
        items = parse_predictions(html_text, source=ALLOWED_URL)
        if not items:
            raise RuntimeError("No se encontraron partidos")

        print(f"   ✓ {len(items)} partidos extraídos")
        print(f"   Primeros 3 debug:")
        for it in items[:3]:
            print(f"   • {it['equipos']} | 1={it['prob_1']} X={it['prob_x']} 2={it['prob_2']}")

        # 3. Enriquecer
        print("🏦 BetPlay...")
        items = enrich_with_betplay(items)

        print("📈 Club Elo...")
        items = enrich_with_stats(items)

        # 4. Guardar raw
        (OUT_DIR / "predicciones.json").write_text(
            json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        rows, cols = to_rows(items)
        with (OUT_DIR / "predicciones.csv").open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader(); w.writerows(rows)

        # 5. Analizar TODOS los mercados
        print("📊 Analizando todos los mercados...")
        result = analyze(items, top_n=TOP_N)
        top    = result["top"]
        stats  = result["stats"]

        print(f"   ✓ {stats['analizados']} picks válidos | "
              f"{stats['elite']} Élite | {stats['alta']} Alta | "
              f"{stats['value_bets']} Value | conf prom {stats['avg_confidence']}%")

        # 6. Guardar análisis
        (OUT_DIR / "analisis.json").write_text(
            json.dumps({"stats": stats, "top": [
                {k: v for k, v in r.items()
                 if not k.startswith("_") or k in (
                     "_favorito","_prob_win","_confidence",
                     "_tier","_value","_pick","_margin"
                 )}
                for r in top
            ]}, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

        # 7. Generar HTML
        print("🎨 Generando dashboard...")
        build_html(
            top=top, stats=stats,
            output_path=str(INDEX_HTML),
            creator_name=CREATOR_NAME,
            creator_image=CREATOR_IMAGE,
            favicon=FAVICON,
        )

        # Actualizar estado
        with _lock:
            state.update({
                "last_update": datetime.now().isoformat(),
                "total":       stats["total_partidos"],
                "elite":       stats["elite"],
                "alta":        stats["alta"],
                "value_bets":  stats["value_bets"],
                "avg_conf":    stats["avg_confidence"],
            })

        print(f"✅ Pipeline completo — {INDEX_HTML}")
        print(f"{'─'*50}\n")
        return True

    except Exception as ex:
        with _lock:
            state["error"] = str(ex)
        print(f"✗ Error en pipeline: {ex}", file=sys.stderr)
        return False

    finally:
        with _lock:
            state["running"] = False


def background_scheduler():
    """Ejecuta el pipeline cada REFRESH_HOURS horas en background."""
    import time
    while True:
        run_pipeline()
        print(f"💤 Próximo refresco en {REFRESH_HOURS}h")
        time.sleep(REFRESH_HOURS * 3600)


# ── Rutas Flask ───────────────────────────────────────────────

@app.route("/")
def index():
    if INDEX_HTML.exists():
        return send_file(str(INDEX_HTML))
    return Response(
        "<h2>Cargando datos... refresca en 30 segundos</h2>"
        "<p>El pipeline está corriendo por primera vez.</p>"
        '<script>setTimeout(()=>location.reload(),15000)</script>',
        mimetype="text/html"
    )


@app.route("/refresh")
def refresh():
    """Endpoint para forzar un refresco manual."""
    t = threading.Thread(target=run_pipeline, daemon=True)
    t.start()
    return jsonify({
        "status": "started",
        "message": "Pipeline iniciado. Refresca / en ~30 segundos."
    })


@app.route("/status")
def status():
    """Healthcheck y estado del sistema."""
    with _lock:
        s = dict(state)
    s["index_exists"] = INDEX_HTML.exists()
    s["uptime"] = "OK"
    return jsonify(s)


@app.route("/data")
def data():
    """Devuelve el análisis en JSON."""
    f = OUT_DIR / "analisis.json"
    if f.exists():
        return send_file(str(f), mimetype="application/json")
    return jsonify({"error": "No hay datos aún"}), 404


@app.route("/favicon.ico")
def favicon():
    if Path(FAVICON).exists():
        return send_file(FAVICON)
    return Response("", status=204)


# ── Archivos estáticos (imágenes, etc.) ───────────────────────

@app.route("/<path:filename>")
def static_files(filename: str):
    p = Path(filename)
    if p.exists() and p.suffix in (".png", ".jpg", ".ico", ".css", ".js"):
        return send_file(str(p))
    return Response("Not found", status=404)


# ── Entry point ───────────────────────────────────────────────

if __name__ == "__main__":
    # Lanzar pipeline en background thread (no bloquea Flask)
    t = threading.Thread(target=background_scheduler, daemon=True)
    t.start()

    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 Servidor Flask en puerto {port}")
    print(f"   Dashboard: http://localhost:{port}/")
    print(f"   Refrescar: http://localhost:{port}/refresh")
    print(f"   Estado:    http://localhost:{port}/status")

    # Use threaded=True para manejar múltiples requests
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
