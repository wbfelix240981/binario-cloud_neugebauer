#!/usr/bin/env python3
"""Monta o index.html: templates/base.html + data/neugebauer.json.

Não acessa a rede. Quem fala com o ClickUp é scripts/sync_clickup.py; este
script só junta os dados já gravados no JSON com o template.

Formato dos marcos
------------------
O modelo novo lê exatamente a árvore que o sync já grava:
    metas[] -> fases[] -> ativ[]
com num, name, short, detail, tags, status, due, original_due, assignee,
party e obs. Nada precisa ser achatado.

Marcos com num 999 são tarefas que estão na raiz da lista do ClickUp sem
pertencer a uma fase; o painel os agrupa à parte, como "Frente paralela".

Credenciais
-----------
O painel guarda SHA-256 de "usuario:senha" (mesma conta de hashCred() no
JavaScript), então a senha em texto puro fica só no JSON do repositório e
nunca no HTML publicado.
"""
import argparse
import hashlib
import json
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
TEMPLATE = RAIZ / "templates" / "base.html"
DADOS = RAIZ / "data" / "neugebauer.json"
SAIDA = RAIZ / "index.html"

MARCADORES = ("{{METAS_JSON}}", "{{CREDENCIAIS_JSON}}", "{{LAST_SYNC_UTC}}")

# Campos que o painel realmente usa. Qualquer outro fica de fora do HTML para
# o arquivo não crescer com sobras do ClickUp.
CAMPOS_META = ("num", "id", "name", "short", "detail", "tags", "status",
               "start", "due", "assignee", "internal", "oculto",
               "excludeFromIndex")
CAMPOS_FASE = ("n", "id", "status", "start", "due", "original_due",
               "assignee", "party", "obs", "subde", "oculto", "extra")
CAMPOS_ATIV = ("n", "id", "status", "start", "due", "original_due",
               "assignee", "party", "obs", "subde", "extra")


def limpar(item, campos):
    """Mantém só os campos conhecidos e descarta valores vazios."""
    return {k: item[k] for k in campos
            if k in item and item[k] not in (None, "", [], {})}


def hash_cred(usuario, senha):
    return hashlib.sha256(
        (usuario.strip().lower() + ":" + senha).encode("utf-8")).hexdigest()


def montar_metas(dados):
    """Converte as metas do JSON para o formato que o painel lê.

    O modelo separa as atividades por responsável (Binário / Neugebauer /
    conjunta). A lista do ClickUp ainda não marca isso, então tudo entra como
    'nd' ("A definir") — sem chutar quem é dono do quê, que num painel de
    cliente é pior do que deixar em branco.
    """
    saida = []
    for meta in dados["metas"]:
        m = limpar(meta, CAMPOS_META)
        fases = []
        for fase in meta.get("fases", []):
            f = limpar(fase, CAMPOS_FASE)
            f.setdefault("party", "nd")
            ativ = []
            for a in fase.get("ativ", []):
                a = limpar(a, CAMPOS_ATIV)
                a.setdefault("party", "nd")
                ativ.append(a)
            if ativ:
                f["ativ"] = ativ
            fases.append(f)
        m["fases"] = fases
        saida.append(m)
    return saida


def montar_credenciais(dados):
    # Só estes dois mexem no painel; os demais acessos são de leitura.
    editores = {"binario", "wfelix"}
    linhas = []
    for u in dados["login"]["users"]:
        usuario = u["usuario"].strip().lower()
        entrada = {
            "usuario": usuario,
            "hash": hash_cred(usuario, u["senha"]),
            "nome": u.get("nome", usuario),
        }
        if usuario in editores:
            entrada["editor"] = True
        linhas.append("  " + json.dumps(entrada, ensure_ascii=False))
    return ",\n".join(linhas)


def js_array(itens):
    """Uma linha por item: o diff do git mostra o que mudou de verdade."""
    return ",\n".join(" " + json.dumps(i, ensure_ascii=False) for i in itens)


def main():
    # Os testes constroem o painel a partir de um JSON temporário, por isso a
    # origem e o destino precisam ser trocáveis pela linha de comando.
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data", default=str(DADOS), help="JSON de entrada")
    ap.add_argument("--out", default=str(SAIDA), help="HTML de saída")
    ap.add_argument("--template", default=str(TEMPLATE))
    args = ap.parse_args()

    template = pathlib.Path(args.template).read_text(encoding="utf-8")
    dados = json.loads(pathlib.Path(args.data).read_text(encoding="utf-8"))
    saida = pathlib.Path(args.out)

    faltando = [m for m in MARCADORES if m not in template]
    if faltando:
        sys.exit(f"ERRO: marcadores ausentes no template: {faltando}")

    metas = montar_metas(dados)
    html = (template
            .replace("{{METAS_JSON}}", js_array(metas))
            .replace("{{CREDENCIAIS_JSON}}", montar_credenciais(dados))
            .replace("{{LAST_SYNC_UTC}}", dados.get("last_synced") or ""))

    # --- conferências antes de gravar ---------------------------------
    sobrou = re.findall(r"\{\{[A-Z_]+\}\}", html)
    if sobrou:
        sys.exit(f"ERRO: marcador não substituído: {sobrou}")

    # Um </div> a mais já quebrou o painel uma vez.
    abre, fecha = html.count("<div"), html.count("</div>")
    if abre != fecha:
        sys.exit(f"ERRO: <div> desbalanceada ({abre} abre, {fecha} fecha)")

    # O carimbo precisa ser o do sync, não um valor preso no template.
    if not dados.get("last_synced"):
        sys.exit("ERRO: last_synced vazio — o painel mostraria 'Atualizado em —'")

    ativ = sum(len(f.get("ativ", [])) or 1
               for m in metas for f in m["fases"]) or 0
    saida.write_text(html, encoding="utf-8")
    print(f"{saida.name} gerado  ·  {len(metas)} marcos  ·  {ativ} atividades  "
          f"·  {len(dados['login']['users'])} acessos  ·  sync {dados['last_synced']}")


if __name__ == "__main__":
    main()
