# Painel executivo — Neugebauer (Binário Cloud)

Painel de acompanhamento do projeto de migração da Neugebauer para a
Binário Cloud, sincronizado automaticamente com o ClickUp.

## Arquitetura

```
data/neugebauer.json   <- fonte da verdade (curado + dinâmico lado a lado)
templates/base.html    <- o painel, com marcadores {{...}} no lugar dos dados
scripts/build.py       <- template + JSON -> index.html (sem rede)
scripts/sync_clickup.py<- ClickUp -> atualiza SÓ os campos dinâmicos do JSON
tests/test_sync.py     <- 9 cenários com dados simulados
index.html             <- gerado; não editar à mão
```

## Curado x dinâmico

**Curado** (o sync nunca sobrescreve):
- `metas[]`: `num`, `name`, `short`, `detail`, `tags`
- `metas[].fases[].ativ[]`: `original_due` — data-base do prazo. Se ela
  acompanhasse a `due`, o cálculo de atraso zeraria sozinho toda vez que
  alguém empurrasse o prazo no ClickUp.
- `gantt[]`: `metaNum`, `name`, `start` e **a seleção de `children`** — o
  Gantt é uma visão curada, mostra um subconjunto escolhido a mão e com
  datas de início definidas manualmente.
- `login.users`

**Dinâmico** (vem do ClickUp): `status`, `due`, `assignee` e a árvore
`fases`/`ativ`.

## ⚠️ Dois vocabulários de status

Este painel usa **dois** conjuntos de status ao mesmo tempo:

| Visão | Vocabulário | Valores |
|---|---|---|
| Metas (`RAFAEL_METAS`) | normalizado, inglês | `backlog`, `in planning`, `in progress`, `in test`, `in review`, `blocked`, `shipped` |
| RoadMap/Gantt (`GANTT_TASKS`) | cru do ClickUp, português | `aberto`, `em andamento`, `fechado`, `aguardando retorno`, `bloqueada`, `concluído`, ... |

A conversão fica no `STATUS_MAP` do `sync_clickup.py`. Um status do
ClickUp que não estiver mapeado **não vira `backlog` silenciosamente** —
ele gera aviso no log e é marcado como `blocked` (vermelho, visível),
justamente para não repetir o bug de painel aparecer zerado por
vocabulário errado.

Conferido em 27/08/2026: `bloqueada` e `concluído` existiam na lista mas
faltavam no `ROADMAP_STATUS_META` do template — as barras do Gantt saíam
sem cor. Foram adicionados.

## Automação

`.github/workflows/sync-clickup.yml` roda **de hora em hora** (e sob
demanda em Actions → Run workflow). Ele sincroniza, reconstrói, roda os
testes e só commita se algo mudou.

A mensagem de commit **nunca** usa `[skip ci]` — o Cloudflare Pages
respeita essa tag e pularia o rebuild, deixando o site publicado
desatualizado mesmo com o GitHub certo.

Secret necessário: `CLICKUP_TOKEN` (gerado em
`app.clickup.com/3080406/settings/apps`).

## Acessos

| Nome | Usuário |
|---|---|
| Acesso geral | `neugebauer` |
| Binário Cloud | `binario` |
| Norton Soares Domingues | `ndomingues` |
| Francis Picoli | `fpicoli` |
| Cassiano Morin dos Santos | `cmsantos` |
| Wagner Bento Felix | `wfelix` |
| Rogerio Martins de Oliveira | `rmartins` |

Ficam em `data/neugebauer.json` → `login.users`.

⚠️ Site estático: essas senhas são visíveis no código-fonte para quem
souber procurar. Serve como barreira contra acesso casual, não como
autenticação de verdade.

## Rodar localmente

```bash
pip install -r requirements.txt
python scripts/build.py                 # só reconstrói (sem rede)

export CLICKUP_TOKEN="pk_..."
python scripts/sync_clickup.py          # busca no ClickUp
python scripts/build.py

python tests/test_sync.py               # dados simulados
```

## Publicação

- GitHub Pages: https://wbfelix240981.github.io/binario-cloud_neugebauer/
- Cloudflare Pages: https://binario-cloud-neugebauer.pages.dev

