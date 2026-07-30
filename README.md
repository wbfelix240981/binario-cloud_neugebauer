# Painel executivo — Neugebauer (Binário Cloud)

Painel de acompanhamento de alto nível do projeto de migração da Neugebauer para a Binário Cloud.

## Atualização automática via ClickUp

O arquivo `index.html` é gerado automaticamente a partir da lista **teste** no ClickUp.

- **Script gerador:** `scripts/generate_dashboard.py`
- **Template:** `templates/base.html` (head/CSS estáticos + placeholders para conteúdo dinâmico)
- **Imagens:** `assets/` (logo Binário Cloud, logo Neugebauer, favicon)
- **Automação:** `.github/workflows/update-dashboard.yml` — roda todo dia às 08h (horário de Brasília) e também pode ser disparado manualmente na aba *Actions* do GitHub.

### Configuração necessária (uma única vez)

1. Gere um **Personal API Token** no ClickUp: `Configurações → Apps → API Token` (começa com `pk_`).
2. No repositório do GitHub, vá em `Settings → Secrets and variables → Actions → New repository secret`.
3. Crie o secret:
   - Nome: `CLICKUP_TOKEN`
   - Valor: o token gerado no passo 1

Pronto — a partir daí o workflow roda sozinho todos os dias e também pode ser disparado manualmente em **Actions → Atualizar painel executivo (ClickUp) → Run workflow**.

### Rodar localmente (opcional)

```bash
pip install -r requirements.txt
export CLICKUP_TOKEN="pk_xxx"
export CLICKUP_LIST_ID="901328018187"
python scripts/generate_dashboard.py
```
