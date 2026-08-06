# Sincronização via Windows (5 em 5 minutos)

Guia passo a passo para configurar a sincronização automática nesta
máquina Windows, usando o Agendador de Tarefas em vez de cron (que é
coisa de Linux/Mac).

## 1. Instalar os pré-requisitos (se ainda não tiver)

- **Python 3**: baixe em https://www.python.org/downloads/ — na
  instalação, marque a caixinha **"Add Python to PATH"**.
- **Git**: baixe em https://git-scm.com/download/win

Depois de instalar, abra o **PowerShell** e confirme:

```powershell
python --version
git --version
```

## 2. Baixar o script

Salve o arquivo `deploy/sync-cron.ps1` (deste repositório) em:

```
C:\neugebauer-sync\sync-cron.ps1
```

## 3. Configurar as credenciais

Abra o arquivo `sync-cron.ps1` num editor de texto e preencha as duas
linhas no topo:

```powershell
$ClickUpToken = "pk_..."          # o mesmo token do ClickUp que já usamos
$GitRemote   = "https://SEU_TOKEN_GITHUB@github.com/wbfelix240981/binario-cloud_neugebauer.git"
```

Pro `$GitRemote`, você precisa de um **token do GitHub** (diferente do
token do ClickUp) com permissão de escrita no repositório. Gere um em:
https://github.com/settings/tokens/new — marque o escopo **repo**.

⚠️ Como o token fica salvo em texto nesse arquivo, mantenha essa pasta
protegida (não compartilhe o arquivo, não suba ele pro GitHub).

## 4. Testar manualmente antes de agendar

Abra o PowerShell **como Administrador** e rode:

```powershell
powershell -ExecutionPolicy Bypass -File "C:\neugebauer-sync\sync-cron.ps1"
```

Deve terminar com `Publicado com sucesso.` ou `Nada mudou, nenhum
commit necessario.`. Se der erro, corrija antes de seguir para o
agendamento.

## 5. Criar a tarefa agendada (a cada 5 minutos)

1. Abra o **Agendador de Tarefas** (pesquise "Agendador de Tarefas" no
   menu Iniciar, ou `taskschd.msc`)
2. Clique em **Criar Tarefa...** (não "Criar Tarefa Básica", para ter
   mais opções)
3. Aba **Geral**:
   - Nome: `Sincronizacao Neugebauer ClickUp`
   - Marque **Executar estando o usuário conectado ou não**
   - Marque **Executar com privilégios mais altos**
4. Aba **Disparadores** → **Novo...**:
   - Iniciar a tarefa: **Em um agendamento**
   - Configurações: **Diariamente**, repetir a cada 1 dia
   - Marque **Repetir a tarefa a cada**: escolha **5 minutos**
   - Duração: **Indefinidamente**
5. Aba **Ações** → **Novo...**:
   - Ação: **Iniciar um programa**
   - Programa/script: `powershell.exe`
   - Adicionar argumentos:
     ```
     -ExecutionPolicy Bypass -File "C:\neugebauer-sync\sync-cron.ps1"
     ```
6. Aba **Condições**: desmarque "Iniciar a tarefa somente se o
   computador estiver com energia CA" (se for notebook) — não se
   aplica muito numa VM, mas não custa conferir.
7. Clique em **OK** e coloque a senha do usuário Windows quando pedir.

## 6. Conferir que está rodando

No Agendador de Tarefas, clique com o botão direito na tarefa criada e
selecione **Executar** para testar. Depois, veja o histórico na aba
**Histórico** (pode precisar habilitar em **Ação → Habilitar Todo o
Histórico de Tarefas**, no painel da direita).

Você também pode redirecionar a saída do script para um arquivo de log
alterando a Ação para chamar um `.bat` intermediário, se quiser
registrar tudo em texto:

```bat
@echo off
powershell -ExecutionPolicy Bypass -File "C:\neugebauer-sync\sync-cron.ps1" >> C:\neugebauer-sync\sync.log 2>&1
```

E apontar a Ação do Agendador para esse `.bat` em vez do PowerShell
diretamente.
