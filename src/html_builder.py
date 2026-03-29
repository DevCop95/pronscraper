"""html_builder.py — Dashboard premium Bootstrap 5 + Bootstrap Icons."""

import html as _h
from datetime import datetime
from pathlib import Path
from typing import Any


def _e(s: Any) -> str:
    return _h.escape(str(s) if s is not None else "")


TIER_CFG = {
    "ELITE": {"color": "#92720A", "bg": "#FBF5E0", "border": "#D4AA3A",
               "badge": "warning",  "icon": "bi-trophy-fill",    "label": "ÉLITE"},
    "ALTA":  {"color": "#1A5C96", "bg": "#EBF4FF", "border": "#4A9BE8",
               "badge": "primary",  "icon": "bi-graph-up-arrow",  "label": "ALTA"},
    "MEDIA": {"color": "#4A5A6A", "bg": "#F2F5F8", "border": "#8A9BAC",
               "badge": "secondary","icon": "bi-dash-circle",     "label": "MEDIA"},
    "BAJA":  {"color": "#6A7A8A", "bg": "#F5F7FA", "border": "#B0BAC8",
               "badge": "light",    "icon": "bi-dash",            "label": "BAJA"},
}


def _t(tier: str) -> dict:
    return TIER_CFG.get(tier, TIER_CFG["MEDIA"])


def _form_dots(form: str) -> str:
    if not form:
        return '<span class="text-muted small">—</span>'
    html_out = []
    for ch in form.upper().replace(",","").replace(" ","")[:6]:
        cls = "bg-success" if ch=="W" else "bg-danger" if ch=="L" else "bg-warning"
        html_out.append(
            f'<span class="{cls} rounded-circle d-inline-block me-1" '
            f'style="width:9px;height:9px" title="{ch}"></span>'
        )
    return "".join(html_out)


def _prob_pill(label: str, val: int, active: bool, color: str = "#92720A") -> str:
    if active:
        return (f'<div class="text-center p-2 rounded-3 border h-100" '
                f'style="background:{color}15;border-color:{color}50!important">'
                f'<div class="fw-bold small mb-1" style="color:{color}">{_e(label)}</div>'
                f'<div class="fw-black" style="font-size:1.4rem;color:{color}">{val}%</div>'
                f'</div>')
    return (f'<div class="text-center p-2 rounded-3 border border-light-subtle bg-light h-100">'
            f'<div class="text-muted small mb-1">{_e(label)}</div>'
            f'<div class="fw-bold text-secondary" style="font-size:1.4rem">{val}%</div>'
            f'</div>')


def _stat_row_bs(label: str, val: Any, icon: str = "", highlight: bool = False) -> str:
    val_cls = 'fw-bold text-warning-emphasis' if highlight else 'fw-semibold'
    return (f'<div class="d-flex justify-content-between align-items-center py-2 border-bottom border-light">'
            f'<span class="text-muted small">{icon} {_e(label)}</span>'
            f'<span class="{val_cls} small">{_e(str(val))}</span>'
            f'</div>')


def _section_hd(title: str, icon: str) -> str:
    return (f'<div class="d-flex align-items-center gap-2 mt-4 mb-2 pb-2 border-bottom border-warning-subtle">'
            f'<i class="bi {icon} text-warning"></i>'
            f'<span class="fw-bold text-uppercase small" style="letter-spacing:1.5px;color:#92720A">{_e(title)}</span>'
            f'</div>')


