#!/usr/bin/env python3
"""
Testes do sync_clickup.py com dados SIMULADOS (não toca no ClickUp real).

Cobre:
  (a) nada mudou
  (b) algo mudou
  (c) regras de negócio deste painel:
      c1 - os DOIS vocabulários (metas normalizado x gantt cru)
      c2 - status desconhecido não vira "backlog" silenciosamente
      c3 - campos curados sobrevivem (detail/short/name/tags/num)
      c4 - original_due é congelada (não acompanha a due)
      c5 - Gantt é curado: não ganha itens novos sozinho, só atualiza
      c6 - ordem das metas segue o 'num' curado, não a ordem do ClickUp
      c7 - inventário profundo (nível 4+) não vira atividade
"""
import copy
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import sync_clickup as sc  # noqa: E402

FALHAS = []


def check(label, cond):
    print(f"[{'OK ' if cond else 'FALHOU'}] {label}")
    if not cond:
        FALHAS.append(label)


def task(id_, name, status, parent, order=0, assignee=None, due=None):
    return {
        "id": id_, "name": name, "status": {"status": status},
        "parent": parent, "orderindex": str(order),
        "assignees": [{"username": assignee}] if assignee else [],
        "due_date": str(due) if due else None,
    }


def base_data():
    return {
        "list_id": "TEST", "last_synced": None,
        "login": {"users": [{"usuario": "x", "senha": "y", "nome": "Z"}]},
        "metas": [
            {"num": 1, "id": "f1", "status": "in progress", "due": None,
             "name": "Fase 1 — Iniciação e planejamento do Projeto Neugebauer",
             "short": "Fase 1 — Iniciação", "assignee": "Diogo", "tags": ["Projeto Neugebauer"],
             "detail": "Texto curado da fase 1.",
             "fases": [
                 {"n": "1.1 Kickoff", "status": "shipped", "assignee": "Diogo", "due": None, "id": "s11",
                  "ativ": [
                      {"n": "Definir stakeholders", "status": "shipped", "due": 1000, "original_due": 1000, "id": "a1"},
                      {"n": "Elaborar TAP", "status": "backlog", "due": 2000, "original_due": 2000, "id": "a2"},
                  ]},
             ]},
        ],
        "gantt": [
            {"id": "f1", "metaNum": 1, "name": "Fase 1 — Iniciação", "status": "em andamento",
             "start": 500, "due": 9000, "assignee": "Diogo",
             "children": [
                 {"id": "s11", "name": "1.1 Kickoff", "status": "fechado",
                  "start": 500, "due": 1500, "assignee": "Diogo"},
             ]},
        ],
    }


def base_tasks():
    return [
        task("f1", "Fase 1 — Iniciação e planejamento", "em andamento", None, 1, "Diogo"),
        task("s11", "1.1 Kickoff", "fechado", "f1", 1, "Diogo"),
        task("a1", "Definir stakeholders", "fechado", "s11", 1, due=1000),
        task("a2", "Elaborar TAP", "aberto", "s11", 2, due=2000),
    ]


def t_a_nada_mudou():
    print("\n--- (a) nada mudou ---")
    w = []
    r = sc.sync(copy.deepcopy(base_data()), base_tasks(), w)
    m = r["metas"][0]
    check("status da meta continua 'in progress'", m["status"] == "in progress")
    check("2 atividades preservadas", len(m["fases"][0]["ativ"]) == 2)
    check("nenhum aviso", len(w) == 0)
    check("last_synced preenchido", r["last_synced"] is not None)


def t_b_algo_mudou():
    print("\n--- (b) algo mudou ---")
    tasks = base_tasks()
    tasks[3]["status"]["status"] = "em andamento"      # a2: aberto -> em andamento
    tasks.append(task("a3", "Atividade nova", "aberto", "s11", 3))
    w = []
    r = sc.sync(copy.deepcopy(base_data()), tasks, w)
    ativ = {a["id"]: a for a in r["metas"][0]["fases"][0]["ativ"]}
    check("a2 virou 'in progress'", ativ["a2"]["status"] == "in progress")
    check("atividade nova entrou", "a3" in ativ)
    check("a1 continua 'shipped'", ativ["a1"]["status"] == "shipped")


def t_c1_dois_vocabularios():
    print("\n--- (c1) dois vocabulários ao mesmo tempo ---")
    w = []
    r = sc.sync(copy.deepcopy(base_data()), base_tasks(), w)
    meta_st = r["metas"][0]["fases"][0]["status"]
    gantt_st = r["gantt"][0]["children"][0]["status"]
    check("METAS usa normalizado em inglês ('shipped')", meta_st == "shipped")
    check("GANTT mantém o cru em português ('fechado')", gantt_st == "fechado")
    check("mesma tarefa, vocabulários diferentes", meta_st != gantt_st)


