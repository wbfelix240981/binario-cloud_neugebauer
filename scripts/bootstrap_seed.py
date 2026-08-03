#!/usr/bin/env python3
"""
Script de bootstrap (rodar 1x): monta data/neugebauer.json com o estado
conhecido atual. Depois disso, quem mantém esse arquivo atualizado é o
sync_clickup.py — este script aqui não faz parte da automação contínua.
"""
import json

# (id, nome, status)  -- ids reais coletados via ClickUp; quando não
# tínhamos o id exato de uma atividade-folha, deixamos None e o
# sync_clickup.py casa por nome na primeira sincronização real e
# preenche o id correto a partir daí (self-healing).
def act(name, status, id_=None):
    return {"id": id_, "name": name, "status": status, "assignee": None, "due_date": None}

FASE1 = {
    "id": "86ajrf5d1", "num": 1, "name": "Fase 1 — Iniciação e planejamento",
    "descricao": "Formalização, refinamento técnico e planejamento do cronograma",
    "status": "em andamento", "assignee": None, "due_date": None,
    "subphases": [
        {
            "id": "86ajrf5df", "name": "1.1 Kickoff e formalização", "status": "complete",
            "assignee": None, "due_date": None,
            "activities": [
                act("Definir stakeholders", "complete"),
                act("Elaborar apresentação de kickoff", "complete"),
                act("Realizar reunião de kickoff", "complete"),
                act("Registrar decisões e pendências do kickoff", "complete"),
                act("Elaborar TAP", "complete"),
                act("Enviar TAP para assinatura", "complete"),
                act("Obter assinatura da Binário Cloud", "complete"),
                act("Obter assinatura da Neugebauer", "complete"),
                act("Formalizar abertura do projeto", "complete"),
            ],
        },
        {
            "id": "86ajrf5de", "name": "1.2 Refinamento do escopo", "status": "em andamento",
            "assignee": None, "due_date": None,
            "activities": [
                act("Validar inventário de servidores", "em andamento"),
                act("Validar servidores ativos e desligados", "em andamento"),
                act("Identificar servidores que serão migrados", "em andamento"),
                act("Identificar servidores fora do escopo", "em andamento"),
                act("Levantar sistemas operacionais", "em andamento"),
                act("Levantar capacidade de disco por servidor", "em andamento"),
                act("Definir tipo de migração por servidor", "em andamento"),
                act("Levantar dependências entre aplicações", "pendente"),
                act("Definir criticidade dos sistemas", "pendente"),
                act("Definir RPO e RTO", "aguardando cliente"),
                act("Levantar integrações externas, IPs e domínios", "pendente"),
                act("Levantar requisitos de licenciamento", "em andamento"),
                act("Definir janelas de manutenção", "aguardando cliente"),
                act("Aprovar escopo técnico refinado", "pendente"),
                act("Levantar serviços hospedados", "em andamento"),
            ],
        },
        {
            "id": "86ajrf5dc", "name": "1.3 Planejamento do projeto", "status": "em andamento",
            "assignee": None, "due_date": None,
            "activities": [
                act("Definir marcos do projeto", "complete"),
                act("Elaborar cronograma detalhado", "em andamento"),
                act("Definir responsáveis por frente", "pendente"),
                act("Definir dependências entre atividades", "pendente"),
                act("Definir critérios de conclusão por tarefa", "pendente"),
                act("Elaborar plano de comunicação", "complete"),
                act("Definir reuniões semanais de acompanhamento", "em andamento"),
                act("Criar registro de riscos e impedimentos", "em andamento"),
                act("Aprovar cronograma com o cliente", "pendente"),
            ],
        },
    ],
}

