---
name: sport-analyst-agent
description: Agente especializado en análisis deportivo de fútbol con razonamiento estadístico avanzado. Úsalo para analizar partidos, calcular probabilidades Poisson/ELO, identificar Value Bets y generar justificaciones técnicas para predicciones deportivas.
---

# Sport Analyst Agent Skill

Este skill proporciona capacidades de análisis predictivo de fútbol basadas en modelos estadísticos y datos en tiempo real.

## Capacidades

1. **Modelo Poisson**: Cálculo de probabilidades 1X2 basado en la distribución de Poisson y goles proyectados.
2. **Razonamiento ELO**: Integración de ratings ELO para medir la fuerza relativa de los equipos.
3. **Detección de Valor**: Identificación de discrepancias entre la probabilidad estimada por el modelo y la probabilidad implícita de las casas de apuestas (BetPlay).
4. **Justificación Técnica**: Generación de razonamientos basados en forma reciente, superioridad técnica y métricas xG.

## Workflows

### 1. Analizar un partido o lista de partidos
Cuando tengas datos de partidos (JSON), usa el script `scripts/analyze_match.py` para obtener métricas avanzadas.

```bash
python scripts/analyze_match.py '<json_data>'
```

### 2. Estructura de Datos de Entrada (Recomendada)
Para obtener el mejor análisis, el JSON de entrada debe contener:
- `elo_local`, `elo_visitante`: Ratings ELO de los equipos.
- `local_form`, `visita_form`: Strings de forma reciente (ej: "WWWD").
- `betplay_impl_prob_1/x/2`: Probabilidades implícitas de la casa de apuestas.

### 3. Interpretación de Resultados
- **adv_confidence**: Nivel de confianza del 10-99%.
- **adv_is_value**: Indica si la apuesta tiene valor matemático positivo.
- **adv_expected_goals**: Goles proyectados para cada equipo (xG).

## Guía de Justificación
Al entregar predicciones al usuario, justifica siempre usando estos criterios:
- **Superioridad marcada**: Si la diferencia de ELO es > 150 pts.
- **Inercia ganadora**: Si la forma reciente muestra rachas positivas (WW).
- **Ineficiencia de Cuotas**: Si `adv_is_value` es verdadero, resalta que la probabilidad real supera a la de la casa.
