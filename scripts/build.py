#!/usr/bin/env python3
"""
Monta o index.html a partir de templates/base.html + data/neugebauer.json.

Não faz nenhuma chamada de rede — só junta template + dados.
Quem busca dados novos no ClickUp é o sync_clickup.py (script separado).

Uso:
  python scripts/build.py
  python scripts/build.py --data data/neugebauer.json --out index.html
"""
import argparse
import base64
import html as html_lib
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")
DEFAULT_TEMPLATE = os.path.join(ROOT, "templates", "base.html")
DEFAULT_DATA = os.path.join(ROOT, "data", "neugebauer.json")
DEFAULT_OUT = os.path.join(ROOT, "index.html")

MONTHS_PT = ["jan", "fev", "mar", "abr", "mai", "jun",
             "jul", "ago", "set", "out", "nov", "dez"]

# Normaliza os nomes de status do ClickUp (vindos do JSON) para as 4
# categorias visuais do painel. Ver README > "Vocabulário de status".
STATUS_RULES = [
    (("complete", "concluido", "concluído", "done"), "done", "Concluído"),
    (("em andamento", "in progress", "andamento"), "progress", "Em andamento"),
    (("bloqueio/impeditivo", "bloqueio", "impeditivo", "bloqueado", "blocked"), "blocked", "Bloqueado"),
    (("aguardando cliente", "aguardando", "waiting"), "wait", "Aguardando cliente"),
    (("to do", "pendente", "open", "backlog", "não iniciado", "nao iniciado"), "todo", "Não iniciado"),
]


def classify_status(status_name):
    """Retorna (classe_css, rotulo, reconhecido)."""
    key = (status_name or "").strip().lower()
    for keywords, css_class, label in STATUS_RULES:
        if key in keywords:
            return css_class, label, True
    # Status não mapeado: NUNCA finge que é "não iniciado" -- isso já
    # causou dado zerado por engano no passado. Mostra como está, mas
    # sinaliza visualmente (classe "unknown") para chamar atenção.
    return "unknown", (status_name or "Status desconhecido").strip().title(), False


def esc(text):
    return html_lib.escape(text or "", quote=True)


def render_activity_row(task):
    css_class, label, _ = classify_status(task["status"])
    name = esc(task["name"])
    done_class = " done" if css_class == "done" else ""
    return (
        f'          <div class="activity{done_class}">'
        f'<span class="aleft"><span class="dot {css_class}"></span>'
        f'<span class="aname">{name}</span></span>'
        f'<span class="astatus">{esc(label)}</span></div>'
    )


def render_subphase(sp):
    css_class, label, _ = classify_status(sp["status"])
    name = esc(sp["name"])
    kids = sp.get("activities", [])

    if kids:
        done = sum(1 for k in kids if classify_status(k["status"])[0] == "done")
        progress = sum(1 for k in kids if classify_status(k["status"])[0] == "progress")
        total = len(kids)
        if css_class == "done":
            count_text = f"{done}/{total} concluídas"
        elif "onda" in sp["name"].lower():
            count_text = f"{total} ondas"
        elif done and not progress:
            count_text = f"{done} de {total} concluída" + ("s" if done > 1 else "")
        elif done and progress:
            count_text = f"{done} concluídas · {progress} em andamento"
        elif progress:
            count_text = f"{progress} de {total} em andamento"
        else:
            count_text = f"{total} atividades"
        activities_html = "\n".join(render_activity_row(k) for k in kids)
    else:
        count_text = label
        activities_html = ""

    return f'''      <details class="subphase">
        <summary>
          <span class="sleft"><span class="chev">&#9656;</span><span class="sname">{name}</span></span>
          <span class="right"><span class="count">{esc(count_text)}</span><span class="badge b-{css_class}">{esc(label)}</span></span>
        </summary>
        <div class="activities">
{activities_html}
        </div>
      </details>'''


def render_phase(phase, is_current):
    css_class, label, _ = classify_status(phase["status"])
    name = esc(phase["name"])
    desc = esc(phase.get("descricao", ""))
    current_class = " current" if is_current else ""
    subphases_html = "\n\n".join(render_subphase(sp) for sp in phase.get("subphases", []))

    return f'''    <!-- Fase {phase["num"]} -->
    <div class="phase{current_class}">
      <div class="phase-head">
        <div>
          <p class="name"><span class="num">{phase["num"]:02d}</span>{name}</p>
          <p class="desc">{desc}</p>
        </div>
        <span class="badge b-{css_class}">{esc(label)}</span>
      </div>

{subphases_html}
    </div>'''


def render_alerts(alerts):
    if not alerts:
        return ""
    items = []
    for a in alerts:
        name = esc(a["name"])
        children = a.get("children", [])
        if children:
            child_names = "; ".join(esc(c["name"]) for c in children)
            items.append(f'<li><strong>{name}</strong> — {child_names}</li>')
        else:
            items.append(f'<li><strong>{name}</strong></li>')
    items_html = "\n          ".join(items)
    plural = "s" if len(alerts) > 1 else ""
    return f'''    <div class="alert-banner" role="alert">
      <div class="alert-head">
        <span class="alert-dot"></span>
        <span class="alert-title">Bloqueio{plural} / impeditivo{plural} identificado{plural}</span>
      </div>
      <ul class="alert-list">
          {items_html}
      </ul>
    </div>

'''