FASE2 = {
    "id": "86ajrf5cz", "num": 2, "name": "Fase 2 — Preparação e implementação",
    "descricao": "Ambiente Binário Cloud: rede, firewall, VMs, backup e monitoramento",
    "status": "em andamento", "assignee": None, "due_date": None,
    "subphases": [
        {
            "id": "86ajrf5dh", "name": "2.1 Preparação da Binário Cloud", "status": "em andamento",
            "assignee": None, "due_date": None,
            "activities": [
                act("Validar sizing contratado", "to do"),
                act("Validar disponibilidade de capacidade", "to do"),
                act("Criar projeto/tenant", "complete"),
                act("Criar usuários e permissões", "to do"),
                act("Configurar quotas", "to do"),
                act("Configurar regiões e zonas de disponibilidade", "to do"),
                act("Registrar evidências do ambiente criado", "to do"),
            ],
        },
        {
            "id": "86ajrf5dj", "name": "2.2 Rede e conectividade", "status": "to do",
            "assignee": None, "due_date": None,
            "activities": [
                act("Levantar redes de origem", "to do"),
                act("Definir redes de destino", "to do"),
                act("Definir endereçamento IP", "to do"),
                act("Definir gateways e rotas", "to do"),
                act("Definir modelo de conectividade entre ambientes", "to do"),
                act("Configurar VPN ou link de migração", "to do"),
                act("Configurar DNS necessário", "to do"),
                act("Testar conectividade entre ambientes", "to do"),
                act("Validar throughput disponível", "to do"),
                act("Documentar topologia final", "to do"),
            ],
        },
        {
            "id": "86ajrf5dk", "name": "2.3 Firewall e segurança", "status": "to do",
            "assignee": None, "due_date": None,
            "activities": [
                act("Levantar políticas atuais", "to do"),
                act("Levantar objetos, grupos e serviços", "to do"),
                act("Definir estratégia de implantação do Fortinet", "to do"),
                act("Provisionar Virtual Firewall Fortinet", "to do"),
                act("Configurar interfaces", "to do"),
                act("Configurar rotas", "to do"),
                act("Configurar políticas de segurança", "to do"),
                act("Configurar NATs", "to do"),
                act("Configurar VPNs", "to do"),
                act("Validar acessos", "to do"),
                act("Obter aprovação das regras pelo cliente", "to do"),
            ],
        },
        {
            "id": "86ajrf5dp", "name": "2.4 Máquinas virtuais", "status": "to do",
            "assignee": None, "due_date": None,
            "activities": [
                act("Definir estratégia de migração por VM", "em andamento"),
                act("Agrupar VMs por sistema ou onda", "to do"),
                act("Criar flavors", "to do"),
                act("Criar redes e portas", "to do"),
                act("Criar volumes", "to do"),
                act("Criar servidores virtuais", "to do"),
                act("Aplicar hardening básico", "to do"),
                act("Configurar sistema operacional", "to do"),
                act("Configurar acesso administrativo", "em andamento"),
                act("Validar CPU, memória e armazenamento", "to do"),
                act("Validar conectividade", "to do"),
                act("Liberar VMs para instalação ou migração", "to do"),
            ],
        },
        {
            "id": "86ajrf5dr", "name": "2.5 Backup", "status": "em andamento",
            "assignee": None, "due_date": None,
            "activities": [
                act("Confirmar RPO/RTO com o cliente", "to do"),
                act("Confirmar servidores protegidos", "to do"),
                act("Validar capacidade do repositório", "to do"),
                act("Criar tenant Veeam", "complete"),
                act("Configurar repositório", "complete"),
                act("Configurar política de retenção de 90 dias", "to do"),
                act("Configurar backup full semanal", "to do"),
                act("Configurar backups incrementais duas vezes ao dia", "to do"),
                act("Configurar cópia imutável", "to do"),
                act("Configurar Health Check semanal", "to do"),
                act("Configurar monitoramento dos jobs", "to do"),
                act("Executar primeiro backup", "to do"),
                act("Executar teste de restauração", "to do"),
                act("Obter validação do cliente", "to do"),
            ],
        },
        {
            "id": "86ajrf5dt", "name": "2.6 Monitoramento e serviços gerenciados", "status": "to do",
            "assignee": None, "due_date": None,
            "activities": [
                act("Integrar ambiente ao Cloud+", "to do"),
                act("Configurar monitoramento das VMs", "to do"),
                act("Configurar monitoramento do sistema operacional", "to do"),
                act("Configurar monitoramento do firewall", "to do"),
                act("Configurar monitoramento dos backups", "to do"),
                act("Validar geração automática de alertas", "to do"),
                act("Definir processo de acionamento", "to do"),
                act("Validar operação CCOE 24x7", "to do"),
                act("Preparar documentação para sustentação", "to do"),
            ],
        },
    ],
}

FASE3 = {
    "id": "86ajrf5cy", "num": 3, "name": "Fase 3 — Migração",
    "descricao": "Estratégia, piloto e ondas de migração dos servidores",
    "status": "to do", "assignee": None, "due_date": None,
    "subphases": [
        {
            "id": "86ajrf5dz", "name": "3.1 Estratégia de migração", "status": "to do",
            "assignee": None, "due_date": None,
            "activities": [
                act("Definir método por servidor", "to do"),
                act("Definir ondas de migração", "to do"),
                act("Definir ordem baseada em dependências", "to do"),
                act("Definir responsáveis de cada onda", "to do"),
                act("Definir janela por onda", "to do"),
                act("Definir tempo estimado", "to do"),
                act("Elaborar checklist pré-migração", "to do"),
                act("Elaborar plano de rollback", "to do"),
                act("Aprovar plano com o cliente", "to do"),
            ],
        },
        {
            "id": "86ajrf5dx", "name": "3.2 Migração piloto", "status": "to do",
            "assignee": None, "due_date": None,
            "activities": [
                act("Selecionar servidores piloto", "to do"),
                act("Executar replicação inicial", "to do"),
                act("Validar sincronização", "to do"),
                act("Executar teste funcional", "to do"),
                act("Registrar problemas encontrados", "to do"),
                act("Ajustar procedimento", "to do"),
                act("Obter aprovação para demais ondas", "to do"),
            ],
        },
        {
            "id": "86ajrf5dy", "name": "3.3 Ondas de migração", "status": "to do",
            "assignee": None, "due_date": None,
            "activities": [
                act("Onda 1 — Servidores de baixa criticidade", "to do"),
                act("Onda 2 — Aplicações intermediárias", "to do"),
                act("Onda 3 — Oracle", "to do"),
                act("Onda 4 — SAP/HANA", "to do"),
                act("Onda 5 — Serviços críticos restantes", "to do"),
            ],
        },
    ],
}

