"""
app.py — Servidor Flask para Render (gunicorn compatible).
"""

import json, csv, sys, os, threading, time
from pathlib import Path
from datetime import datetime, timezone, timedelta

from flask import Flask, send_file, jsonify, Response, request

from src.scraper         import fetch_html, ALLOWED_URL
from src.parser_logic    import parse_predictions, to_rows
from src.analyzer        import analyze
from src.html_builder    import build as build_html
from src.betplay_fetcher import enrich_with_betplay
from src.stats_enricher  import enrich_with_stats, enrich_with_form

OUT_DIR       = Path("outputs")
INDEX_HTML    = Path("index.html")
TOP_N         = 20
CREATOR_NAME  = "DevOpsHB"
CREATOR_IMAGE = "creador.png"
FAVICON       = "favicon.ico"
REFRESH_MINS  = 60

app    = Flask(__name__)
_lock  = threading.Lock()
_state = {
    "last_update":    None,
    "running":        False,
    "error":          None,
    "stats":          {},
    "run_count":      0,
    "last_run_epoch": 0,
}


def _col_now() -> datetime:
    return datetime.now(timezone(timedelta(hours=-5)))

def _col_time() -> str:
    return _col_now().strftime("%H:%M")

def _col_ts() -> str:
    return _col_now().strftime("%H:%M COL · %d/%m/%Y")

def _mins_since_last_run() -> float:
    last = _state.get("last_run_epoch", 0)
    if not last:
        return 9999
    return (time.time() - last) / 60


