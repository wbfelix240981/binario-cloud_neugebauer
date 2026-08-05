#!/usr/bin/env python3
"""
Sincroniza data/neugebauer.json com o estado atual do ClickUp.

Regra de preservação (igual ao padrão usado no projeto Metas):
- Campos CURADOS à mão (descricao, num, meta.* incl. login) NUNCA são
  sobrescritos por este script.
- Campos DINÂMICOS (name, status, assignee, due_date, e a lista de
  filhos) são sempre substituídos pelo estado atual do ClickUp.
- O casamento entre um nó existente no JSON e uma tarefa do ClickUp é
  feito por "id"; se um nó do JSON ainda não tem id do ClickUp (ex.:
  seed inicial), casa por nome no mesmo nível -- e a partir daí passa
  a guardar o id real, tornando as sincronizações seguintes mais
  robustas a renomeações.

Variáveis de ambiente:
  CLICKUP_TOKEN    - token de API pessoal do ClickUp (obrigatório)
  CLICKUP_LIST_ID  - id da lista (default: 901328018187)
  DATA_PATH        - caminho do JSON (default: data/neugebauer.json)

Uso:
  python scripts/sync_clickup.py
"""
import datetime
import json
import os
import sys
from collections import defaultdict

import requests

CLICKUP_TOKEN = os.environ.get("CLICKUP_TOKEN")
LIST_ID = os.environ.get("CLICKUP_LIST_ID", "901328018187")
DATA_PATH = os.environ.get("DATA_PATH", os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "neugebauer.json"
))
API_BASE = "https://api.clickup.com/api/v2"

# Vocabulário de status conhecido nesta lista (ver README > "Vocabulário
# de status" -- IMPORTANTE checar isso de novo se algum dia adicionarmos
# outra lista/pessoa, porque já causou um bug real de dado zerado por
# assumir o vocabulário errado numa lista com nomes customizados).
KNOWN_STATUSES = {
    "complete", "to do", "em andamento", "pendente", "aguardando cliente",
    "bloqueio/impeditivo",
}

# Status que, quando aparecem numa tarefa RAIZ (sem pai) que não é uma das
# 5 fases já conhecidas, indicam que é um alerta de bloqueio -- não uma
# fase nova de verdade. Esses vão para data["alerts"], não para
# data["phases"], e aparecem como banner piscando em vermelho no painel.
BLOCKER_STATUSES = {"bloqueio/impeditivo"}


def fetch_all_tasks_flat(list_id, token):
    """Busca todas as tarefas da lista (formato plano, com subtarefas)."""
    headers = {"Authorization": token}
    all_tasks = []
    page = 0
    while True:
        resp = requests.get(
            f"{API_BASE}/list/{list_id}/task",
            headers=headers,
            params={"subtasks": "true", "include_closed": "true", "page": page},
            timeout=30,
        )
        resp.raise_for_status()
        payload = resp.json()
        batch = payload.get("tasks", [])
        if not batch:
            break
        all_tasks.extend(batch)
        if payload.get("last_page", True):
            break
        page += 1
    return all_tasks


def build_clickup_tree(tasks):
    """Reconstroi a árvore fase > subfase > atividade a partir da lista
    plana de tarefas do ClickUp (usa o campo 'parent')."""
    children = defaultdict(list)
    for t in tasks:
        children[t.get("parent")].append(t)
    for k in children:
        children[k].sort(key=lambda t: float(t.get("orderindex", 0) or 0))
    roots = children.get(None, [])
    roots.sort(key=lambda t: float(t.get("orderindex", 0) or 0))
    return roots, children


def task_to_dynamic(task):
    assignees = task.get("assignees") or []
    assignee_name = assignees[0]["username"] if assignees else None
    due = task.get("due_date")
    due_iso = None
    if due:
        try:
            due_iso = datetime.datetime.utcfromtimestamp(int(due) / 1000).date().isoformat()
        except (ValueError, TypeError):
            due_iso = None
    return {
        "id": task["id"],
        "name": task["name"],
        "status": task["status"]["status"],
        "assignee": assignee_name,
        "due_date": due_iso,
    }


def merge_activity(existing, incoming_task, warnings):
    """Atividade-folha: não tem filhos, só campos dinâmicos + id."""
    dyn = task_to_dynamic(incoming_task)
    status_key = dyn["status"].strip().lower()
    if status_key not in KNOWN_STATUSES:
        warnings.append(
            f"status desconhecido '{dyn['status']}' na atividade '{dyn['name']}' "
            f"(id {dyn['id']}) -- verifique o vocabulário de status desta lista"
        )
    if existing is None:
        return dyn
    merged = dict(existing)
    merged.update(dyn)  # sobrescreve só as chaves dinâmicas (id/name/status/assignee/due_date)
    return merged