FASE4 = {
    "id": "86ajrf5d3", "num": 4, "name": "Fase 4 — Go-live e estabilização",
    "descricao": "Testes finais, virada de chave e estabilização pós go-live",
    "status": "to do", "assignee": None, "due_date": None,
    "subphases": [
        {
            "id": "86ajrf5e8", "name": "4.1 Testes finais", "status": "to do",
            "assignee": None, "due_date": None,
            "activities": [
                act("Testar conectividade", "to do"),
                act("Testar aplicações", "to do"),
                act("Testar integrações", "to do"),
                act("Testar acessos externos", "to do"),
                act("Testar firewall e políticas", "to do"),
                act("Testar jobs de backup", "to do"),
                act("Testar restauração", "to do"),
                act("Validar monitoramento", "to do"),
                act("Validar desempenho", "to do"),
                act("Registrar aceite dos testes", "to do"),
            ],
        },
        {
            "id": "86ajrf5e4", "name": "4.2 Virada de chave", "status": "to do",
            "assignee": None, "due_date": None,
            "activities": [
                act("Confirmar autorização do cliente", "to do"),
                act("Comunicar início da virada", "to do"),
                act("Realizar sincronização final", "to do"),
                act("Desativar ou isolar ambiente anterior", "to do"),
                act("Atualizar DNS, rotas ou apontamentos", "to do"),
                act("Liberar ambiente de produção", "to do"),
                act("Executar testes pós-virada", "to do"),
                act("Comunicar conclusão", "to do"),
            ],
        },
        {
            "id": "86ajrf5e7", "name": "4.3 Estabilização", "status": "to do",
            "assignee": None, "due_date": None,
            "activities": [
                act("Monitorar ambiente após o go-live", "to do"),
                act("Acompanhar alertas", "to do"),
                act("Corrigir pendências", "to do"),
                act("Registrar incidentes da estabilização", "to do"),
                act("Validar desempenho", "to do"),
                act("Confirmar estabilidade com o cliente", "to do"),
            ],
        },
    ],
}

FASE5 = {
    "id": "86ajrf5d6", "num": 5, "name": "Fase 5 — Encerramento e transição",
    "descricao": "Transição para operação (CCOE) e encerramento formal do projeto",
    "status": "to do", "assignee": None, "due_date": None,
    "subphases": [
        {
            "id": "86ajrf5ee", "name": "5.1 Transição para operação", "status": "to do",
            "assignee": None, "due_date": None,
            "activities": [
                act("Elaborar documentação as built", "to do"),
                act("Atualizar diagrama de rede", "to do"),
                act("Documentar inventário final", "to do"),
                act("Documentar políticas de firewall", "to do"),
                act("Documentar rotinas de backup", "to do"),
                act("Validar cadastro no monitoramento", "to do"),
                act("Realizar passagem para o CCOE", "to do"),
                act("Confirmar canais de suporte", "to do"),
                act("Confirmar SLAs", "to do"),
                act("Realizar reunião de transição", "to do"),
            ],
        },
        {
            "id": "86ajrf5ef", "name": "5.2 Encerramento", "status": "to do",
            "assignee": None, "due_date": None,
            "activities": [
                act("Validar entregáveis contratados", "to do"),
                act("Consolidar pendências residuais", "to do"),
                act("Elaborar relatório final", "to do"),
                act("Realizar reunião de encerramento", "to do"),
                act("Enviar termo de aceite", "to do"),
                act("Obter aceite formal da Neugebauer", "to do"),
                act("Registrar lições aprendidas", "to do"),
                act("Encerrar o projeto", "to do"),
            ],
        },
    ],
}

data = {
    "list_id": "901328018187",
    "last_synced": None,
    "meta": {
        "page_title": "Neugebauer — Painel Binário Cloud",
        "hero_eyebrow": "Painel executivo · Jornada para a nuvem",
        "hero_title": "Acompanhamento do projeto",
        "hero_subtitle": "Visão consolidada de fases e atividades para a liderança do projeto.",
        "login": {"username": "neugebauer", "password": "binario2026"},
    },
    "phases": [FASE1, FASE2, FASE3, FASE4, FASE5],
}

with open("data/neugebauer.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

n_sub = sum(len(p["subphases"]) for p in data["phases"])
n_act = sum(len(s["activities"]) for p in data["phases"] for s in p["subphases"])
print(f"data/neugebauer.json criado: {len(data['phases'])} fases, {n_sub} subfases, {n_act} atividades")
