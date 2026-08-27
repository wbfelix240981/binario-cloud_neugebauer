#!/usr/bin/env python3
"""
Monta o index.html a partir de templates/base.html + data/neugebauer.json.

Não faz nenhuma chamada de rede. Quem busca dados novos no ClickUp é o
sync_clickup.py (script separado).

Uso:
  python scripts/build.py
"""
import argparse
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_TEMPLATE = os.path.join(ROOT, "templates", "base.html")
DEFAULT_DATA = os.path.join(ROOT, "data", "neugebauer.json")
DEFAULT_OUT = os.path.join(ROOT, "index.html")

PLACEHOLDERS = ("{{GANTT_TASKS_JSON}}", "{{RAFAEL_METAS_JSON}}", "{{LOGIN_USERS_JSON}}",
                "{{LAST_SYNC_UTC}}")


def js_array(obj, indent=1):
    """Serializa como JSON (que é JS válido) preservando acentuação."""
    return json.dumps(obj, ensure_ascii=False, indent=indent)


def build(template_path=DEFAULT_TEMPLATE, data_path=DEFAULT_DATA, out_path=DEFAULT_OUT):
    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    with open(template_path, "r", encoding="utf-8") as f:
        template = f.read()

    for ph in PLACEHOLDERS:
        if ph not in template:
            print(f"ERRO: placeholder {ph} não encontrado no template.", file=sys.stderr)
            sys.exit(1)

    out = (
        template
        .replace("{{GANTT_TASKS_JSON}}", js_array(data["gantt"]))
        .replace("{{RAFAEL_METAS_JSON}}", js_array(data["metas"]))
        .replace("{{LOGIN_USERS_JSON}}", js_array(data["login"]["users"]))
        # Sem isto o painel mostrava sempre a mesma data (o valor ficava
        # congelado no template) e parecia que nunca atualizava.
        .replace("{{LAST_SYNC_UTC}}", data.get("last_synced") or "")
    )

    leftover = re.findall(r"\{\{[A-Z_]+\}\}", out)
    if leftover:
        print(f"ERRO: sobraram placeholders sem substituir: {leftover}", file=sys.stderr)
        sys.exit(1)

    # sanidade básica antes de gravar
    if out.count("<div") != out.count("</div>"):
        print(f"ERRO: divs desbalanceadas ({out.count('<div')} x {out.count('</div>')}).", file=sys.stderr)
        sys.exit(1)

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(out)

    n_fases = sum(len(m.get("fases", [])) for m in data["metas"])
    n_ativ = sum(len(f.get("ativ", [])) for m in data["metas"] for f in m.get("fases", []))
    print(f"OK: {out_path} gerado "
          f"({len(data['metas'])} metas, {n_fases} fases, {n_ativ} atividades, "
          f"{len(data['gantt'])} barras no Gantt)")
    return out


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--template", default=DEFAULT_TEMPLATE)
    p.add_argument("--data", default=DEFAULT_DATA)
    p.add_argument("--out", default=DEFAULT_OUT)
    a = p.parse_args()
    build(a.template, a.data, a.out)
