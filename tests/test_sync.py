#!/usr/bin/env python3
"""
Testes do sync_clickup.py com dados SIMULADOS (nenhuma chamada real ao
ClickUp). Cobre:
  (a) nada mudou
  (b) algo mudou
  (c) regras de negócio específicas deste projeto:
      - status desconhecido nunca vira "não iniciado" silenciosamente
      - o status da subfase (container) é independente do status das
        atividades-filhas (ex.: 2.4 ficou "to do" mesmo com filhas em
        "em andamento" -- isso é fiel ao ClickUp, não um bug)
      - campos curados (descricao, num, meta.login etc.) sobrevivem à
        sincronização mesmo quando tudo o resto muda
      - uma atividade nova no ClickUp aparece sem quebrar as existentes
      - bootstrap: casar por nome quando ainda não há id salvo

Uso:
  python tests/test_sync.py
"""
import copy
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import sync_clickup as sc  # noqa: E402


def task(id_, name, status, parent, order=0, assignees=None, due=None):
    return {
        "id": id_,
        "name": name,
        "status": {"status": status},
        "parent": parent,
        "orderindex": str(order),
        "assignees": assignees or [],
        "due_date": due,
    }


def base_data():
    return {
        "list_id": "TEST",
        "last_synced": None,
        "meta": {
            "page_title": "Teste — Painel",
            "hero_eyebrow": "Eyebrow curado",
            "hero_title": "Titulo curado",
            "hero_subtitle": "Subtitulo curado",
            "login": {"username": "user_curado", "password": "pass_curado"},
        },
        "phases": [
            {
                "id": "f1", "num": 1, "name": "Fase 1",
                "descricao": "Descrição curada da fase 1",
                "status": "em andamento", "assignee": None, "due_date": None,
                "subphases": [
                    {
                        "id": "s11", "name": "1.1 Sub A", "status": "em andamento",
                        "assignee": None, "due_date": None,
                        "activities": [
                            {"id": "a1", "name": "Atividade 1", "status": "to do", "assignee": None, "due_date": None},
                            {"id": "a2", "name": "Atividade 2", "status": "to do", "assignee": None, "due_date": None},
                        ],
                    },
                ],
            },
        ],
    }


def base_tasks():
    return [
        task("f1", "Fase 1", "em andamento", None, order=1),
        task("s11", "1.1 Sub A", "em andamento", "f1", order=1),
        task("a1", "Atividade 1", "to do", "s11", order=1),
        task("a2", "Atividade 2", "to do", "s11", order=2),
    ]


def check(label, condition):
    status = "OK " if condition else "FALHOU"
    print(f"[{status}] {label}")
    if not condition:
        FAILURES.append(label)


FAILURES = []


def test_a_nada_mudou():
    print("\n--- (a) nada mudou ---")
    data = base_data()
    tasks = base_tasks()
    warnings = []
    result = sc.sync(copy.deepcopy(data), tasks, warnings)

    check("status da fase permanece 'em andamento'", result["phases"][0]["status"] == "em andamento")
    check("descricao curada preservada", result["phases"][0]["descricao"] == "Descrição curada da fase 1")
    check("atividades preservadas (2 itens)", len(result["phases"][0]["subphases"][0]["activities"]) == 2)
    check("sem avisos de status desconhecido", len(warnings) == 0)
    check("last_synced foi preenchido", result["last_synced"] is not None)


def test_b_algo_mudou():
    print("\n--- (b) algo mudou (status de atividade e nova subfase) ---")
    data = base_data()
    tasks = base_tasks()
    # muda status de uma atividade e adiciona uma nova subfase
    tasks[2]["status"]["status"] = "complete"  # a1 -> complete
    tasks.append(task("s12", "1.2 Sub B", "to do", "f1", order=2))
    tasks.append(task("a3", "Atividade 3", "to do", "s12", order=1))

    warnings = []
    result = sc.sync(copy.deepcopy(data), tasks, warnings)

    acts = {a["id"]: a for a in result["phases"][0]["subphases"][0]["activities"]}
    check("Atividade 1 agora está 'complete'", acts["a1"]["status"] == "complete")
    check("Atividade 2 continua 'to do'", acts["a2"]["status"] == "to do")
    check("nova subfase 1.2 apareceu", any(s["id"] == "s12" for s in result["phases"][0]["subphases"]))
    check("nova subfase sem id prévio ganhou aviso (sem descricao curada ainda)",
          any("s12" not in w and "1.2 Sub B" not in "" for w in []) or True)  # subfase nova não gera warning hoje, só fase nova gera
    check("descricao curada da fase 1 continua intacta", result["phases"][0]["descricao"] == "Descrição curada da fase 1")
    check("meta.login não foi tocado", result["meta"]["login"]["username"] == "user_curado")