def t_c2_status_desconhecido():
    print("\n--- (c2) status desconhecido não vira 'backlog' escondido ---")
    tasks = base_tasks()
    tasks[3]["status"]["status"] = "Status Inventado"
    w = []
    r = sc.sync(copy.deepcopy(base_data()), tasks, w)
    ativ = {a["id"]: a for a in r["metas"][0]["fases"][0]["ativ"]}
    check("NÃO virou 'backlog'", ativ["a2"]["status"] != "backlog")
    check("virou 'blocked' (visível)", ativ["a2"]["status"] == "blocked")
    check("gerou aviso", any("NÃO MAPEADO" in x for x in w))


def t_c3_curados_sobrevivem():
    print("\n--- (c3) campos curados sobrevivem ---")
    tasks = base_tasks()
    tasks[0]["name"] = "Fase 1 renomeada no ClickUp"
    w = []
    r = sc.sync(copy.deepcopy(base_data()), tasks, w)
    m = r["metas"][0]
    check("detail curado intacto", m["detail"] == "Texto curado da fase 1.")
    check("name curado intacto (não pegou o nome novo do ClickUp)",
          m["name"] == "Fase 1 — Iniciação e planejamento do Projeto Neugebauer")
    check("short curado intacto", m["short"] == "Fase 1 — Iniciação")
    check("tags curadas intactas", m["tags"] == ["Projeto Neugebauer"])
    check("num curado intacto", m["num"] == 1)
    check("login intacto", r["login"]["users"][0]["usuario"] == "x")


def t_c4_original_due_congelada():
    print("\n--- (c4) original_due é congelada (base do cálculo de atraso) ---")
    tasks = base_tasks()
    tasks[3]["due_date"] = "9999"   # prazo empurrado no ClickUp
    w = []
    r = sc.sync(copy.deepcopy(base_data()), tasks, w)
    a2 = {a["id"]: a for a in r["metas"][0]["fases"][0]["ativ"]}["a2"]
    check("due acompanhou o ClickUp (9999)", a2["due"] == 9999)
    check("original_due continua 2000 (não zerou o atraso)", a2["original_due"] == 2000)


def t_c5_gantt_curado():
    print("\n--- (c5) Gantt é curado: atualiza, mas não cresce sozinho ---")
    tasks = base_tasks()
    tasks[1]["status"]["status"] = "bloqueada"
    tasks.append(task("s12", "1.2 Subfase nova", "aberto", "f1", 2))
    w = []
    d = copy.deepcopy(base_data())
    r = sc.sync(d, tasks, w)
    check("Gantt continua com 1 barra (não absorveu a subfase nova)", len(r["gantt"]) == 1)
    check("Gantt continua com 1 filho", len(r["gantt"][0]["children"]) == 1)
    check("status do filho atualizou para 'bloqueada'", r["gantt"][0]["children"][0]["status"] == "bloqueada")
    check("start curado preservado", r["gantt"][0]["children"][0]["start"] == 500)
    check("METAS (essa sim) absorveu a subfase nova", len(r["metas"][0]["fases"]) == 2)


def t_c6_ordem_pelo_num():
    print("\n--- (c6) ordem das metas segue o 'num' curado ---")
    d = copy.deepcopy(base_data())
    d["metas"].append({"num": 2, "id": "f2", "status": "backlog", "due": None,
                       "name": "Fase 2", "short": "Fase 2", "assignee": "", "tags": [],
                       "detail": "curado 2", "fases": []})
    tasks = base_tasks()
    tasks.append(task("f2", "Fase 2", "aberto", None, 0))   # orderindex menor que a Fase 1
    tasks[0]["orderindex"] = "9"
    w = []
    r = sc.sync(d, tasks, w)
    check("ordem publicada é 1,2 (não a do ClickUp)", [m["num"] for m in r["metas"]] == [1, 2])


def t_c7_inventario_profundo():
    print("\n--- (c7) inventário de VMs (nível 4+) não vira atividade ---")
    tasks = base_tasks()
    tasks.append(task("srv", "Servidores Linux", "em andamento", "a2", 1))
    tasks.append(task("vm1", "NGBORA1", "bloqueada", "srv", 1))
    w = []
    r = sc.sync(copy.deepcopy(base_data()), tasks, w)
    nomes = [a["n"] for a in r["metas"][0]["fases"][0]["ativ"]]
    check("atividades continuam sendo só as de nível 3", len(nomes) == 2)
    check("VM do inventário não subiu para o painel", "NGBORA1" not in nomes)


if __name__ == "__main__":
    for fn in (t_a_nada_mudou, t_b_algo_mudou, t_c1_dois_vocabularios,
               t_c2_status_desconhecido, t_c3_curados_sobrevivem,
               t_c4_original_due_congelada, t_c5_gantt_curado,
               t_c6_ordem_pelo_num, t_c7_inventario_profundo):
        fn()
    print("\n" + "=" * 52)
    if FALHAS:
        print(f"{len(FALHAS)} teste(s) falharam:")
        for f in FALHAS:
            print(" -", f)
        sys.exit(1)
    print("Todos os testes passaram.")