def _modal(r: dict, idx: int) -> str:
    mid  = f"m{idx}"
    tier = r.get("_tier", "MEDIA")
    tc   = _t(tier)
    acc  = tc["color"]

    fav    = _e(r.get("_favorito",""))
    eq     = _e(r.get("equipos",""))
    comp   = _e(r.get("competicion",""))
    hora   = _e(r.get("hora","") or "Sin hora")
    prono  = _e(r.get("pronostico",""))
    pick   = _e(r.get("_pick",""))
    conf   = r.get("_confidence",0)
    margin = r.get("_margin",0)
    p_win  = r.get("_prob_win",0)

    p1  = int(r.get("prob_1",0) or 0)
    px  = int(r.get("prob_x",0) or 0)
    p2  = int(r.get("prob_2",0) or 0)
    o15 = int(r.get("prob_over_15",0) or 0)
    o25 = int(r.get("prob_over_25",0) or 0)
    o35 = int(r.get("prob_over_35",0) or 0)
    bty = int(r.get("prob_btts_yes",0) or 0)
    btn = int(r.get("prob_btts_no",0) or 0)
    ht1 = int(r.get("prob_ht1",0) or 0)
    htx = int(r.get("prob_htx",0) or 0)
    ht2 = int(r.get("prob_ht2",0) or 0)

    is_local = r.get("_pick","") in ("1","1X")
    p1_hl = is_local
    p2_hl = not is_local and r.get("_pick","") not in ("X",)

    elo_l   = r.get("elo_local")
    elo_v   = r.get("elo_visitante")
    elo_d   = r.get("elo_diff")
    elo_fav = r.get("elo_favorito","—")
    elo_pw  = r.get("elo_prob_home_win")
    elo_pd  = r.get("elo_prob_draw")
    elo_pa  = r.get("elo_prob_away_win")
    lpos    = r.get("local_pos"); lpts = r.get("local_pts"); lform = r.get("local_form","")
    vpos    = r.get("visita_pos"); vpts = r.get("visita_pts"); vform = r.get("visita_form","")
    lform_data = r.get("local_form_data", [])
    vform_data = r.get("visita_form_data", [])
    bp_o1   = r.get("betplay_odds_1"); bp_ox = r.get("betplay_odds_x"); bp_o2 = r.get("betplay_odds_2")
    bp_p1   = r.get("betplay_impl_prob_1",0); bp_px = r.get("betplay_impl_prob_x",0)
    bp_p2   = r.get("betplay_impl_prob_2",0)
    bp_ok   = r.get("betplay_matched",False)

    # ── Advanced Agent Section ──────────────────────────────────────────────
    adv_just     = _e(r.get("adv_justification", "Análisis en curso..."))
    adv_conf     = r.get("adv_confidence", 0)
    adv_pick     = _e(r.get("adv_pick", "—"))
    adv_exp_goals = r.get("adv_expected_goals")
    adv_probs    = r.get("adv_probs", {})
    
    exp_goals_html = ""
    if adv_exp_goals and adv_exp_goals[0] is not None:
        exp_goals_html = (f'<div class="badge bg-dark-subtle text-dark border border-dark-subtle mb-2">'
                          f'<i class="bi bi-bullseye me-1"></i>xG Esperado: {adv_exp_goals[0]} - {adv_exp_goals[1]}</div>')

    agent_html = f"""
    {_section_hd("Agente IA — Razonamiento Estadístico","bi-robot")}
    <div class="p-3 rounded-3 mb-3" style="background:rgba(184,150,12,0.08); border:1px solid rgba(184,150,12,0.2)">
        <div class="d-flex align-items-center gap-2 mb-2">
            <span class="badge bg-warning text-dark"><i class="bi bi-cpu-fill me-1"></i>MODELO POISSON + ELO</span>
            <span class="ms-auto fw-bold" style="color:#92720A">Confianza Agente: {adv_conf}%</span>
        </div>
        <div class="fw-semibold text-dark mb-2" style="font-size:13px; line-height:1.5">
            <i class="bi bi-chat-right-quote-fill text-warning me-2"></i>"{adv_just}"
        </div>
        {exp_goals_html}
        <div class="row g-1 text-center mt-2">
            <div class="col-4">
                <div class="p-1 rounded bg-white border" style="font-size:10px">
                    <div class="text-muted">IA LOCAL</div>
                    <div class="fw-bold">{adv_probs.get('1', 0)}%</div>
                </div>
            </div>
            <div class="col-4">
                <div class="p-1 rounded bg-white border" style="font-size:10px">
                    <div class="text-muted">IA EMPATE</div>
                    <div class="fw-bold">{adv_probs.get('X', 0)}%</div>
                </div>
            </div>
            <div class="col-4">
                <div class="p-1 rounded bg-white border" style="font-size:10px">
                    <div class="text-muted">IA VISITA</div>
                    <div class="fw-bold">{adv_probs.get('2', 0)}%</div>
                </div>
            </div>
        </div>
    </div>"""

    local_n  = _e(r.get("equipo_local","Local"))
    visita_n = _e(r.get("equipo_visitante","Visitante"))
    vtag     = ('<span class="badge bg-warning text-dark ms-1"><i class="bi bi-gem me-1"></i>VALUE BET</span>'
                if r.get("_value") else "")

    # ── Elo section ───────────────────────────────────────────────────────────
    elo_html = ""
    if elo_l or elo_v or elo_pw is not None:
        elo_dir = (elo_d > 0 and is_local) or (elo_d and elo_d < 0 and not is_local) if elo_d else False
        elo_c   = "text-success" if elo_dir else "text-secondary"

        elo_probs_html = ""
        if elo_pw is not None:
            elo_probs_html = f"""
        <div class="mb-3">
          <div class="d-flex align-items-center gap-1 mb-1">
            <span class="small text-muted fw-semibold">Probabilidades según Elo</span>
            <span class="badge bg-secondary-subtle text-secondary-emphasis" style="font-size:9px">CLUBELO</span>
          </div>
          <div class="row g-1 text-center">
            <div class="col-4">
              <div class="p-2 rounded {'bg-success-subtle border border-success-subtle' if elo_pw and elo_pw > max(elo_pd or 0, elo_pa or 0) else 'bg-light'}">
                <div class="text-muted" style="font-size:11px">LOCAL</div>
                <div class="fw-bold {'text-success' if elo_pw and elo_pw > max(elo_pd or 0, elo_pa or 0) else ''}" style="font-size:1.1rem">{elo_pw}%</div>
              </div>
            </div>
            <div class="col-4">
              <div class="p-2 rounded {'bg-secondary-subtle border border-secondary-subtle' if elo_pd and elo_pd > max(elo_pw or 0, elo_pa or 0) else 'bg-light'}">
                <div class="text-muted" style="font-size:11px">EMPATE</div>
                <div class="fw-bold" style="font-size:1.1rem">{elo_pd}%</div>
              </div>
            </div>
            <div class="col-4">
              <div class="p-2 rounded {'bg-primary-subtle border border-primary-subtle' if elo_pa and elo_pa > max(elo_pw or 0, elo_pd or 0) else 'bg-light'}">
                <div class="text-muted" style="font-size:11px">VISITA</div>
                <div class="fw-bold {'text-primary' if elo_pa and elo_pa > max(elo_pw or 0, elo_pd or 0) else ''}" style="font-size:1.1rem">{elo_pa}%</div>
              </div>
            </div>
          </div>
        </div>"""

        elo_html = f"""
        {_section_hd("Club Elo — Fuerza histórica","bi-lightning-charge-fill")}
        {elo_probs_html}
        <div class="row g-2 mb-2">
          <div class="col-6">
            <div class="card border-0 bg-light text-center py-3">
              <div class="text-muted small mb-1">{local_n}</div>
              <div class="fw-black" style="font-size:1.8rem">{int(elo_l) if elo_l else "—"}</div>
              <div class="badge bg-secondary-subtle text-secondary-emphasis">ELO</div>
            </div>
          </div>
          <div class="col-6">
            <div class="card border-0 bg-light text-center py-3">
              <div class="text-muted small mb-1">{visita_n}</div>
              <div class="fw-black" style="font-size:1.8rem">{int(elo_v) if elo_v else "—"}</div>
              <div class="badge bg-secondary-subtle text-secondary-emphasis">ELO</div>
            </div>
          </div>
        </div>
        {_stat_row_bs("Diferencia", f"{'+' if elo_d and elo_d>0 else ''}{int(elo_d) if elo_d else '—'} pts","<i class='bi bi-arrows-expand-vertical'></i>", bool(elo_d and abs(elo_d)>30))}
        {_stat_row_bs("Favorito por Elo", elo_fav or "—","<i class='bi bi-star-fill'></i>")}"""

    # ── Últimos 5 partidos ────────────────────────────────────────────────────
    def _form_row(m: dict) -> str:
        res   = m.get("result","?")
        chg   = m.get("change", 0)
        dt    = (m.get("date","") or "")[:10]
        elo_a = m.get("elo_after","—")
        color = {"W":"#198754","D":"#6c757d","L":"#dc3545"}.get(res,"#aaa")
        label = {"W":"V","D":"E","L":"D"}.get(res,"?")
        sign  = "+" if chg > 0 else ""
        return (f'<tr>'
                f'<td><span class="badge rounded-pill" style="background:{color};min-width:28px">{label}</span></td>'
                f'<td class="text-muted small">{dt}</td>'
                f'<td class="text-end small fw-semibold" style="color:{color}">{sign}{chg}</td>'
                f'<td class="text-end small text-muted">{int(elo_a) if elo_a != "—" else "—"}</td>'
                f'</tr>')

    form_html = ""
    if lform_data or vform_data:
        rows_l = "".join(_form_row(m) for m in lform_data) or '<tr><td colspan="4" class="text-muted small">Sin datos</td></tr>'
        rows_v = "".join(_form_row(m) for m in vform_data) or '<tr><td colspan="4" class="text-muted small">Sin datos</td></tr>'
        form_html = f"""
        {_section_hd("Últimos 5 partidos — Forma reciente","bi-bar-chart-steps")}
        <div class="row g-3">
          <div class="col-6">
            <div class="fw-semibold small mb-2 text-truncate">{local_n}</div>
            <table class="table table-sm mb-0" style="font-size:12px">
              <thead class="table-light"><tr>
                <th>Res</th><th>Fecha</th><th class="text-end">Δ Elo</th><th class="text-end">Elo</th>
              </tr></thead>
              <tbody>{rows_l}</tbody>
            </table>
          </div>
          <div class="col-6">
            <div class="fw-semibold small mb-2 text-truncate">{visita_n}</div>
            <table class="table table-sm mb-0" style="font-size:12px">
              <thead class="table-light"><tr>
                <th>Res</th><th>Fecha</th><th class="text-end">Δ Elo</th><th class="text-end">Elo</th>
              </tr></thead>
              <tbody>{rows_v}</tbody>
            </table>
          </div>
        </div>"""

    # ── Standings ─────────────────────────────────────────────────────────────
    stand_html = ""
    if lpos or vpos:
        stand_html = f"""
        {_section_hd("Tabla de posiciones","bi-list-ol")}
        <div class="table-responsive">
          <table class="table table-sm table-hover align-middle small">
            <thead class="table-light"><tr>
              <th>Equipo</th><th class="text-center">Pos</th>
              <th class="text-center">Pts</th><th>Forma</th>
            </tr></thead>
            <tbody>
              <tr>
                <td class="fw-semibold">{local_n}</td>
                <td class="text-center fw-bold text-warning-emphasis">{lpos or "—"}</td>
                <td class="text-center">{lpts or "—"}</td>
                <td>{_form_dots(lform or "")}</td>
              </tr>
              <tr>
                <td class="fw-semibold">{visita_n}</td>
                <td class="text-center fw-bold text-primary-emphasis">{vpos or "—"}</td>
                <td class="text-center">{vpts or "—"}</td>
                <td>{_form_dots(vform or "")}</td>
              </tr>
            </tbody>
          </table>
        </div>"""

    # ── BetPlay ───────────────────────────────────────────────────────────────
    bp_html = ""
    if bp_ok and bp_o1:
        agreement = abs(p_win - (bp_p1 if is_local else bp_p2))
        agree_icon = "bi-check-circle-fill text-success" if agreement<=10 else \
                     "bi-exclamation-triangle-fill text-warning" if agreement<=20 else \
                     "bi-x-circle-fill text-danger"
        agree_txt  = "Alineado" if agreement<=10 else "Discrepancia leve" if agreement<=20 else "Contradice"
        bp_html = f"""
        {_section_hd("BetPlay — Cuotas en vivo","bi-currency-dollar")}
        <div class="row g-2 mb-2">
          <div class="col-4"><div class="card border-0 bg-primary-subtle text-center py-2 px-1">
            <div class="small fw-semibold text-primary-emphasis mb-1">LOCAL (1)</div>
            <div class="fw-black text-primary" style="font-size:1.4rem">{bp_o1 or "—"}</div>
            <div class="text-muted" style="font-size:11px">{bp_p1}% impl.</div>
          </div></div>
          <div class="col-4"><div class="card border-0 bg-light text-center py-2 px-1">
            <div class="small fw-semibold text-secondary mb-1">EMPATE (X)</div>
            <div class="fw-black text-secondary" style="font-size:1.4rem">{bp_ox or "—"}</div>
            <div class="text-muted" style="font-size:11px">{bp_px}% impl.</div>
          </div></div>
          <div class="col-4"><div class="card border-0 bg-primary-subtle text-center py-2 px-1">
            <div class="small fw-semibold text-primary-emphasis mb-1">VISITA (2)</div>
            <div class="fw-black text-primary" style="font-size:1.4rem">{bp_o2 or "—"}</div>
            <div class="text-muted" style="font-size:11px">{bp_p2}% impl.</div>
          </div></div>
        </div>
        {_stat_row_bs("Consenso",f'<i class="bi {agree_icon}"></i> {agree_txt}',"",agreement<=10)}"""

    # ── Radial SVG ────────────────────────────────────────────────────────────
    circ = 125.66
    dash = circ * conf / 100
    colors = {"ELITE":"#92720A","ALTA":"#1A5C96","MEDIA":"#6A7A8A","BAJA":"#B0BAC8"}
    rc = colors.get(tier,"#6A7A8A")
    ring = (f'<svg viewBox="0 0 44 44" width="52" height="52">'
            f'<circle cx="22" cy="22" r="20" fill="none" stroke="#E8EDF3" stroke-width="3"/>'
            f'<circle cx="22" cy="22" r="20" fill="none" stroke="{rc}" stroke-width="3"'
            f' stroke-dasharray="{dash:.1f} {circ:.1f}" stroke-linecap="round"'
            f' transform="rotate(-90 22 22)"/>'
            f'<text x="22" y="27" text-anchor="middle" fill="{rc}"'
            f' font-size="10" font-weight="700" font-family=\'Sora,sans-serif\'>{conf}</text></svg>')

    return f"""
<div class="offcanvas offcanvas-end" tabindex="-1" id="{mid}" style="width:min(600px,100vw)">
  <div class="offcanvas-header border-bottom" style="border-left:4px solid {acc}">
    <div class="flex-grow-1 min-width-0">
      <div class="d-flex align-items-center flex-wrap gap-2 mb-2">
        <span class="badge bg-{tc['badge']} text-dark">
          <i class="bi {tc['icon']} me-1"></i>{tc['label']}
        </span>
        {vtag}
        <span class="text-muted small"><i class="bi bi-trophy me-1"></i>{comp}</span>
        <span class="badge bg-warning-subtle text-warning-emphasis border border-warning-subtle ms-auto"><i class="bi bi-clock-fill me-1"></i>{hora}</span>
      </div>
      <h5 class="mb-1 fw-black" style="color:{acc}">{fav}</h5>
      <div class="text-muted small">{eq}</div>
      <div class="fst-italic text-secondary" style="font-size:12px">{prono}</div>
    </div>
    <button type="button" class="btn-close ms-3" data-bs-dismiss="offcanvas"></button>
  </div>
  <div class="offcanvas-body">

    <!-- Agente IA -->
    {agent_html}

    <!-- KPIs -->
    <div class="row g-3 mb-1">
      <div class="col-4">
        <div class="card border-0 text-center py-3" style="background:{tc['bg']};border:1px solid {tc['border']}!important">
          <div class="small fw-bold mb-1" style="color:{acc};letter-spacing:1px">CONFIANZA</div>
          <div style="font-size:2rem;font-weight:900;color:{acc};line-height:1">{conf}<span style="font-size:1rem">%</span></div>
        </div>
      </div>
      <div class="col-4">
        <div class="card border-0 bg-light text-center py-3">
          <div class="small fw-bold text-muted mb-1" style="letter-spacing:1px">PICK</div>
          <div style="font-size:2rem;font-weight:900;color:{acc};line-height:1">{pick}</div>
        </div>
      </div>
      <div class="col-4">
        <div class="card border-0 bg-light text-center py-3">
          <div class="small fw-bold text-muted mb-1" style="letter-spacing:1px">VENTAJA</div>
          <div style="font-size:2rem;font-weight:900;line-height:1">+{margin}<span style="font-size:1rem">pts</span></div>
        </div>
      </div>
    </div>

    <!-- 1X2 -->
    {_section_hd("Probabilidades de resultado","bi-bar-chart-fill")}
    <div class="row g-2 mb-1">
      <div class="col-4">{_prob_pill("LOCAL (1)", p1, p1_hl, acc)}</div>
      <div class="col-4">{_prob_pill("EMPATE (X)", px, False, "#6A7A8A")}</div>
      <div class="col-4">{_prob_pill("VISITA (2)", p2, p2_hl, acc)}</div>
    </div>

    <!-- HT -->
    {_section_hd("Medio tiempo","bi-hourglass-split")}
    <div class="row g-2 mb-1">
      <div class="col-4">{_prob_pill("HT Local", ht1, False, "#6A7A8A")}</div>
      <div class="col-4">{_prob_pill("HT Empate", htx, False, "#6A7A8A")}</div>
      <div class="col-4">{_prob_pill("HT Visita", ht2, False, "#6A7A8A")}</div>
    </div>

    <!-- Goles -->
    {_section_hd("Mercado de goles","bi-bullseye")}
    <div class="row g-2 mb-1">
      <div class="col">{_prob_pill("+1.5", o15, o15>=65, "#22A86E")}</div>
      <div class="col">{_prob_pill("+2.5", o25, o25>=65, "#22A86E")}</div>
      <div class="col">{_prob_pill("+3.5", o35, o35>=65, "#22A86E")}</div>
      <div class="col">{_prob_pill("BTTS Sí", bty, bty>=60, "#E8A020")}</div>
      <div class="col">{_prob_pill("BTTS No", btn, btn>=60, "#E8A020")}</div>
    </div>

    {elo_html}
    {form_html}
    {stand_html}
    {bp_html}

    <div class="mt-4 p-3 rounded-3 bg-light border border-light-subtle">
      <div class="small text-muted" style="line-height:1.6">
        <i class="bi bi-info-circle me-1"></i>
        Score = prob. victoria (60%) + margen (40%) + claridad pick (20%) ± Elo ± BetPlay.<br>
        Solo fines informativos. No constituye consejo de apuestas.
      </div>
    </div>
  </div>
</div>"""


