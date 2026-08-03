# Painel executivo — Neugebauer (Binário Cloud)

Painel de acompanhamento de alto nível do projeto de migração da Neugebauer
para a Binário Cloud, sincronizado automaticamente com o ClickUp.

## Arquitetura

```
data/neugebauer.json        <- fonte da verdade: dados dinâmicos do ClickUp
                                + campos curados à mão, lado a lado
templates/base.html         <- HTML/CSS estático com marcadores {{...}}
assets/                     <- logos e favicon (arquivos reais, não base64 solto)
scripts/build.py            <- template + JSON -> index.html (sem rede)
scripts/sync_clickup.py     <- ClickUp API -> atualiza SÓ os campos dinâmicos do JSON
scripts/bootstrap_seed.py   <- rodado 1x só, pra criar o JSON inicial (não faz parte da automação)
tests/test_sync.py          <- testes com dados simulados (sem tocar no ClickUp de verdade)
.github/workflows/sync-clickup.yml  <- roda sync + build sozinho, 3x ao dia
index.html                  <- arquivo final publicado (gerado, não editar direto)
```

### Separação curado vs. dinâmico

Dentro de `data/neugebauer.json`, cada fase/subfase/atividade tem os dois
tipos de campo juntos:

- **Curado** (nunca é sobrescrito pela sincronização): `descricao` de cada
  fase, `num`, e tudo em `meta` (título da página, textos do cabeçalho,
  usuário/senha da tela de login).
- **Dinâmico** (sempre atualizado a partir do ClickUp): `name`, `status`,
  `assignee`, `due_date`, e a lista de filhos (`subphases`/`activities`).

O casamento entre um nó do JSON e uma tarefa do ClickUp é feito por `id`.
Se um nó ainda não tem `id`, o script casa por nome no mesmo nível e passa a
gravar o id real a partir da primeira sincronização — depois disso o
casamento por id é robusto até a renomeações.

### Vocabulário de status

Esta lista usa nomes de status **em português customizados**:
`complete`, `em andamento`, `pendente`, `aguardando cliente`, `to do`.

⚠️ Se um dia outra lista/pessoa for adicionada a este painel, **confirme o
vocabulário de status dela antes de reaproveitar o código** — já tivemos um
bug real de dado zerado em outro projeto por assumir o vocabulário errado
(uma lista usava os nomes padrão em inglês do ClickUp, outra usava nomes
customizados em português). Por segurança, `sync_clickup.py` e `build.py`
**nunca** classificam um status desconhecido como "não iniciado"
silenciosamente: preservam o texto bruto, avisam no log, e mostram um badge
roxo "status desconhecido" no painel para chamar atenção.

## Automação (GitHub Actions)

O workflow `.github/workflows/sync-clickup.yml` roda sozinho:

- **3x ao dia**: 06h, 12h e 20h (horário de Brasília)
- Também pode ser disparado manualmente em **Actions → Sincronizar com
  ClickUp → Run workflow**
- Só cria um commit (e só publica) **quando algo realmente mudou**

⚠️ A mensagem de commit automático **nunca** usa `[skip ci]` — essa tag
também é respeitada pelo Cloudflare Pages, e faz ele pular o rebuild,
deixando o site publicado desatualizado mesmo com o GitHub certo (isso já
aconteceu de verdade em outro projeto).

### Configuração necessária (uma única vez)

1. Gere um **Personal API Token** no ClickUp: `app.clickup.com/settings/apps`
   (começa com `pk_`).
2. No repositório do GitHub: `Settings → Secrets and variables → Actions →
   New repository secret`.
3. Crie o secret:
   - Nome: `CLICKUP_TOKEN`
   - Valor: o token gerado no passo 1

## Rodar localmente

```bash
pip install -r requirements.txt

# só reconstrói o HTML a partir do JSON atual (sem rede)
python scripts/build.py

# busca o ClickUp de verdade e atualiza o JSON, depois reconstrói
export CLICKUP_TOKEN="pk_xxx"
python scripts/sync_clickup.py
python scripts/build.py

# roda os testes (dados simulados, não toca no ClickUp real)
python tests/test_sync.py
```