def sync(data, tasks, warnings):
    roots, children_map = build_clickup_tree(tasks)
    by_id = {t["id"]: t for t in tasks}

    existing_phases_by_id = {p["id"]: p for p in data["phases"] if p.get("id")}
    existing_phases_by_name = {p["name"]: p for p in data["phases"] if not p.get("id")}

    # Separa: raízes que já são fases conhecidas (ou vão virar fase nova de
    # verdade) das raízes que são só alertas de bloqueio soltos na lista
    # (ex.: tarefa tipo "Fase" chamada "Bloqueio", criada à parte pelo time
    # pra sinalizar um impeditivo -- não faz parte da jornada do projeto).
    phase_roots = []
    blocker_roots = []
    for root_task in roots:
        is_known_phase = root_task["id"] in existing_phases_by_id or root_task["name"] in existing_phases_by_name
        status_key = (root_task["status"]["status"] or "").strip().lower()
        if not is_known_phase and status_key in BLOCKER_STATUSES:
            blocker_roots.append(root_task)
        else:
            phase_roots.append(root_task)

    alerts = []
    for blocker_task in blocker_roots:
        dyn = task_to_dynamic(blocker_task)
        children = [task_to_dynamic(c) for c in children_map.get(blocker_task["id"], [])]
        alerts.append({**dyn, "children": children})
        warnings.append(f"ALERTA: bloqueio/impeditivo encontrado -- '{dyn['name']}'")
    data["alerts"] = alerts

    new_phases = []
    for i, root_task in enumerate(phase_roots, start=1):
        existing_phase = existing_phases_by_id.get(root_task["id"]) or existing_phases_by_name.get(root_task["name"])
        dyn = task_to_dynamic(root_task)
        status_key = dyn["status"].strip().lower()
        if status_key not in KNOWN_STATUSES:
            warnings.append(f"status desconhecido '{dyn['status']}' na fase '{dyn['name']}'")

        if existing_phase is None:
            warnings.append(f"NOVA fase encontrada no ClickUp sem entrada curada: '{dyn['name']}' -- "
                             f"adicione 'descricao' manualmente em data/neugebauer.json")
            phase = dict(dyn)
            phase["num"] = i
            phase["descricao"] = ""
            phase["subphases"] = []
        else:
            phase = dict(existing_phase)
            phase.update(dyn)  # preserva 'descricao' e 'num' (não estão em dyn)

        # subfases
        sub_tasks = children_map.get(root_task["id"], [])
        existing_subs = existing_phase.get("subphases", []) if existing_phase else []
        existing_subs_by_id = {s["id"]: s for s in existing_subs if s.get("id")}
        existing_subs_by_name = {s["name"]: s for s in existing_subs if not s.get("id")}

        new_subs = []
        for sub_task in sub_tasks:
            existing_sub = existing_subs_by_id.get(sub_task["id"]) or existing_subs_by_name.get(sub_task["name"])
            dyn_sub = task_to_dynamic(sub_task)
            status_key = dyn_sub["status"].strip().lower()
            if status_key not in KNOWN_STATUSES:
                warnings.append(f"status desconhecido '{dyn_sub['status']}' na subfase '{dyn_sub['name']}'")

            sub = dict(existing_sub) if existing_sub else {}
            sub.update(dyn_sub)

            # atividades (folhas)
            act_tasks = children_map.get(sub_task["id"], [])
            existing_acts = existing_sub.get("activities", []) if existing_sub else []
            existing_acts_by_id = {a["id"]: a for a in existing_acts if a.get("id")}
            existing_acts_by_name = {a["name"]: a for a in existing_acts if not a.get("id")}

            new_acts = []
            for act_task in act_tasks:
                existing_act = existing_acts_by_id.get(act_task["id"]) or existing_acts_by_name.get(act_task["name"])
                new_acts.append(merge_activity(existing_act, act_task, warnings))

            sub["activities"] = new_acts
            new_subs.append(sub)

        phase["subphases"] = new_subs
        new_phases.append(phase)

    data["phases"] = new_phases
    data["last_synced"] = datetime.datetime.utcnow().isoformat() + "Z"
    return data


def main():
    if not CLICKUP_TOKEN:
        print("ERRO: variável de ambiente CLICKUP_TOKEN não definida.", file=sys.stderr)
        sys.exit(1)

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    tasks = fetch_all_tasks_flat(LIST_ID, CLICKUP_TOKEN)
    if not tasks:
        print("ERRO: nenhuma tarefa retornada pelo ClickUp -- abortando sem tocar no JSON.", file=sys.stderr)
        sys.exit(1)

    warnings = []
    before = json.dumps(data, sort_keys=True)
    data = sync(data, tasks, warnings)
    after = json.dumps(data, sort_keys=True)

    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")

    for w in warnings:
        print(f"AVISO: {w}", file=sys.stderr)

    changed = before != after
    print(f"Sincronização concluída. Mudou algo além do timestamp: {changed}")
    return changed


if __name__ == "__main__":
    main()