def _card(idx: int, r: dict) -> str:
    tier     = r.get("_tier","MEDIA")
    tc       = _t(tier)
    acc      = tc["color"]
    fav      = _e(r.get("_favorito",""))
    conf     = r.get("_confidence",0)
    pick     = _e(r.get("_pick",""))
    eq       = _e(r.get("equipos",""))
    comp     = _e(r.get("competicion",""))
    hora     = _e(r.get("hora","") or "Sin hora")
    prono    = _e(r.get("pronostico",""))
    margin   = r.get("_margin",0)
    value    = r.get("_value",False)
    p1       = int(r.get("prob_1",0) or 0)
    p2       = int(r.get("prob_2",0) or 0)
    px       = int(r.get("prob_x",0) or 0)
    o25      = int(r.get("prob_over_25",0) or 0)
    bty      = int(r.get("prob_btts_yes",0) or 0)
    is_local = r.get("_pick","") in ("1","1X")
    mid      = f"m{idx}"

    rank_colors = ["#92720A","#707888","#956A40"]
    rank_c = rank_colors[idx-1] if idx <= 3 else "#A0AAB4"

    elo_fav = r.get("elo_favorito")
    elo_ok  = elo_fav and ((elo_fav=="LOCAL" and is_local) or (elo_fav=="VISITANTE" and not is_local))
    elo_badge = ""
    if elo_fav:
        elo_badge = (f'<span class="badge bg-{"success" if elo_ok else "secondary"}-subtle '
                     f'text-{"success" if elo_ok else "secondary"}-emphasis border border-{"success" if elo_ok else "secondary"}-subtle small">'
                     f'<i class="bi bi-lightning-charge me-1"></i>Elo: {elo_fav}</span>')

    bp_badge = ""
    if r.get("betplay_matched"):
        bp_badge = ('<span class="badge bg-primary-subtle text-primary-emphasis border border-primary-subtle small">'
                    '<i class="bi bi-currency-dollar me-1"></i>BetPlay</span>')

    ai_badge = ""
    if r.get("adv_confidence", 0) >= 70:
        ai_badge = ('<span class="badge bg-warning text-dark border border-warning small">'
                    '<i class="bi bi-robot me-1"></i>IA: Alta Confianza</span>')
    elif r.get("adv_is_value"):
        ai_badge = ('<span class="badge bg-info-subtle text-info-emphasis border border-info-subtle small">'
                    '<i class="bi bi-robot me-1"></i>IA: Value Detectado</span>')

    vtag = ('<span class="badge bg-warning text-dark small"><i class="bi bi-gem me-1"></i>VALUE</span>'
            if value else "")

    p1w = min(100,p1); pxw = min(100,px); p2w = min(100,p2)
    active_c = acc

    circ = 125.66; dash = circ*conf/100
    colors = {"ELITE":"#92720A","ALTA":"#1A5C96","MEDIA":"#6A7A8A","BAJA":"#B0BAC8"}
    rc = colors.get(tier,"#6A7A8A")
    ring = (f'<svg viewBox="0 0 44 44" width="48" height="48" class="flex-shrink-0">'
            f'<circle cx="22" cy="22" r="20" fill="none" stroke="#E8EDF3" stroke-width="3"/>'
            f'<circle cx="22" cy="22" r="20" fill="none" stroke="{rc}" stroke-width="3"'
            f' stroke-dasharray="{dash:.1f} {circ:.1f}" stroke-linecap="round"'
            f' transform="rotate(-90 22 22)"/>'
            f'<text x="22" y="27" text-anchor="middle" fill="{rc}"'
            f' font-size="10" font-weight="700" font-family=\'Sora,sans-serif\'>{conf}</text></svg>')

    return f"""
<div class="card mb-2 border-0 card-match" data-tier="{tier}"
  data-comp="{_e(r.get('competicion',''))}"
  style="cursor:pointer"
  data-bs-toggle="offcanvas" data-bs-target="#{mid}">
  <div class="card-body p-3">
    <div class="d-flex align-items-center gap-3">
      
      <!-- Rank & Ring Minimal -->
      <div class="d-flex flex-column align-items-center" style="min-width:40px">
        <div class="text-muted fw-bold mb-1" style="font-size:10px; opacity:0.5">#{idx}</div>
        {ring}
      </div>

      <!-- Main Info -->
      <div class="flex-grow-1 min-width-0">
        <div class="d-flex align-items-center gap-2 mb-1">
          <span class="badge bg-warning">{tc['label']}</span>
          <span class="text-muted" style="font-size:11px; opacity:0.7">{comp}</span>
          <span class="ms-auto text-muted fw-semibold" style="font-size:11px">{hora}</span>
        </div>
        <div class="fw-black text-truncate" style="font-size:1.1rem; color:var(--premium-black)">{fav}</div>
        <div class="text-muted small text-truncate" style="font-size:12px">{eq}</div>
        
        <div class="d-flex flex-wrap gap-2 mt-2">
          {ai_badge}{elo_badge}{bp_badge}
          <span class="badge bg-light text-muted border-0" style="background:rgba(0,0,0,0.03)!important">{pick}</span>
        </div>
      </div>

      <!-- Prob Bars - Ultra Minimal -->
      <div class="d-none d-md-block" style="min-width:120px">
        <div class="d-flex flex-column gap-1">
          <div class="progress" style="height:2px!important">
            <div class="progress-bar" style="width:{p1w}%"></div>
          </div>
          <div class="progress" style="height:2px!important; opacity:0.3">
            <div class="progress-bar bg-secondary" style="width:{pxw}%"></div>
          </div>
          <div class="progress" style="height:2px!important">
            <div class="progress-bar" style="width:{p2w}%"></div>
          </div>
        </div>
        <div class="text-end mt-1" style="font-size:9px; opacity:0.5; letter-spacing:1px">+{margin} PTS VENTAXA</div>
      </div>

    </div>
  </div>
</div>
{_modal(r, idx)}"""


