# Contexto e evidências — arquitetura do Agro Notes para pecuária

## Tarefa
Definir, com revisões de agentes, a arquitetura futura do Agro Notes para evoluir de captura de eventos por Telegram para um sistema de manejo pecuário inspirado em conceitos do farmOS, sem assumir cópia da aplicação ou integração obrigatória.

## Resultado desejado
Uma arquitetura implementável e fatiada que preserve o funcionamento atual enquanto define domínio, persistência, interfaces, fluxos, integração futura, riscos, critérios de aceite e estratégia de verificação.

## Evidências locais
- A branch de trabalho é `codex/livestock-management`, derivada de `origin/main`.
- `README.md` descreve captura de texto/áudio via Telegram, interpretação estruturada, validação determinística, confirmação e armazenamento append-only em Google Sheets; escopo atual inclui cadastro/entrada, parto, pesagem, transferência de lote, vacinação reportada e observação de saúde.
- `src/agro_notes/domain.py` define sete tipos de eventos e payloads estritos.
- `src/agro_notes/application.py` orquestra validação, resolução, confirmação e efeitos de eventos; alocações de grupo são temporais.
- `src/agro_notes/sheets.py` implementa a persistência atual, com abas para animais, grupos, alocações, eventos e dados derivados.
- Pesquisa anterior do farmOS encontrou o padrão Assets + Logs + Quantities, grupos, inventário/head-counts, locais/movimentos e estado planejado/concluído.
- Pesquisa anterior aponta que a licença do código farmOS é GPL-2.0; API JSON:API pode servir para interoperabilidade se houver instância-alvo. Não copiar código ou documentação nesta etapa.

## Restrições
- Esta etapa é de arquitetura e planejamento; não implementar funcionalidades nem alterar contratos de produção.
- Manter o modelo de eventos e o fluxo Telegram como base incremental, salvo evidência forte em contrário.
- Distinguir associação de lote de localização física; distinguir confirmação de mensagem de conclusão do manejo; distinguir grupo de contagem de cabeças.
- Não inferir protocolo veterinário, regra regulatória ou fluxo de corte/leite sem requisitos do produtor.
- Qualquer integração farmOS deve ser opcional, via fronteira/adaptador e IDs explícitos; não introduzir dependência da stack Drupal/PHP sem decisão explícita.

## Desconhecidos a registrar como decisões abertas
- Pecuária de corte, leite ou mista; espécies além de bovinos.
- Nível de rastreio individual vs. coortes/contagem de cabeças.
- Necessidade e disponibilidade de conexão no campo/offline.
- Papel desejado de Google Sheets a médio prazo e necessidade de interface web.
- Existência de instalação farmOS que precise de sincronização.
- Regras locais sobre identificadores, reprodução, tratamentos, carência, retenção e relatórios.

## Pontos de contato
- `src/agro_notes/domain.py`
- `src/agro_notes/validation.py`
- `src/agro_notes/application.py`
- `src/agro_notes/sheets.py`
- `src/agro_notes/telegram_bot.py`
- `src/agro_notes/exports.py`
- `tests/test_domain_validation.py`
- `tests/test_application.py`
- `tests/test_sheets.py`
- `docs/implementation-plan.md`

## Proveniência
Baseado em inspeção read-only do branch local e pesquisa primária do farmOS: https://github.com/farmOS/farmOS, https://farmos.org/model/, https://farmos.org/development/api/, https://v1.farmos.org/guide/assets/animals/ e https://farmos.org/model/logic/group/.


## Revisão arquitetural

O PRD e a especificação de aceitação foram aprovados pelo Architect (rodada 4) e pelo Critic adversarial (rodada 1), em 2026-10-20. Isso aprova o handoff arquitetural das etapas 1–2, sujeito aos gates de produto; não declara implementação concluída.

## Extensão de importação de planilhas

O usuário confirmou que a primeira versão deve importar cadastro e todos os sete tipos já suportados, inclusive parto com múltiplas crias e vacinação individual/grupal. A inspeção local confirmou que o bot recebe texto/voz, mas não importa documentos; `openpyxl` já está declarado para exportação XLSX. A revisão documental decidiu intake via Telegram e propôs destino na planilha Google oficial da propriedade, ainda sujeito a confirmação de produto.

A revisão 4 do PRD/test-spec foi aprovada pelo Architect (rodada 4, com checagem dirigida rodada 5) e Critic adversarial (rodada 2), em 2026-10-20. O P1 da revisão adversarial anterior sobre snapshot durável e correções de vacina grupal foi fechado por abas append-only, proveniência/owner, publicação verificada e regras de correção que preservam a composição. A aprovação é para handoff, não implementação: importação permanece desligada até gates de produto, migração, testes I0 e homologação em cópia. Nenhum teste/código de importação foi executado/implementado nesta etapa.
