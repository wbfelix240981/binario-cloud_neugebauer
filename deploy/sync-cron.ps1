# Sincroniza o painel da Neugebauer com o ClickUp, rodando nesta máquina Windows.
# Pensado para ser chamado pelo Agendador de Tarefas a cada 5 minutos.
#
# Instalação (uma vez só):
#   1. Salve este arquivo em, por exemplo: C:\neugebauer-sync\sync-cron.ps1
#   2. Preencha CLICKUP_TOKEN e GIT_REMOTE abaixo
#   3. Configure o Agendador de Tarefas (ver deploy/README-WINDOWS.md)
#
# Requisitos: Python 3 e Git instalados e no PATH do Windows.

$ErrorActionPreference = "Stop"

# ---- CONFIGURAÇÃO (ajuste estes 2 valores) ----
$RepoDir     = "C:\neugebauer-sync\binario-cloud_neugebauer"
$ClickUpToken = "COLE_O_TOKEN_DO_CLICKUP_AQUI"
$GitRemote   = "https://COLE_SEU_TOKEN_GITHUB_AQUI@github.com/wbfelix240981/binario-cloud_neugebauer.git"
# ------------------------------------------------

$env:CLICKUP_TOKEN   = $ClickUpToken
$env:CLICKUP_LIST_ID = "901328018187"

function Log($msg) {
    $ts = (Get-Date).ToUniversalTime().ToString("yyyy-MM-dd HH:mm:ss")
    Write-Output "[$ts UTC] $msg"
}

if (-not (Test-Path "$RepoDir\.git")) {
    Log "Repositorio nao encontrado, clonando pela primeira vez..."
    New-Item -ItemType Directory -Force -Path (Split-Path $RepoDir) | Out-Null
    git clone -q $GitRemote $RepoDir
}

Set-Location $RepoDir

git config user.name "neugebauer-vm-sync"
git config user.email "vm-sync@binario.cloud"

Log "Puxando ultimas mudancas..."
git fetch -q $GitRemote main
git reset -q --hard FETCH_HEAD

Log "Instalando dependencias (silencioso se ja instalado)..."
pip install -q -r requirements.txt

Log "Sincronizando com o ClickUp..."
python scripts\sync_clickup.py
if ($LASTEXITCODE -ne 0) {
    Log "ERRO: sync_clickup.py falhou -- abortando sem publicar nada."
    exit 1
}

Log "Reconstruindo index.html..."
python scripts\build.py

git diff --quiet -- data\neugebauer.json index.html
if ($LASTEXITCODE -eq 0) {
    Log "Nada mudou, nenhum commit necessario."
    exit 0
}

Log "Mudanca detectada, publicando..."
git add data\neugebauer.json index.html
git commit -q -m "Sincronizacao automatica com ClickUp (via VM Windows)"
git push -q $GitRemote main
Log "Publicado com sucesso."
