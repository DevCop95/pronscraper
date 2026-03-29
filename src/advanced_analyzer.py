"""
advanced_analyzer.py - Agente especializado en análisis deportivo de fútbol.
Implementa razonamiento estadístico avanzado, modelos probabilísticos y justificación técnica.
"""

import math
from scipy.stats import poisson
from typing import Any, Dict, List

class FootballAgent:
    def __init__(self):
        self.name = "Advanced Football Analyst Agent"
        self.confidence_threshold = 60
        self.value_margin = 0.10  # 10% de ventaja sobre la casa

    def calculate_poisson_probs(self, avg_goals_home: float, avg_goals_away: float, max_goals: int = 5) -> Dict[str, float]:
        """
        Calcula probabilidades de 1X2 usando la distribución de Poisson.
        """
        prob_home = 0.0
        prob_draw = 0.0
        prob_away = 0.0

        for h in range(max_goals + 1):
            for a in range(max_goals + 1):
                # Probabilidad de que el local anote h y el visitante anote a
                p = poisson.pmf(h, avg_goals_home) * poisson.pmf(a, avg_goals_away)
                
                if h > a:
                    prob_home += p
                elif h == a:
                    prob_draw += p
                else:
                    prob_away += p
        
        # Normalizar para que sumen 1 (por si acaso el max_goals es bajo)
        total = prob_home + prob_draw + prob_away
        return {
            "1": float(round((prob_home / total) * 100, 2)),
            "X": float(round((prob_draw / total) * 100, 2)),
            "2": float(round((prob_away / total) * 100, 2))
        }

    def estimate_goals(self, elo_home: float, elo_away: float) -> tuple:
        """
        Estima goles promedio basados en la diferencia de ELO.
        Basado en una simplificación de modelos de regresión de goles.
        """
        elo_diff = elo_home - elo_away
        # Constante base de goles en fútbol (~1.3 local, ~1.1 visitante)
        base_home = 1.35
        base_away = 1.10
        
        # Ajuste por ELO (cada 100 puntos de diferencia suele ser ~0.2 goles)
        adjustment = elo_diff / 500.0
        
        exp_home = max(0.2, base_home + adjustment)
        exp_away = max(0.2, base_away - adjustment)
        
        return exp_home, exp_away

    def identify_value(self, model_prob: float, bookie_prob: float) -> bool:
        """
        Identifica si hay valor: Prob Real > Prob Implícita de la casa.
        """
        if bookie_prob <= 0: return False
        # Valor real = (Prob_Modelo - Prob_Casa) / Prob_Casa
        edge = (model_prob - bookie_prob) / 100.0
        return edge >= self.value_margin

    def generate_justification(self, item: Dict[str, Any], model_probs: Dict[str, float]) -> str:
        """
        Genera un razonamiento técnico para la predicción.
        """
        pick = item.get("_pick", "UNK")
        elo_diff = item.get("elo_diff", 0) or 0
        local = item.get("equipo_local", "Local")
        visita = item.get("equipo_visitante", "Visitante")
        
        reasons = []
        
        # Factor ELO
        if abs(elo_diff) > 150:
            dominant = local if elo_diff > 0 else visita
            reasons.append(f"Superioridad técnica marcada de {dominant} (Dif. ELO: {abs(elo_diff)} pts).")
        elif abs(elo_diff) > 50:
            dominant = local if elo_diff > 0 else visita
            reasons.append(f"Ventaja competitiva para {dominant} basada en ratings históricos.")
        
        # Factor Forma
        l_form = item.get("local_form", "")
        v_form = item.get("visita_form", "")
        if "WW" in l_form:
            reasons.append(f"{local} mantiene una inercia ganadora sólida.")
        if "LL" in v_form:
            reasons.append(f"{visita} atraviesa una racha negativa de resultados.")
            
        # Factor Probabilidad Poisson
        p_val = model_probs.get(pick, 0)
        if p_val > 55:
            reasons.append(f"Modelo Poisson estima una probabilidad de éxito del {p_val}% para el mercado {pick}.")
            
        # Factor Valor
        if item.get("_value"):
            reasons.append("Se detecta ineficiencia en la cuota de la casa de apuestas (Value Bet).")

        if not reasons:
            return "Análisis basado en correlación estadística estándar y equilibrio de fuerzas."
            
        return " ".join(reasons)

    def analyze_match(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Realiza el análisis completo de un partido.
        """
        elo_l = item.get("elo_local")
        elo_v = item.get("elo_visitante")
        
        # Si no hay ELO, usamos las probabilidades base del scraper
        if elo_l and elo_v:
            exp_h, exp_a = self.estimate_goals(elo_l, elo_v)
            model_probs = self.calculate_poisson_probs(exp_h, exp_a)
        else:
            model_probs = {
                "1": float(item.get("prob_1", 0) or 0),
                "X": float(item.get("prob_x", 0) or 0),
                "2": float(item.get("prob_2", 0) or 0)
            }

        # Determinar pick sugerido por el modelo
        best_pick = max(model_probs, key=model_probs.get)
        model_prob = model_probs[best_pick]
        
        # Comparar con BetPlay si existe
        bp_prob = 0
        if best_pick == "1": bp_prob = item.get("betplay_impl_prob_1", 0) or 0
        elif best_pick == "X": bp_prob = item.get("betplay_impl_prob_x", 0) or 0
        elif best_pick == "2": bp_prob = item.get("betplay_impl_prob_2", 0) or 0
        
        is_value = self.identify_value(model_prob, bp_prob)
        
        # Calcular confianza ajustada
        # (Mezclamos prob del modelo con el edge encontrado)
        confidence = model_prob * 0.8 + (15 if is_value else 0)
        confidence = min(99, max(10, confidence))
        
        # Justificación
        temp_item = dict(item)
        temp_item.update({"_pick": best_pick, "_value": is_value})
        justification = self.generate_justification(temp_item, model_probs)
        
        return {
            "model_probs": model_probs,
            "best_pick": best_pick,
            "is_value": is_value,
            "confidence": round(confidence),
            "justification": justification,
            "expected_goals": (round(exp_h, 2), round(exp_a, 2)) if (elo_l and elo_v) else (None, None)
        }

def run_advanced_analysis(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    agent = FootballAgent()
    enriched = []
    for it in items:
        analysis = agent.analyze_match(it)
        e = dict(it)
        e.update({
            "adv_pick": analysis["best_pick"],
            "adv_confidence": analysis["confidence"],
            "adv_is_value": analysis["is_value"],
            "adv_justification": analysis["justification"],
            "adv_expected_goals": analysis["expected_goals"],
            "adv_probs": analysis["model_probs"]
        })
        enriched.append(e)
    return enriched
