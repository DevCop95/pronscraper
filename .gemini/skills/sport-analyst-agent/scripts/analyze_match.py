import sys
import json
import math
from scipy.stats import poisson

class FootballAgent:
    def __init__(self):
        self.confidence_threshold = 60
        self.value_margin = 0.10

    def calculate_poisson_probs(self, avg_goals_home, avg_goals_away, max_goals=5):
        prob_home = 0.0
        prob_draw = 0.0
        prob_away = 0.0
        for h in range(max_goals + 1):
            for a in range(max_goals + 1):
                p = poisson.pmf(h, avg_goals_home) * poisson.pmf(a, avg_goals_away)
                if h > a: prob_home += p
                elif h == a: prob_draw += p
                else: prob_away += p
        total = prob_home + prob_draw + prob_away
        return {
            "1": float(round((prob_home / total) * 100, 2)),
            "X": float(round((prob_draw / total) * 100, 2)),
            "2": float(round((prob_away / total) * 100, 2))
        }

    def estimate_goals(self, elo_home, elo_away):
        elo_diff = elo_home - elo_away
        base_home, base_away = 1.35, 1.10
        adjustment = elo_diff / 500.0
        return max(0.2, base_home + adjustment), max(0.2, base_away - adjustment)

    def identify_value(self, model_prob, bookie_prob):
        if bookie_prob <= 0: return False
        edge = (model_prob - bookie_prob) / 100.0
        return bool(edge >= self.value_margin)

    def analyze(self, item):
        elo_l = item.get("elo_local")
        elo_v = item.get("elo_visitante")
        if elo_l and elo_v:
            exp_h, exp_a = self.estimate_goals(elo_l, elo_v)
            model_probs = self.calculate_poisson_probs(exp_h, exp_a)
        else:
            model_probs = {
                "1": float(item.get("prob_1", 0) or 0),
                "X": float(item.get("prob_x", 0) or 0),
                "2": float(item.get("prob_2", 0) or 0)
            }
        best_pick = max(model_probs, key=model_probs.get)
        model_prob = model_probs[best_pick]
        bp_prob = item.get(f"betplay_impl_prob_{best_pick.lower()}", 0) or 0
        is_value = self.identify_value(model_prob, bp_prob)
        confidence = min(99, max(10, model_prob * 0.8 + (15 if is_value else 0)))
        
        return {
            "adv_pick": best_pick,
            "adv_confidence": round(confidence),
            "adv_is_value": is_value,
            "adv_probs": model_probs,
            "adv_expected_goals": (round(exp_h, 2), round(exp_a, 2)) if (elo_l and elo_v) else None
        }

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python analyze_match.py '<json_data>'")
        sys.exit(1)
    try:
        data = json.loads(sys.argv[1])
        agent = FootballAgent()
        if isinstance(data, list):
            results = [agent.analyze(it) for it in data]
        else:
            results = agent.analyze(data)
        print(json.dumps(results, indent=2))
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)