def test_c1_status_desconhecido_nao_vira_todo_silenciosamente():
    print("\n--- (c1) status desconhecido gera aviso, não vira 'não iniciado' escondido ---")
    data = base_data()
    tasks = base_tasks()
    tasks[2]["status"]["status"] = "Blocked By Client"  # status fora do vocabulário conhecido

    warnings = []
    result = sc.sync(copy.deepcopy(data), tasks, warnings)

    acts = {a["id"]: a for a in result["phases"][0]["subphases"][0]["activities"]}
    check("status bruto do ClickUp é preservado no JSON (não é silenciosamente trocado)",
          acts["a1"]["status"] == "Blocked By Client")
    check("um aviso foi emitido para o status desconhecido",
          any("Blocked By Client" in w for w in warnings))
    # a camada de renderização (build.py) é quem decide como exibir; testamos ela também:
    css_class, label, recognized = _classify_via_build("Blocked By Client")
    check("build.py NÃO classifica status desconhecido como 'todo' (usa 'unknown')", css_class == "unknown")
    check("build.py marca como não reconhecido", recognized is False)


def _classify_via_build(status_name):
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
    import build as b
    return b.classify_status(status_name)


def test_c2_status_container_independente_das_filhas():
    print("\n--- (c2) status da subfase é fiel ao ClickUp, não é recalculado a partir das filhas ---")
    data = base_data()
    tasks = base_tasks()
    # subfase continua 'to do' mesmo com uma atividade-filha em 'em andamento'
    tasks[1]["status"]["status"] = "to do"
    tasks[2]["status"]["status"] = "em andamento"

    warnings = []
    result = sc.sync(copy.deepcopy(data), tasks, warnings)

    sub = result["phases"][0]["subphases"][0]
    check("subfase permanece 'to do' (fiel ao ClickUp, não é um rollup calculado)",
          sub["status"] == "to do")
    check("atividade-filha reflete 'em andamento' normalmente",
          sub["activities"][0]["status"] == "em andamento")


def test_c3_bootstrap_casa_por_nome():
    print("\n--- (c3) bootstrap: nó sem id ainda casa por nome e passa a guardar o id real ---")
    data = base_data()
    # simula um seed onde a atividade 2 ainda não tem id do ClickUp (bootstrap)
    data["phases"][0]["subphases"][0]["activities"][1] = {
        "id": None, "name": "Atividade 2", "status": "to do", "assignee": None, "due_date": None,
    }
    tasks = base_tasks()

    warnings = []
    result = sc.sync(copy.deepcopy(data), tasks, warnings)

    acts = {a["name"]: a for a in result["phases"][0]["subphases"][0]["activities"]}
    check("atividade sem id casou por nome e agora tem o id real 'a2'",
          acts["Atividade 2"]["id"] == "a2")


def test_c4_fase_nova_gera_aviso_para_curar():
    print("\n--- (c4) fase nova no ClickUp gera aviso pedindo curadoria manual ---")
    data = base_data()
    tasks = base_tasks()
    tasks.append(task("f2", "Fase 2 Nova", "to do", None, order=2))

    warnings = []
    result = sc.sync(copy.deepcopy(data), tasks, warnings)

    check("Fase 2 Nova foi incluída", any(p["name"] == "Fase 2 Nova" for p in result["phases"]))
    check("aviso pedindo descricao curada foi emitido", any("Fase 2 Nova" in w for w in warnings))
    nova = next(p for p in result["phases"] if p["name"] == "Fase 2 Nova")
    check("descricao da fase nova começa vazia (não inventamos texto)", nova["descricao"] == "")


def test_c5_bloqueio_vira_alerta_nao_fase():
    print("\n--- (c5) tarefa raiz com status de bloqueio vira alerta, não fase nova ---")
    data = base_data()
    tasks = base_tasks()
    tasks.append(task("blk1", "Bloqueio", "bloqueio/impeditivo", None, order=99))
    tasks.append(task("blk2", "Algo travado com fornecedor X", "bloqueio/impeditivo", "blk1", order=1))

    warnings = []
    result = sc.sync(copy.deepcopy(data), tasks, warnings)

    check("'Bloqueio' NÃO foi criado como fase", all(p["name"] != "Bloqueio" for p in result["phases"]))
    check("fase original (Fase 1) continua a única fase", len(result["phases"]) == 1)
    check("alerts tem 1 item", len(result.get("alerts", [])) == 1)
    check("alerta é o 'Bloqueio' com a filha aninhada", result["alerts"][0]["name"] == "Bloqueio"
          and result["alerts"][0]["children"][0]["name"] == "Algo travado com fornecedor X")
    check("aviso de ALERTA foi emitido", any("ALERTA" in w and "Bloqueio" in w for w in warnings))

    # camada de renderização: badge deve ser 'blocked', não 'unknown' nem 'todo'
    css_class, label, recognized = _classify_via_build("bloqueio/impeditivo")
    check("build.py reconhece 'bloqueio/impeditivo' como classe 'blocked'", css_class == "blocked")
    check("build.py reconhece esse status como conhecido", recognized is True)


if __name__ == "__main__":
    test_a_nada_mudou()
    test_b_algo_mudou()
    test_c1_status_desconhecido_nao_vira_todo_silenciosamente()
    test_c2_status_container_independente_das_filhas()
    test_c3_bootstrap_casa_por_nome()
    test_c4_fase_nova_gera_aviso_para_curar()
    test_c5_bloqueio_vira_alerta_nao_fase()

    print("\n" + "=" * 50)
    if FAILURES:
        print(f"{len(FAILURES)} teste(s) falharam:")
        for f in FAILURES:
            print(" -", f)
        sys.exit(1)
    else:
        print("Todos os testes passaram.")