def _stat_card(val: Any, label: str, icon: str, color: str = "#92720A") -> str:
    return (f'<div class="col"><div class="card border-0 shadow-sm text-center py-3 px-2 h-100">'
            f'<i class="bi {icon} mb-2" style="font-size:1.4rem;color:{color}"></i>'
            f'<div class="fw-black mb-1" style="font-size:1.5rem;color:{color}">{val}</div>'
            f'<div class="text-uppercase text-muted" style="font-size:10px;letter-spacing:1px">{label}</div>'
            f'</div></div>')


def build(
    top: list[dict],
    stats: dict,
    output_path: "str | Path" = "index.html",
    creator_name: str = "DevOpsHB",
    creator_image: str = "creador.png",
    favicon: str = "favicon.ico",
) -> None:
    cards  = "".join(_card(i+1, r) for i, r in enumerate(top))
    comps  = sorted({r.get("competicion","") for r in top if r.get("competicion")})
    chips  = "".join(
        f'<button class="btn btn-sm btn-outline-secondary comp-chip rounded-pill" '
        f'data-comp="{_e(c)}">{_e(c)}</button>' for c in comps
    )
    today  = datetime.now().strftime("%d de %B %Y").capitalize()
    avg_c  = stats.get("avg_confidence",0)

    # Generamos el CSS de animaciones fuera del f-string para evitar conflictos con las llaves
    anim_css = ""
    for i in range(1, 22):
        anim_css += f".card-match:nth-child({i}){{animation-delay:{i*0.04:.2f}s}}\n"

    doc = f"""<!DOCTYPE html>
<html lang="es" data-bs-theme="light">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>SportAnalysis \u00b7 Top {len(top)} Picks</title>
<link rel="icon" href="{_e(favicon)}"/>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Sora:wght@300;400;600;700;800;900&family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
<link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css" rel="stylesheet">
<link rel="stylesheet" href="static/style.css">
<style>
{anim_css}
</style>
</head>
<body>

<!-- MODAL CREADOR -->
<div class="modal fade" id="creatorModal" tabindex="-1">
  <div class="modal-dialog modal-dialog-centered">
    <div class="modal-content border-0 shadow-lg">
      <div class="modal-body text-center p-5">
        <img src="{_e(creator_image)}" class="rounded-3 mb-3 shadow-sm"
          style="width:80px;height:80px;object-fit:cover;border:2px solid var(--gold)"
          onerror="this.style.display='none'">
        <div class="small fw-bold text-uppercase mb-1" style="letter-spacing:3px;color:var(--gold)">
          Desarrollado por
        </div>
        <h4 class="fw-black mb-2">{_e(creator_name)}</h4>
        <p class="text-muted small mb-4">
          Plataforma de análisis deportivo con scoring de confianza propio.<br>
          Datos: pronosticosfutbol365.com \u00b7 Club Elo \u00b7 BetPlay
        </p>
        <button type="button" class="btn btn-warning fw-bold px-4" data-bs-dismiss="modal" id="enterBtn">
          <i class="bi bi-play-fill me-1"></i>Ver análisis del día
        </button>
      </div>
    </div>
  </div>
</div>

<!-- NAVBAR -->
<nav class="navbar navbar-expand-lg sticky-top shadow-sm bg-white">
  <div class="container-xl">
    <a class="navbar-brand d-flex align-items-center gap-2" href="#">
      <div class="d-flex align-items-center justify-content-center rounded-2"
        style="width:36px;height:36px;background:linear-gradient(135deg,#B8960C,#7A5E08)">
        <i class="bi bi-trophy-fill text-white" style="font-size:1rem"></i>
      </div>
      <div>
        <div style="font-size:14px;line-height:1.1">SportAnalysis</div>
        <div class="text-muted fw-normal" style="font-size:10px">Intelligence Platform</div>
      </div>
    </a>
    <div class="ms-auto d-flex align-items-center gap-2">
      <span class="badge bg-success-subtle text-success-emphasis border border-success-subtle">
        <i class="bi bi-circle-fill me-1" style="font-size:6px"></i>Live
      </span>
      <span class="text-muted small d-none d-sm-inline">
        <i class="bi bi-calendar3 me-1"></i>{today}
      </span>
      <span class="badge bg-secondary-subtle text-secondary-emphasis border border-secondary-subtle small">
        <i class="bi bi-clock me-1"></i><span id="live-clock">--:--:--</span>
      </span>
    </div>
  </div>
</nav>

<!-- AVISO LEGAL -->
<div id="avisoLegal" style="
  position:fixed;inset:0;z-index:9999;
  display:flex;align-items:center;justify-content:center;
  background:rgba(0,0,0,0.75);backdrop-filter:blur(4px)">
  <div style="
    background:linear-gradient(160deg,#1a1a2e 0%,#16213e 100%);
    border:2px solid #B8960C;border-radius:20px;
    max-width:520px;width:90%;padding:40px 36px 32px;
    box-shadow:0 24px 80px rgba(0,0,0,0.6);
    text-align:center;position:relative">
    <div style="width:64px;height:64px;border-radius:50%;
      background:linear-gradient(135deg,#B8960C,#7A5E08);
      display:flex;align-items:center;justify-content:center;
      margin:0 auto 20px;box-shadow:0 8px 24px rgba(184,150,12,0.4)">
      <i class="bi bi-shield-exclamation" style="font-size:1.8rem;color:#fff"></i>
    </div>
    <div style="font-size:11px;letter-spacing:3px;color:#B8960C;font-weight:700;margin-bottom:8px;text-transform:uppercase">
      Aviso Importante
    </div>
    <h3 style="color:#fff;font-weight:900;font-size:1.4rem;margin-bottom:16px;line-height:1.3">
      Este sitio es solo para<br><span style="color:#B8960C">análisis estadístico</span>
    </h3>
    <p style="color:#aab4c8;font-size:13.5px;line-height:1.7;margin-bottom:24px">
      La información presentada <strong style="color:#fff">no constituye consejo, recomendación
      ni incitación a realizar apuestas</strong> de ningún tipo.<br><br>
      Las apuestas pueden generar <strong style="color:#e74c3c">adicción y pérdidas económicas graves.</strong>
      Si tienes problemas con el juego, busca ayuda profesional.
    </p>
    <div style="height:1px;background:linear-gradient(90deg,transparent,#B8960C,transparent);margin-bottom:24px"></div>
    <button onclick="document.getElementById('avisoLegal').style.display='none'"
      style="background:linear-gradient(135deg,#B8960C,#7A5E08);
        color:#fff;border:none;border-radius:50px;
        padding:12px 40px;font-size:14px;font-weight:700;
        cursor:pointer;letter-spacing:1px;text-transform:uppercase;
        box-shadow:0 4px 20px rgba(184,150,12,0.4)"
      onmouseover="this.style.transform='scale(1.05)'"
      onmouseout="this.style.transform='scale(1)'">
      <i class="bi bi-check-circle-fill me-2"></i>Entendido, continuar
    </button>
    <div style="margin-top:20px;color:#4a5568;font-size:11px">
      <i class="bi bi-code-slash me-1"></i>Desarrollado por <strong style="color:#6b7280">DevOpsHB</strong>
    </div>
  </div>
</div>

<!-- HERO -->
<section class="hero-section py-5">
  <div class="container-xl">
    <div class="row align-items-center">
      <div class="col-lg-7">
        <div class="small fw-bold text-uppercase mb-2" style="letter-spacing:3px;color:var(--gold)">
          <i class="bi bi-stars me-1"></i>Análisis del día
        </div>
        <h1 class="display-5 fw-black mb-3">
          Top <span style="color:var(--gold)">{len(top)}</span> Picks<br>del Día
        </h1>
        <p class="text-muted mb-4" style="max-width:480px">
          <strong>{stats.get('total_partidos',0)}</strong> partidos analizados de
          <strong>{stats.get('competiciones',0)}</strong> competiciones.
          Haz clic en cualquier pick para ver análisis completo.
        </p>
        <div class="d-flex flex-wrap gap-2">
          <span class="badge bg-warning-subtle text-warning-emphasis border border-warning-subtle px-3 py-2">
            <i class="bi bi-trophy-fill me-1"></i>{stats.get('elite',0)} Élite
          </span>
          <span class="badge bg-primary-subtle text-primary-emphasis border border-primary-subtle px-3 py-2">
            <i class="bi bi-graph-up-arrow me-1"></i>{stats.get('alta',0)} Alta
          </span>
          <span class="badge bg-success-subtle text-success-emphasis border border-success-subtle px-3 py-2">
            <i class="bi bi-gem me-1"></i>{stats.get('value_bets',0)} Value Bets
          </span>
          <span class="badge bg-info-subtle text-info-emphasis border border-info-subtle px-3 py-2">
            <i class="bi bi-speedometer2 me-1"></i>Conf. prom: {avg_c}%
          </span>
        </div>
      </div>
      <div class="col-lg-5 d-none d-lg-block">
        <div class="row g-3">
          {_stat_card(stats.get('total_partidos',0),"Partidos","bi-calendar-event","#1A5C96")}
          {_stat_card(stats.get('elite',0),"Élite","bi-trophy-fill","#92720A")}
          {_stat_card(stats.get('alta',0),"Alta","bi-graph-up-arrow","#1A5C96")}
          {_stat_card(stats.get('value_bets',0),"Value Bets","bi-gem","#92720A")}
          {_stat_card(f"{avg_c}%","Confianza","bi-speedometer2","#1A7A60")}
          {_stat_card(stats.get('competiciones',0),"Ligas","bi-globe","#6A7A8A")}
        </div>
      </div>
    </div>
  </div>
</section>

<!-- MAIN -->
<div class="container-xl py-4">
  <div class="d-flex align-items-center justify-content-between flex-wrap gap-3 mb-3">
    <div class="small fw-bold text-uppercase d-flex align-items-center gap-2" style="letter-spacing:2px;color:var(--gold)">
      <span style="display:inline-block;width:3px;height:16px;background:var(--gold);border-radius:2px"></span>
      Ranking de Picks
    </div>
    <div class="d-flex gap-2 flex-wrap" id="tier-btns">
      <button class="btn btn-sm btn-outline-secondary rounded-pill tier-btn active" data-t="ALL">
        <i class="bi bi-grid-3x3-gap me-1"></i>Todos
      </button>
      <button class="btn btn-sm btn-outline-warning rounded-pill tier-btn" data-t="ELITE">
        <i class="bi bi-trophy-fill me-1"></i>Élite
      </button>
      <button class="btn btn-sm btn-outline-primary rounded-pill tier-btn" data-t="ALTA">
        <i class="bi bi-graph-up-arrow me-1"></i>Alta
      </button>
      <button class="btn btn-sm btn-outline-secondary rounded-pill tier-btn" data-t="MEDIA">
        <i class="bi bi-dash-circle me-1"></i>Media
      </button>
    </div>
  </div>

  <div class="d-flex flex-wrap gap-2 mb-4" id="comp-chips">
    <button class="btn btn-sm btn-outline-secondary comp-chip rounded-pill active" data-comp="ALL">
      <i class="bi bi-globe me-1"></i>Todas las ligas
    </button>
    {chips}
  </div>

  <div id="cards">{cards}</div>

  <div id="empty-state" class="text-center py-5 d-none">
    <i class="bi bi-search display-3 text-muted"></i>
    <div class="text-muted mt-3">No hay picks para este filtro</div>
  </div>

  <div class="card border-0 shadow-sm mt-4">
    <div class="card-body">
      <div class="small fw-bold text-uppercase text-muted mb-3" style="letter-spacing:2px">Leyenda</div>
      <div class="row g-2 align-items-center">
        <div class="col-auto">
          <span class="badge bg-warning text-dark"><i class="bi bi-trophy-fill me-1"></i>ÉLITE</span>
          <span class="small text-muted ms-1">Confianza ≥ 65</span>
        </div>
        <div class="col-auto">
          <span class="badge bg-primary"><i class="bi bi-graph-up-arrow me-1"></i>ALTA</span>
          <span class="small text-muted ms-1">Confianza 50–64</span>
        </div>
        <div class="col-auto">
          <span class="badge bg-secondary"><i class="bi bi-dash-circle me-1"></i>MEDIA</span>
          <span class="small text-muted ms-1">Confianza 35–49</span>
        </div>
        <div class="col-auto">
          <span class="badge bg-warning text-dark"><i class="bi bi-gem me-1"></i>VALUE</span>
          <span class="small text-muted ms-1">Prob ≥ 50% y ventaja ≥ 15pts</span>
        </div>
        <div class="col-12">
          <small class="text-muted">
            <i class="bi bi-info-circle me-1"></i>
            Score = prob. victoria (60%) + margen sobre rival (40%) + claridad del pick (20%) ± Club Elo ± BetPlay
          </small>
        </div>
      </div>
    </div>
  </div>

  <footer class="d-flex justify-content-between flex-wrap gap-2 mt-4 pt-3 border-top small text-muted">
    <span>© {datetime.now().year} <strong>DevOpsHB</strong> \u00b7 Datos: pronosticosfutbol365.com \u00b7 clubelo.com</span>
    <span><i class="bi bi-code-slash me-1"></i>Desarrollado por DevOpsHB</span>
  </footer>
</div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
<script src="static/script.js"></script>
</body>
</html>"""
    Path(output_path).write_text(doc, encoding="utf-8")