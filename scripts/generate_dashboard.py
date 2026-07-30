#!/usr/bin/env python3
"""
Gera o painel executivo (index.html) do projeto Neugebauer a partir
dos dados reais da lista do ClickUp.

Requer as variáveis de ambiente:
  CLICKUP_TOKEN    - token de API pessoal do ClickUp
  CLICKUP_LIST_ID  - id da lista (default: 901328018187)

Uso:
  python scripts/generate_dashboard.py
"""
import os
import sys
import base64
import datetime
import html as html_lib
from collections import defaultdict

import requests

CLICKUP_TOKEN = os.environ.get("CLICKUP_TOKEN")
LIST_ID = os.environ.get("CLICKUP_LIST_ID", "901328018187")
API_BASE = "https://api.clickup.com/api/v2"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "assets")
TEMPLATE_PATH = os.path.join(ROOT, "templates", "base.html")
OUTPUT_PATH = os.path.join(ROOT, "index.html")

MONTHS_PT = ["jan", "fev", "mar", "abr", "mai", "jun",
             "jul", "ago", "set", "out", "nov", "dez"]

PHASE_DESCRIPTIONS = {
    1: "Formalização, refinamento técnico e planejamento do cronograma",
    2: "Ambiente Binário Cloud: rede, firewall, VMs, backup e monitoramento",
    3: "Estratégia, piloto e ondas de migração dos servidores",
    4: "Testes finais, virada de chave e estabilização pós go-live",
    5: "Transição para operação (CCOE) e encerramento formal do projeto",
}

JOURNEY_LABELS = [
    "Iniciação e<br>planejamento",
    "Preparação e<br>implementação",
    "Migração",
    "Go-live e<br>estabilização",
    "Encerramento e<br>transição",
]

# Normaliza os nomes de status do ClickUp para as 4 categorias visuais do painel.
STATUS_RULES = [
    (("complete", "concluido", "concluído", "done"), "done", "Concluído"),
    (("em andamento", "in progress", "andamento"), "progress", "Em andamento"),
    (("aguardando cliente", "aguardando", "waiting", "blocked"), "wait", "Aguardando cliente"),
    (("to do", "pendente", "open", "backlog", "não iniciado", "nao iniciado"), "todo", "Não iniciado"),
]


def classify_status(status_name):
    key = (status_name or "").strip().lower()
    for keywords, css_class, label in STATUS_RULES:
        if key in keywords:
            return css_class, label
    # fallback: mantém o nome original do ClickUp, tratado como "todo"
    return "todo", status_name.strip().title() if status_name else "Não iniciado"


