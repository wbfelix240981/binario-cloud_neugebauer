#!/usr/bin/env python3
"""
Sincroniza data/neugebauer.json com o estado atual do ClickUp.

O QUE É PRESERVADO (curado à mão, o sync NUNCA sobrescreve)
-----------------------------------------------------------
  metas[]: num, name, short, detail, tags
  metas[].fases[].ativ[]: original_due  (data-base do prazo; se fosse
      atualizada junto com a "due", o cálculo de atraso zerava sozinho
      toda vez que alguém empurrasse o prazo no ClickUp)
  gantt[]: metaNum, name, start, e a SELEÇÃO de children -- o Gantt é
      uma visão curada (mostra um subconjunto escolhido a mão, com datas
      de início definidas manualmente, porque o ClickUp não tem start
      date confiável em todas as tarefas)
  login.users

O QUE É ATUALIZADO (vem do ClickUp)
-----------------------------------
  status, due, assignee, e a árvore fases/ativ dentro de metas.

DOIS VOCABULÁRIOS DE STATUS
---------------------------
Este painel usa dois conjuntos de status ao mesmo tempo:

  1. Visão "Metas" (RAFAEL_METAS) usa status NORMALIZADOS em inglês:
     backlog / in planning / in progress / in test / in review /
     blocked / shipped
  2. Visão "RoadMap/Gantt" (GANTT_TASKS) usa os status CRUS do ClickUp,
     em português: aberto / em andamento / fechado / aguardando retorno
     / bloqueada / concluído / ...

Por isso existe o STATUS_MAP abaixo. Um status do ClickUp que não
estiver mapeado NÃO vira "backlog" silenciosamente -- ele gera aviso e
recebe a marcação 'blocked' (visível, vermelha), justamente para não
repetir o bug de "lista aparecer zerada" por vocabulário errado.

Variáveis de ambiente:
  CLICKUP_TOKEN    (obrigatório)
  CLICKUP_LIST_ID  (default 901328018187)
"""
import datetime
import json
import os
import re
import sys
import time
from collections import defaultdict

import requests

CLICKUP_TOKEN = os.environ.get("CLICKUP_TOKEN")
LIST_ID = os.environ.get("CLICKUP_LIST_ID", "901328018187")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.environ.get("DATA_PATH", os.path.join(ROOT, "data", "neugebauer.json"))
API_BASE = "https://api.clickup.com/api/v2"

# ClickUp (cru, minúsculo) -> status normalizado da visão "Metas".
# Conferido contra a lista real em 27/08/2026.
STATUS_MAP = {
    "aberto": "backlog",
    "backlog": "backlog",
    "to do": "backlog",
    "em andamento": "in progress",
    "in progress": "in progress",
    "revisando": "in review",
    "aguardando retorno": "in review",
    "aguardando cliente": "in review",
    "em teste": "in test",
    "bloqueada": "blocked",
    "bloqueado": "blocked",
    "impedimento": "blocked",
    "bloqueio/impeditivo": "blocked",
    "rejeitada": "blocked",
    "fechado": "shipped",
    "concluído": "shipped",
    "concluido": "shipped",
    "entregue": "shipped",
    "complete": "shipped",
}

# Status crus que o Gantt sabe colorir (ROADMAP_STATUS_META no template).
GANTT_KNOWN = {
    "aberto", "em andamento", "revisando", "rejeitada", "aguardando retorno",
    "impedimento", "entregue", "fechado", "bloqueada", "concluído",
}


def norm(s):
    return (s or "").strip().lower()


def to_normalized(raw_status, contexto, warnings):
    key = norm(raw_status)
    if key in STATUS_MAP:
        return STATUS_MAP[key]
    warnings.append(
        f"status do ClickUp NÃO MAPEADO: '{raw_status}' (em {contexto}). "
        f"Marcado como 'blocked' para ficar visível -- adicione ao STATUS_MAP."
    )
    return "blocked"


def check_gantt_status(raw_status, contexto, warnings):
    key = norm(raw_status)
    if key not in GANTT_KNOWN:
        warnings.append(
            f"status '{raw_status}' (em {contexto}) não existe no ROADMAP_STATUS_META "
            f"do template -- a barra do Gantt sairá sem cor. Adicione lá."
        )
    return key


def fetch_all_tasks(list_id, token):
    headers = {"Authorization": token}
    tasks, page = [], 0
    while True:
        payload = None
        for attempt in range(1, 4):
            try:
                r = requests.get(
                    f"{API_BASE}/list/{list_id}/task",
                    headers=headers,
                    params={"subtasks": "true", "include_closed": "true", "page": page},
                    timeout=60,
                )
                if r.status_code == 429:
                    wait = int(r.headers.get("Retry-After", 5 * attempt))
                    print(f"AVISO: rate limit (429), esperando {wait}s...", file=sys.stderr)
                    time.sleep(wait)
                    continue
                r.raise_for_status()
                payload = r.json()
                break
            except requests.exceptions.RequestException as e:
                print(f"AVISO: falha na página {page} (tentativa {attempt}/3): {e}", file=sys.stderr)
                time.sleep(5 * attempt)
        if payload is None:
            print(f"ERRO: não foi possível buscar a página {page} após 3 tentativas.", file=sys.stderr)
            sys.exit(1)
        batch = payload.get("tasks", [])
        if not batch:
            break
        tasks.extend(batch)
        if payload.get("last_page", True):
            break
        page += 1
    return tasks


