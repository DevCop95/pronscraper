"""
app.py — Servidor Flask para Render (gunicorn compatible).
- Thread de background arranca al importar el módulo (funciona con gunicorn)
- Pipeline cada 60 minutos
- /refresh → refresco manual
- /status  → healthcheck para Render
"""

import json, csv, sys, os, threading, time
from pathlib import Path
from datetime import datetime, timezone, timedelta

from flask import Flask, send_file, jsonify, Response

from src.scraper         import fetch_html, ALLOWED_URL
from src.parser_logic    import parse_predictions, to_rows
from src.analyzer        import analyze
from src.html_builder    import build as build_html
from src.betplay_fetcher import enrich_with_betplay
from src.stats_enricher  import enrich_with_stats

# ── Config ────────────────────────────────────────────────────────────────────
OUT_DIR       = Path("outputs")
INDEX_HTML    = Path("index.html")
TOP_N         = 20
CREATOR_NAME  = "DevOpsHB"
CREATOR_IMAGE = "creador.png"
FAVICON       = "favicon.ico"
REFRESH_MINS  = 60

# ── Estado compartido ─────────────────────────────────────────────────────────
app   = Flask(__name__)
_lock = threading.Lock()
_state = {
    "last_update":  None,
    "next_update":  None,
    "running":      False,
    "error":        None,
    "stats":        {},
    "run_count":    0,
}


def _col_now() -> datetime:
    return datetime.now(timezone(timedelta(hours=-5)))

def _col_time() -> str:
    return _col_now().strftime("%H:%M")

def _col_ts() -> str:
    return _col_now().strftime("%H:%M COL · %d/%m/%Y")


# ── Pipeline principal ────────────────────────────────────────────────────────