def fetch_all_tasks():
    if not CLICKUP_TOKEN:
        print("ERRO: variável de ambiente CLICKUP_TOKEN não definida.", file=sys.stderr)
        sys.exit(1)

    headers = {"Authorization": CLICKUP_TOKEN}
    tasks = []
    page = 0
    while True:
        resp = requests.get(
            f"{API_BASE}/list/{LIST_ID}/task",
            headers=headers,
            params={
                "subtasks": "true",
                "include_closed": "true",
                "page": page,
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        batch = data.get("tasks", [])
        if not batch:
            break
        tasks.extend(batch)
        if data.get("last_page", True):
            break
        page += 1
    return tasks


def build_tree(tasks):
    children = defaultdict(list)
    for t in tasks:
        children[t.get("parent")].append(t)
    for k in children:
        children[k].sort(key=lambda t: float(t.get("orderindex", 0) or 0))
    roots = children.get(None, [])
    return roots, children


def esc(text):
    return html_lib.escape(text or "", quote=True)


def render_activity_row(task, ondas_mode=False):
    css_class, label = classify_status(task["status"]["status"])
    name = esc(task["name"])
    if ondas_mode:
        sub_count = task.get("subtask_count")
        status_text = f"{sub_count} atividades" if sub_count else label
    else:
        status_text = label
    done_class = " done" if css_class == "done" else ""
    return (
        f'          <div class="activity{done_class}">'
        f'<span class="aleft"><span class="dot {css_class}"></span>'
        f'<span class="aname">{name}</span></span>'
        f'<span class="astatus">{esc(status_text)}</span></div>'
    )


def render_subphase(index_label, task, children_map):
    css_class, label = classify_status(task["status"]["status"])
    kids = children_map.get(task["id"], [])
    name = esc(task["name"])

    if kids:
        done = sum(1 for k in kids if classify_status(k["status"]["status"])[0] == "done")
        progress = sum(1 for k in kids if classify_status(k["status"]["status"])[0] == "progress")
        total = len(kids)
        if css_class == "done":
            count_text = f"{done}/{total} concluídas"
        elif progress:
            count_text = f"{progress} de {total} em andamento"
        else:
            count_text = f"{total} atividades" if "onda" not in task["name"].lower() else f"{total} ondas"

        # Detecta um 4º nível (ex.: "ondas" que por sua vez têm subtarefas)
        ondas_mode = any(children_map.get(k["id"]) for k in kids)
        activities_html = "\n".join(render_activity_row(k, ondas_mode=ondas_mode) for k in kids)
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


def render_phase(phase_num, task, children_map):
    css_class, label = classify_status(task["status"]["status"])
    name = esc(task["name"])
    desc = esc(PHASE_DESCRIPTIONS.get(phase_num, ""))
    current_class = " current" if css_class == "progress" else ""
    subphases = children_map.get(task["id"], [])
    subphases_html = "\n\n".join(render_subphase(i, sp, children_map) for i, sp in enumerate(subphases, start=1))

    return f'''    <!-- Fase {phase_num} -->
    <div class="phase{current_class}">
      <div class="phase-head">
        <div>
          <p class="name"><span class="num">{phase_num:02d}</span>{name}</p>
          <p class="desc">{desc}</p>
        </div>
        <span class="badge b-{css_class}">{esc(label)}</span>
      </div>

{subphases_html}
    </div>'''


def render_metrics(phases, children_map):
    total_phases = len(phases)
    current_phase_idx = next(
        (i for i, p in enumerate(phases, start=1) if classify_status(p["status"]["status"])[0] != "done"),
        total_phases,
    )

    all_subphases = []
    for p in phases:
        all_subphases.extend(children_map.get(p["id"], []))

    done = sum(1 for s in all_subphases if classify_status(s["status"]["status"])[0] == "done")
    progress = sum(1 for s in all_subphases if classify_status(s["status"]["status"])[0] == "progress")
    total = len(all_subphases)
    todo = total - done - progress

    return f'''    <div class="metrics">
      <div class="metric">
        <p class="label">Fase atual</p>
        <p class="value">{current_phase_idx} <small>de {total_phases}</small></p>
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
    </div>''', current_phase_idx


def render_journey(phases, current_phase_idx):
    stops = []
    for i, label in enumerate(JOURNEY_LABELS, start=1):
        phase = phases[i - 1] if i - 1 < len(phases) else None
        css_class = classify_status(phase["status"]["status"])[0] if phase else "todo"
        if css_class == "done":
            state = "done"
        elif i == current_phase_idx:
            state = "active"
        else:
            state = ""
        stops.append(
            f'        <div class="stop{(" " + state) if state else ""}"><div class="ring">{i}</div>'
            f'<div class="name">{label}</div></div>'
        )
    return "\n" + "\n".join(stops) + "\n      "


def b64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")


def main():
    tasks = fetch_all_tasks()
    if not tasks:
        print("ERRO: nenhuma tarefa retornada pelo ClickUp.", file=sys.stderr)
        sys.exit(1)

    roots, children_map = build_tree(tasks)
    roots.sort(key=lambda t: float(t.get("orderindex", 0) or 0))

    phases_html = "\n\n".join(
        render_phase(i, t, children_map) for i, t in enumerate(roots, start=1)
    )
    metrics_html, current_phase_idx = render_metrics(roots, children_map)
    journey_html = render_journey(roots, current_phase_idx)

    today = datetime.datetime.now()
    generated_date = f"{today.day} {MONTHS_PT[today.month - 1]}. {today.year}"

    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        template = f.read()

    output = (
        template
        .replace("{{FAVICON_B64}}", b64(os.path.join(ASSETS, "favicon.png")))
        .replace("{{BINARIO_LOGO_B64}}", b64(os.path.join(ASSETS, "binario-cloud-logo.png")))
        .replace("{{NEUGEBAUER_LOGO_B64}}", b64(os.path.join(ASSETS, "neugebauer-logo.png")))
        .replace("{{GENERATED_DATE}}", generated_date)
        .replace("{{METRICS_HTML}}", metrics_html)
        .replace("{{JOURNEY_HTML}}", journey_html)
        .replace("{{PHASES_HTML}}", phases_html)
    )

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(output)

    print(f"OK: index.html gerado com {len(roots)} fases e {len(tasks)} tarefas no total.")


if __name__ == "__main__":
    main()
