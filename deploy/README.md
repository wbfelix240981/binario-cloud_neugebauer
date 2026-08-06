# Sincronização via VM (5 em 5 minutos)

Isso substitui o agendamento do GitHub Actions como driver principal
(o GitHub Actions continua ativo, mas só como backup a cada 6h, caso a
VM fique fora do ar).

## Por quê

O cron nativo do GitHub Actions (mesmo configurado para rodar de hora
em hora) atrasa e às vezes pula execuções inteiras em contas gratuitas
-- já vimos isso acontecer de verdade nesse projeto e no de Metas.
Rodando numa VM própria, o cron do sistema operacional é confiável e
permite um intervalo bem mais curto (5 minutos).

## Passo a passo

**1. Copie o script para a VM**

Pegue o arquivo `deploy/sync-cron.sh` deste repositório e salve na VM,
por exemplo em `/opt/neugebauer-sync/sync-cron.sh`.

```bash
mkdir -p /opt/neugebauer-sync
# copie o conteúdo de deploy/sync-cron.sh para /opt/neugebauer-sync/sync-cron.sh
chmod +x /opt/neugebauer-sync/sync-cron.sh
```

**2. Garanta que a VM tem Python 3 e git**

```bash
python3 --version   # 3.9+
git --version
pip3 --version
```

**3. Configure as credenciais**

Edite o topo do `sync-cron.sh` (ou exporte como variáveis de ambiente
num arquivo `/etc/environment` ou similar) com:

- `CLICKUP_TOKEN`: o Personal API Token do ClickUp (o mesmo já usado no
  secret do GitHub, `app.clickup.com/3080406/settings/apps`)
- `GIT_REMOTE`: a URL do repositório **com um token do GitHub embutido**
  para permitir push sem interação, no formato:
  `https://SEU_TOKEN_GITHUB@github.com/wbfelix240981/binario-cloud_neugebauer.git`
  (o token do GitHub precisa do escopo `repo`)

⚠️ Como o token fica salvo em texto no arquivo do script, proteja o
acesso a ele: `chmod 600 sync-cron.sh` e restrinja quem tem acesso SSH
a essa VM.

**4. Teste manualmente antes de agendar**

```bash
/opt/neugebauer-sync/sync-cron.sh
```

Deve terminar com `Publicado com sucesso.` ou `Nada mudou, nenhum
commit necessário.` -- qualquer outra saída indica um problema a
corrigir antes de agendar.

**5. Agende no cron do sistema**

```bash
crontab -e
```

Adicione a linha:

```
*/5 * * * * /opt/neugebauer-sync/sync-cron.sh >> /var/log/neugebauer-sync.log 2>&1
```

**6. Acompanhe os logs**

```bash
tail -f /var/log/neugebauer-sync.log
```