def run_pipeline() -> bool:
    with _lock:
        if _state["running"]:
            print("⚠ Pipeline ya en ejecución, ignorando llamada")
            return False
        _state["running"] = True
        _state["error"]   = None

    try:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        run_n = _state["run_count"] + 1
        print(f"\n{'─'*55}")
        print(f"🔄 Pipeline #{run_n} — {_col_ts()}")

        # 1. Scrape
        print("⬇  Descargando predicciones...")
        html_text = fetch_html(ALLOWED_URL)

        # 2. Parse
        print("🔍 Parseando HTML...")
        items = parse_predictions(html_text, source=ALLOWED_URL)
        if not items:
            raise RuntimeError("No se encontraron partidos en el HTML")
        print(f"   ✓ {len(items)} partidos parseados")

        # 3. Enriquecer BetPlay
        print("🏦 Consultando BetPlay...")
        items = enrich_with_betplay(items)

        # 4. Enriquecer ClubElo
        print("📈 Cargando ClubElo...")
        items = enrich_with_stats(items)

        # 5. Guardar JSON y CSV crudos
        (OUT_DIR / "predicciones.json").write_text(
            json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        rows, cols = to_rows(items)
        with (OUT_DIR / "predicciones.csv").open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader(); w.writerows(rows)

        # 6. Analizar
        print("📊 Analizando picks...")
        result     = analyze(items, top_n=TOP_N)
        top        = result["top"]
        stats_data = result["stats"]
        print(f"   ✓ {stats_data['total_partidos']} partidos hoy | "
              f"{stats_data['elite']} ELITE | {stats_data['alta']} Alta | "
              f"{stats_data['value_bets']} Value | {stats_data['avg_confidence']}% conf")

        # 7. Guardar análisis JSON
        (OUT_DIR / "analisis.json").write_text(
            json.dumps({
                "stats": stats_data,
                "top": [
                    {k: v for k, v in r.items()
                     if not k.startswith("_") or k in
                     ("_favorito","_prob_win","_prob_rival","_confidence",
                      "_tier","_value","_pick","_margin")}
                    for r in top
                ],
                "generated_at": _col_ts(),
            }, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

        # 8. Generar HTML
        print("🎨 Generando dashboard...")
        build_html(
            top=top, stats=stats_data,
            output_path=str(INDEX_HTML),
            creator_name=CREATOR_NAME,
            creator_image=CREATOR_IMAGE,
            favicon=FAVICON,
        )

        with _lock:
            _state["last_update"] = _col_ts()
            _state["next_update"] = f"~{REFRESH_MINS} min"
            _state["stats"]       = stats_data
            _state["run_count"]   = run_n

        print(f"✅ Listo — próxima actualización en {REFRESH_MINS} min")
        print(f"{'─'*55}\n")
        return True

    except Exception as ex:
        import traceback
        with _lock:
            _state["error"] = str(ex)
        print(f"✗ Error pipeline: {ex}", file=sys.stderr)
        traceback.print_exc()
        return False

    finally:
        with _lock:
            _state["running"] = False


# ── Background loop ───────────────────────────────────────────────────────────
# CRÍTICO: se define AQUÍ (nivel de módulo) para que gunicorn lo arranque
# al importar app.py. Si estuviera dentro de if __name__=="__main__"
# gunicorn nunca lo ejecutaría y no habría auto-refresh.

def _background_loop():
    time.sleep(3)   # esperar que Flask esté listo
    while True:
        run_pipeline()
        print(f"💤 Durmiendo {REFRESH_MINS} min hasta próxima actualización...")
        time.sleep(REFRESH_MINS * 60)


_bg_thread = threading.Thread(target=_background_loop, daemon=True, name="pipeline-loop")
_bg_thread.start()


# ── Rutas Flask ───────────────────────────────────────────────────────────────

@app.route("/")
def index():
    if INDEX_HTML.exists():
        return send_file(str(INDEX_HTML))
    return Response("""
    <!DOCTYPE html>
    <html lang="es">
    <head><meta charset="UTF-8"><title>Cargando análisis...</title>
    <meta http-equiv="refresh" content="15">
    <style>
      body{margin:0;display:flex;align-items:center;justify-content:center;
           min-height:100vh;background:#0f0f1a;font-family:sans-serif;color:#fff}
      .box{text-align:center;padding:40px}
      .spinner{width:48px;height:48px;border:4px solid #333;
               border-top-color:#B8960C;border-radius:50%;
               animation:spin 1s linear infinite;margin:0 auto 20px}
      @keyframes spin{to{transform:rotate(360deg)}}
      h2{color:#B8960C;margin-bottom:8px}
      p{color:#aaa;font-size:14px}
    </style></head>
    <body><div class="box">
      <div class="spinner"></div>
      <h2>Preparando el análisis...</h2>
      <p>Primera ejecución en curso. La página se recargará automáticamente.</p>
      <p style="font-size:12px;color:#555">DevOpsHB · SportAnalysis</p>
    </div></body></html>
    """, mimetype="text/html")


@app.route("/refresh")
def refresh():
    if _state["running"]:
        return jsonify({"status": "running", "message": "Pipeline ya en curso, espera..."})
    t = threading.Thread(target=run_pipeline, daemon=True)
    t.start()
    return jsonify({"status": "started", "message": "Pipeline iniciado. Refresca en ~45s"})


@app.route("/status")
def status():
    with _lock:
        s = dict(_state)
    s["html_existe"]   = INDEX_HTML.exists()
    s["refresh_mins"]  = REFRESH_MINS
    s["hora_colombia"] = _col_time()
    s["thread_vivo"]   = _bg_thread.is_alive()
    return jsonify(s)


@app.route("/data")
def data():
    f = OUT_DIR / "analisis.json"
    if f.exists():
        return send_file(str(f), mimetype="application/json")
    return jsonify({"error": "Sin datos aún"}), 404


@app.route("/favicon.ico")
def favicon_route():
    p = Path(FAVICON)
    return send_file(str(p)) if p.exists() else Response("", 204)


@app.route("/<path:filename>")
def static_files(filename):
    p = Path(filename)
    if p.exists() and p.suffix in (".png", ".jpg", ".ico", ".css", ".js", ".webp"):
        return send_file(str(p))
    return Response("Not found", 404)


# ── Entry point local ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 Flask local en puerto {port}")
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)