def run_pipeline(force: bool = False) -> bool:
    with _lock:
        if _state["running"]:
            return False
        if not force and _mins_since_last_run() < 55:
            return False
        _state["running"] = True
        _state["error"]   = None

    try:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        run_n = _state["run_count"] + 1
        print(f"\n{'─'*55}")
        print(f"🔄 Pipeline #{run_n} — {_col_ts()}")

        print("⬇  Scraping...")
        HTML_CACHE = OUT_DIR / "cache.html"
        try:
            html_text = fetch_html(ALLOWED_URL)
            HTML_CACHE.write_text(html_text, encoding="utf-8")
            print("   ✓ HTML guardado en caché")
        except Exception as scrape_err:
            print(f"   ⚠ Scrape falló: {scrape_err}")
            if HTML_CACHE.exists():
                print("   🔄 Usando HTML en caché del último scrape exitoso...")
                html_text = HTML_CACHE.read_text(encoding="utf-8")
            else:
                raise RuntimeError(f"Scrape falló y no hay caché: {scrape_err}")

        print("🔍 Parseando...")
        items = parse_predictions(html_text, source=ALLOWED_URL)
        if not items:
            raise RuntimeError("No se encontraron partidos")
        print(f"   ✓ {len(items)} partidos")

        print("🏦 BetPlay...")
        items = enrich_with_betplay(items)

        print("📈 ClubElo...")
        items = enrich_with_stats(items)

        (OUT_DIR / "predicciones.json").write_text(
            json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        rows, cols = to_rows(items)
        with (OUT_DIR / "predicciones.csv").open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader(); w.writerows(rows)

        print("📊 Analizando...")
        result     = analyze(items, top_n=TOP_N)
        top        = result["top"]
        stats_data = result["stats"]

        # Forma: SOLO para el top (máx 40 requests)
        elo_names = [k for k in [r.get("equipo_local","") for r in top] +
                                 [r.get("equipo_visitante","") for r in top] if k]
        print(f"📅 Forma reciente ({len(top)} partidos del top)...")
        top = enrich_with_form(top, elo_names)

        print(f"   ✓ {stats_data['total_partidos']} partidos | "
              f"{stats_data['elite']} ELITE | {stats_data['alta']} Alta | "
              f"{stats_data['value_bets']} Value")

        (OUT_DIR / "analisis.json").write_text(
            json.dumps({
                "stats": stats_data,
                "generated_at": _col_ts(),
                "top": [
                    {k: v for k, v in r.items()
                     if not k.startswith("_") or k in
                     ("_favorito","_prob_win","_prob_rival","_confidence",
                      "_tier","_value","_pick","_margin")}
                    for r in top
                ],
            }, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        print("🎨 Generando HTML...")
        build_html(
            top=top, stats=stats_data,
            output_path=str(INDEX_HTML),
            creator_name=CREATOR_NAME,
            creator_image=CREATOR_IMAGE,
            favicon=FAVICON,
        )

        with _lock:
            _state["last_update"]    = _col_ts()
            _state["stats"]          = stats_data
            _state["run_count"]      = run_n
            _state["last_run_epoch"] = time.time()

        print(f"✅ Pipeline #{run_n} completo")
        print(f"{'─'*55}\n")
        return True

    except Exception as ex:
        import traceback
        with _lock:
            _state["error"] = str(ex)
        print(f"✗ Error: {ex}", file=sys.stderr)
        traceback.print_exc()
        return False
    finally:
        with _lock:
            _state["running"] = False


# ── Background loop: pipeline inicial + refresco cada hora ───────────────────
def _background_loop():
    # Pipeline inicial en background (NO bloquea gunicorn)
    print("🚀 Pipeline inicial arrancando en background...")
    try:
        run_pipeline(force=True)
    except Exception as ex:
        print(f"✗ Pipeline inicial error: {ex}")

    # Luego repetir cada hora
    while True:
        time.sleep(REFRESH_MINS * 60)
        try:
            run_pipeline()
        except Exception as ex:
            print(f"✗ Background loop error: {ex}")


_bg = threading.Thread(target=_background_loop, daemon=True, name="bg-pipeline")
_bg.start()


@app.route("/")
def index():
    if _mins_since_last_run() >= 55 and not _state["running"]:
        t = threading.Thread(target=run_pipeline, args=(True,), daemon=True)
        t.start()
    if INDEX_HTML.exists():
        return send_file(str(INDEX_HTML))
    return Response("""<!DOCTYPE html><html lang="es">
    <head><meta charset="UTF-8"><title>Cargando...</title>
    <meta http-equiv="refresh" content="10">
    <style>
      body{margin:0;display:flex;align-items:center;justify-content:center;
           min-height:100vh;background:#0f0f1a;font-family:sans-serif;color:#fff}
      .box{text-align:center;padding:40px}
      .spinner{width:48px;height:48px;border:4px solid #333;
               border-top-color:#B8960C;border-radius:50%;
               animation:spin 1s linear infinite;margin:0 auto 20px}
      @keyframes spin{to{transform:rotate(360deg)}}
      h2{color:#B8960C}p{color:#aaa;font-size:14px}
    </style></head>
    <body><div class="box">
      <div class="spinner"></div>
      <h2>Preparando análisis...</h2>
      <p>Generando picks del día. Se recargará en ~10s.</p>
      <p style="font-size:12px;color:#555">DevOpsHB · SportAnalysis</p>
    </div></body></html>""", mimetype="text/html")


@app.route("/upload", methods=["POST"])
def upload_html():
    html = request.get_data(as_text=True)
    if not html or len(html) < 500:
        return jsonify({"error": "HTML vacío o muy corto"}), 400
    if "competition" not in html and "match" not in html:
        return jsonify({"error": "HTML no contiene partidos"}), 400
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "cache.html").write_text(html, encoding="utf-8")
    print(f"📥 HTML recibido ({len(html)} chars) — disparando pipeline")
    t = threading.Thread(target=run_pipeline, args=(True,), daemon=True)
    t.start()
    return jsonify({"status": "ok", "chars": len(html), "message": "Pipeline iniciado"})


@app.route("/ping")
def ping():
    mins = _mins_since_last_run()
    if mins >= 55 and not _state["running"]:
        t = threading.Thread(target=run_pipeline, args=(True,), daemon=True)
        t.start()
        return jsonify({"status": "pipeline_started", "mins_since_last": round(mins, 1), "hora": _col_time()})
    return jsonify({"status": "ok", "mins_since_last": round(mins, 1), "next_run_in_mins": round(max(0, 55 - mins), 1), "hora": _col_time()})


@app.route("/refresh")
def refresh():
    if _state["running"]:
        return jsonify({"status": "running", "message": "Pipeline ya en curso..."})
    t = threading.Thread(target=run_pipeline, args=(True,), daemon=True)
    t.start()
    return jsonify({"status": "started", "message": "Pipeline iniciado. Refresca en ~45s"})


@app.route("/status")
def status():
    with _lock:
        s = dict(_state)
    s.pop("last_run_epoch", None)
    s["html_existe"]       = INDEX_HTML.exists()
    s["refresh_mins"]      = REFRESH_MINS
    s["hora_colombia"]     = _col_time()
    s["thread_vivo"]       = _bg.is_alive()
    s["mins_desde_update"] = round(_mins_since_last_run(), 1)
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
    if p.exists() and p.suffix in (".png",".jpg",".ico",".css",".js",".webp"):
        return send_file(str(p))
    return Response("Not found", 404)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 Flask local en puerto {port}")
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)