def build_tree(tasks):
    children = defaultdict(list)
    for t in tasks:
        children[t.get("parent")].append(t)
    for k in children:
        children[k].sort(key=lambda t: float(t.get("orderindex", 0) or 0))
    return children


def assignee_of(task):
    a = task.get("assignees") or []
    return a[0]["username"] if a else ""


def due_of(task):
    d = task.get("due_date")
    return int(d) if d else None


def phase_sort_key(meta):
    return meta.get("num", 999)


def sub_sort_key(name):
    m = re.match(r"^(\d+)\.(\d+)", (name or "").strip())
    return (int(m.group(1)), int(m.group(2))) if m else (999, 999)


def sync(data, tasks, warnings):
    children = build_tree(tasks)
    by_id = {t["id"]: t for t in tasks}
    roots = children.get(None, [])

    # ---------- visão METAS ----------
    existing_by_id = {m["id"]: m for m in data["metas"] if m.get("id")}
    # Tarefas soltas na raiz da lista que NÃO são fases do projeto
    # (ex.: avisos de bloqueio criados à parte). Ficam de fora da visão
    # Metas para não virarem uma "Fase 6" fantasma.
    ignorar = set(data.get("ignore_root_ids", []))
    new_metas = []
    for root in roots:
        if root["id"] in ignorar:
            continue
        cur = existing_by_id.get(root["id"])
        if cur is None:
            # fase nova no ClickUp que ainda não foi curada -- entra com os
            # campos curados vazios e avisa, em vez de inventar texto.
            warnings.append(
                f"NOVA fase no ClickUp sem curadoria: '{root['name']}' (id {root['id']}). "
                f"Preencha 'name', 'short', 'detail' e 'num' em data/neugebauer.json."
            )
            cur = {"id": root["id"], "num": 999, "name": root["name"],
                   "short": root["name"], "detail": "", "tags": []}

        meta = dict(cur)  # preserva num, name, short, detail, tags
        meta["status"] = to_normalized(root["status"]["status"], f"fase '{root['name']}'", warnings)
        meta["due"] = due_of(root)
        meta["assignee"] = assignee_of(root)

        prev_fases = {f["id"]: f for f in cur.get("fases", []) if f.get("id")}
        fases = []
        for sub in children.get(root["id"], []):
            prev_f = prev_fases.get(sub["id"], {})
            prev_ativ = {a["id"]: a for a in prev_f.get("ativ", []) if a.get("id")}

            ativ = []
            for leaf in children.get(sub["id"], []):
                prev_a = prev_ativ.get(leaf["id"], {})
                due = due_of(leaf)
                # original_due é a data-base: só é definida na primeira vez
                # que a atividade aparece; depois disso fica congelada.
                original_due = prev_a.get("original_due", due) if prev_a else due
                ativ.append({
                    "n": leaf["name"],
                    "status": to_normalized(leaf["status"]["status"], f"atividade '{leaf['name']}'", warnings),
                    "due": due,
                    "original_due": original_due,
                    "id": leaf["id"],
                })

            fases.append({
                "n": sub["name"],
                "status": to_normalized(sub["status"]["status"], f"subfase '{sub['name']}'", warnings),
                "assignee": assignee_of(sub),
                "due": due_of(sub),
                "id": sub["id"],
                "ativ": ativ,
            })

        fases.sort(key=lambda f: sub_sort_key(f["n"]))
        meta["fases"] = fases
        new_metas.append(meta)

    # ordena pelo 'num' curado, nunca pela orderindex viva do ClickUp
    new_metas.sort(key=phase_sort_key)
    data["metas"] = new_metas

    # ---------- visão GANTT (seleção curada) ----------
    for bar in data["gantt"]:
        t = by_id.get(bar["id"])
        if t is None:
            warnings.append(f"barra do Gantt '{bar['name']}' (id {bar['id']}) não existe mais no ClickUp.")
        else:
            bar["status"] = check_gantt_status(t["status"]["status"], f"Gantt '{bar['name']}'", warnings)
            d = due_of(t)
            if d:
                bar["due"] = d
        for ch in bar.get("children", []):
            ct = by_id.get(ch["id"])
            if ct is None:
                warnings.append(f"item do Gantt '{ch['name']}' (id {ch['id']}) não existe mais no ClickUp.")
                continue
            ch["status"] = check_gantt_status(ct["status"]["status"], f"Gantt '{ch['name']}'", warnings)
            d = due_of(ct)
            if d:
                ch["due"] = d

    data["last_synced"] = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
    return data


def main():
    if not CLICKUP_TOKEN:
        print("ERRO: CLICKUP_TOKEN não definido.", file=sys.stderr)
        sys.exit(1)

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    tasks = fetch_all_tasks(LIST_ID, CLICKUP_TOKEN)
    if not tasks:
        print("ERRO: ClickUp devolveu zero tarefas -- abortando sem tocar no JSON.", file=sys.stderr)
        sys.exit(1)
    print(f"{len(tasks)} tarefas recebidas do ClickUp.")

    warnings = []
    before = json.dumps(data, sort_keys=True, ensure_ascii=False)
    data = sync(data, tasks, warnings)
    after = json.dumps(data, sort_keys=True, ensure_ascii=False)

    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
        f.write("\n")

    for w in warnings:
        print(f"AVISO: {w}", file=sys.stderr)

    print(f"Sincronização concluída. Mudou algo além do timestamp: {before != after}")


if __name__ == "__main__":
    main()
