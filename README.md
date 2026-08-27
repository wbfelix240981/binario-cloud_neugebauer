# Painel executivo — Neugebauer (Binário Cloud)

Painel de acompanhamento do projeto de migração da Neugebauer para a
Binário Cloud.

## Estado atual (27/08/2026)

O painel publicado é o arquivo **`index.html`**, editado diretamente
(não é mais gerado por script). Ele tem tela de login, abas, KPIs,
visão de metas e visão RoadMap (Kanban/Gantt).

**A sincronização automática com o ClickUp está DESATIVADA.**

### Por quê

O pipeline antigo (`legado/`) gerava o `index.html` a partir de
`legado/templates/base.html` + `legado/data/neugebauer.json`. Esse
template produz o **layout antigo**, diferente do painel atual. Se o
workflow voltasse a rodar no agendamento, ele reconstruiria o
`index.html` no formato antigo e commitaria por cima — apagando o
painel novo.

Por isso o gatilho `schedule` foi removido de
`.github/workflows/sync-clickup.yml` (sobrou só o disparo manual, e
mesmo esse não mexe mais no `index.html`).

### Para religar a automação

É preciso reescrever `legado/scripts/build.py` para gerar o layout
novo (extraindo `index.html` num template com marcadores, como era
feito antes), e só então reativar o `cron` no workflow.

## Acessos

O login fica no próprio `index.html`, no array `CREDENCIAIS` (final do
arquivo). Usuários atuais:

| Nome | Usuário |
|---|---|
| Acesso geral | `neugebauer` |
| Binário Cloud | `binario` |
| Norton Soares Domingues | `ndomingues` |
| Francis Picoli | `fpicoli` |
| Cassiano Morin dos Santos | `cmsantos` |
| Wagner Bento Felix | `wfelix` |
| Rogerio Martins de Oliveira | `rmartins` |

⚠️ Como é um site estático, essas senhas ficam visíveis no código-fonte
para quem souber procurar. Serve como barreira contra acesso casual,
não como autenticação de verdade.

## Publicação

- **GitHub Pages:** https://wbfelix240981.github.io/binario-cloud_neugebauer/
- **Cloudflare Pages:** https://binario-cloud-neugebauer.pages.dev

Ambos publicam automaticamente a cada push na `main`.

## Pastas

```
index.html    <- o painel publicado (editar aqui)
assets/       <- logos e favicon
legado/       <- pipeline antigo de sincronização (desativado)
deploy/       <- scripts de cron para VM (Linux e Windows), não configurados
```
