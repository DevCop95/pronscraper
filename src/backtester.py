import json
from pathlib import Path
from datetime import datetime

LOG_FILE = Path("outputs/history.json")

def log_predictions(top_picks: list):
    """Guarda las predicciones actuales en un historial para posterior validación."""
    if not top_picks:
        return
    
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    history = []
    if LOG_FILE.exists():
        try:
            history = json.loads(LOG_FILE.read_text(encoding="utf-8"))
        except:
            history = []
            
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    new_entry = {
        "date": timestamp,
        "picks": [
            {
                "teams": p.get("equipos"),
                "comp": p.get("competicion"),
                "pick": p.get("_pick"),
                "confidence": p.get("_confidence"),
                "tier": p.get("_tier"),
                "is_value": p.get("_value"),
                "adv_pick": p.get("adv_pick")
            }
            for p in top_picks
        ]
    }
    
    history.append(new_entry)
    
    # Mantener solo los últimos 100 runs para no saturar
    history = history[-100:]
    
    LOG_FILE.write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"   ✓ {len(top_picks)} picks registrados en el historial.")

def get_performance_summary():
    """Calcula estadísticas rápidas de aciertos (requeriría una función de actualización de resultados)."""
    # Esta función se expandirá cuando implementemos el fetcher de resultados reales.
    pass
