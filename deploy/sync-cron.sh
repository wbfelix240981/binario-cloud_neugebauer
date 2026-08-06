#!/usr/bin/env bash
#
# Sincroniza o painel da Neugebauer com o ClickUp, direto da sua VM.
# Pensado para rodar via cron a cada 5 minutos, sem depender do
# agendador do GitHub Actions (que atrasa/pula execuções).
#
# Instalação (uma vez só):
#   1. Copie este arquivo para a VM, ex: /opt/neugebauer-sync/sync-cron.sh
#   2. chmod +x /opt/neugebauer-sync/sync-cron.sh
#   3. Preencha REPO_DIR, CLICKUP_TOKEN e GIT_REMOTE abaixo (ou exporte
#      como variáveis de ambiente antes de chamar o script)
#   4. Adicione ao crontab do usuário que vai rodar isso:
#        crontab -e
#      e inclua a linha:
#        */5 * * * * /opt/neugebauer-sync/sync-cron.sh >> /var/log/neugebauer-sync.log 2>&1
#
set -euo pipefail

# ---- CONFIGURAÇÃO (ajuste estes 3 valores) ----
REPO_DIR="${REPO_DIR:-/opt/neugebauer-sync/binario-cloud_neugebauer}"
CLICKUP_TOKEN="${CLICKUP_TOKEN:-COLE_O_TOKEN_AQUI}"
GIT_REMOTE="${GIT_REMOTE:-https://SEU_TOKEN_GITHUB@github.com/wbfelix240981/binario-cloud_neugebauer.git}"
# ------------------------------------------------

export CLICKUP_TOKEN
export CLICKUP_LIST_ID="901328018187"

log() { echo "[$(date -u '+%Y-%m-%d %H:%M:%S UTC')] $*"; }

# Clona o repositório na primeira vez, se ainda não existir
if [ ! -d "$REPO_DIR/.git" ]; then
  log "Repositório não encontrado, clonando pela primeira vez..."
  git clone -q "$GIT_REMOTE" "$REPO_DIR"
fi

cd "$REPO_DIR"

git config user.name "neugebauer-vm-sync"
git config user.email "vm-sync@binario.cloud"

log "Puxando últimas mudanças..."
git fetch -q "$GIT_REMOTE" main
git reset -q --hard FETCH_HEAD

log "Instalando dependências (silencioso se já instalado)..."
pip install -q -r requirements.txt

log "Sincronizando com o ClickUp..."
if ! python3 scripts/sync_clickup.py; then
  log "ERRO: sync_clickup.py falhou -- abortando sem publicar nada."
  exit 1
fi

log "Reconstruindo index.html..."
python3 scripts/build.py

if git diff --quiet -- data/neugebauer.json index.html; then
  log "Nada mudou, nenhum commit necessário."
  exit 0
fi

log "Mudança detectada, publicando..."
git add data/neugebauer.json index.html
git commit -q -m "Sincronização automática com ClickUp (via VM)"
git push -q "$GIT_REMOTE" main
log "Publicado com sucesso."