def render_metrics(phases):
    total_phases = len(phases)
    active_phase_nums = [p["num"] for p in phases if classify_status(p["status"])[0] == "progress"]
    if active_phase_nums:
        lo, hi = min(active_phase_nums), max(active_phase_nums)
        current_label = f"{lo}" if lo == hi else f"{lo}\u2013{hi}"
    else:
        # nenhuma fase em andamento: mostra a primeira ainda não concluída
        not_done = next((p["num"] for p in phases if classify_status(p["status"])[0] != "done"), total_phases)
        current_label = str(not_done)

    all_subphases = [sp for p in phases for sp in p.get("subphases", [])]
    done = sum(1 for s in all_subphases if classify_status(s["status"])[0] == "done")
    progress = sum(1 for s in all_subphases if classify_status(s["status"])[0] == "progress")
    total = len(all_subphases)
    todo = total - done - progress

    # progresso geral: subfase concluída conta 1, em andamento conta 0.5
    pct = round(((done * 1.0) + (progress * 0.5)) / total * 100) if total else 0
    circumference = 2 * 3.14159265 * 26
    dash = round(circumference * pct / 100, 1)

    value_style = ' style="font-size:22px;"' if "\u2013" in current_label else ""

    metrics_html = f'''    <div class="metrics">
      <div class="metric metric-ring">
        <p class="label">Progresso geral</p>
        <div class="ring-wrap">
          <svg viewBox="0 0 64 64" class="progress-ring">
            <circle cx="32" cy="32" r="26" class="ring-bg"></circle>
            <circle cx="32" cy="32" r="26" class="ring-fill" style="stroke-dasharray:{dash} {circumference:.1f}"></circle>
          </svg>
          <span class="ring-percent">{pct}%</span>
        </div>
      </div>
      <div class="metric">
        <p class="label">Fase atual</p>
        <p class="value"{value_style}>{current_label} <small>de {total_phases}</small></p>
      </div>
      <div class="metric">
        <p class="label">Subfases concluídas</p>
        <p class="value">{done} <small>de {total}</small></p>
      </div>
      <div class="metric">
        <p class="label">Subfases em andamento</p>
        <p class="value" style="color:var(--cyan);">{progress}</p>
      </div>
      <div class="metric">
        <p class="label">Subfases não iniciadas</p>
        <p class="value">{todo}</p>
      </div>
    </div>'''
    return metrics_html, active_phase_nums


def render_journey(phases, active_phase_nums):
    stops = []
    for p in phases:
        css_class = classify_status(p["status"])[0]
        if css_class == "done":
            state = "done"
        elif p["num"] in active_phase_nums:
            state = "active"
        else:
            state = ""
        cls = f" {state}" if state else ""
        # extrai o rótulo curto após o travessão do nome da fase, se houver
        label = p["name"].split("—", 1)[-1].strip() if "—" in p["name"] else p["name"]
        stops.append(
            f'        <div class="stop{cls}"><div class="ring">{p["num"]}</div>'
            f'<div class="name">{esc(label)}</div></div>'
        )
    return "\n" + "\n".join(stops) + "\n      "


def b64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")


def build(template_path=DEFAULT_TEMPLATE, data_path=DEFAULT_DATA, out_path=DEFAULT_OUT):
    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    phases = data["phases"]
    meta = data["meta"]

    alerts_html = render_alerts(data.get("alerts", []))
    metrics_html, active_phase_nums = render_metrics(phases)
    journey_html = render_journey(phases, active_phase_nums)
    phases_html = "\n\n".join(render_phase(p, p["num"] in active_phase_nums) for p in phases)

    last_synced = data.get("last_synced")
    import datetime
    BRT = datetime.timezone(datetime.timedelta(hours=-3))
    if last_synced:
        dt = datetime.datetime.fromisoformat(last_synced.replace("Z", "+00:00")).astimezone(BRT)
    else:
        dt = datetime.datetime.now(BRT)
    generated_date = f"{dt.day} {MONTHS_PT[dt.month - 1]}. {dt.year} \u00e0s {dt.hour:02d}:{dt.minute:02d}"
    sync_date_long = f"{dt.day:02d} de {MONTHS_PT[dt.month - 1]}. de {dt.year}"
    sync_datetime_short = f"{dt.day:02d}/{dt.month:02d}/{dt.year}, {dt.hour:02d}:{dt.minute:02d}"

    with open(template_path, "r", encoding="utf-8") as f:
        template = f.read()

    output = (
        template
        .replace("{{FAVICON_B64}}", b64(os.path.join(ASSETS, "favicon.png")))
        .replace("{{BINARIO_LOGO_B64}}", b64(os.path.join(ASSETS, "binario-cloud-logo.png")))
        .replace("{{NEUGEBAUER_LOGO_B64}}", b64(os.path.join(ASSETS, "neugebauer-logo.png")))
        .replace("{{GENERATED_DATE}}", generated_date)
        .replace("{{SYNC_DATE_LONG}}", sync_date_long)
        .replace("{{SYNC_DATETIME_SHORT}}", sync_datetime_short)
        .replace("{{LOGIN_USERS_JSON}}", json.dumps(meta["login"]["users"], ensure_ascii=False))
        .replace("{{ALERTS_HTML}}", alerts_html)
        .replace("{{METRICS_HTML}}", metrics_html)
        .replace("{{JOURNEY_HTML}}", journey_html)
        .replace("{{PHASES_HTML}}", phases_html)
    )

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(output)

    n_sub = sum(len(p.get("subphases", [])) for p in phases)
    n_act = sum(len(s.get("activities", [])) for p in phases for s in p.get("subphases", []))
    print(f"OK: {out_path} gerado ({len(phases)} fases, {n_sub} subfases, {n_act} atividades)")
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--template", default=DEFAULT_TEMPLATE)
    parser.add_argument("--data", default=DEFAULT_DATA)
    parser.add_argument("--out", default=DEFAULT_OUT)
    args = parser.parse_args()
    build(args.template, args.data, args.out)
