# Auditoria da definição de pronto do MVP V1

Atualizada em 2026-10-12 após inspeção do checkout e execução de 87 testes locais. Status `localmente verificado` significa comportamento exercitado com serviços simulados, não acesso real a Telegram/OpenAI/Google.

| Requisito | Evidência atual | Estado |
|---|---|---|
| As sete famílias canônicas, identidade interna e identificador de exibição separado | `domain.py`, `validation.py`, `application.py`; testes de domínio e aplicação, incluindo vacinação direcionada a lote e histórico por associação temporal | Localmente verificado |
| Uma fazenda configurada, whitelist antes da resolução, buscas de animal/lote limitadas por propriedade | `settings.py`, `_ensure_trusted_rows`, resolução do adaptador Sheets | Localmente verificado |
| Texto e áudio em português, limite de download, transcrição em memória e auditoria de falha antes da interpretação | `telegram_bot.py`, `transcription.py`; testes de roteamento, transcrição e estado `FAILED` | Localmente verificado com doubles |
| Áudio → STT → interpretação → evento → consulta do histórico em um percurso | `test_voice_to_event_to_history_integrated_path_with_service_doubles` | Localmente verificado com doubles; prova real segue pendente |
| Saída estruturada do modelo, regra determinística, esclarecimento encadeado e prévia | `llm.py`, `validation.py`, `application.py`; testes com proposta fixa e preservação do pedido/respostas em esclarecimentos múltiplos | Localmente verificado com doubles |
| Data relativa em fuso da propriedade, omissão de data e data obrigatória para pesagem | `validation.py` resolve `hoje`/`ontem`/`amanhã` e o dia da propriedade para eventos sem expressão; golden set e testes cobrem as regras e a clarificação de pesagem | Localmente verificado com doubles |
| Confirmação/cancelamento ligados a usuário, chat e mensagem, recuperáveis após reinício | binding append-only em `18_Conversas`; testes de reabertura do roteador e de vínculo | Localmente verificado com store em memória |
| Evento canônico, resultados 1:N de parto e efeitos derivados idempotentes | `application.py`, `sheets.py`; testes de parto, identifiers, genealogia e falha parcial | Localmente verificado com store em memória |
| Transferência encerra alocação anterior e abre nova | pré-validação de uma alocação ativa; teste de transferência | Localmente verificado com store em memória |
| Correções preservam evento original e relacionam nova versão | `correction_of`, resolução de correção natural, prévia com valor anterior/novo e projeção de histórico | Parcial: pesagem, vacinação e observação em alvo compatível; trocar grupo-alvo, identidade, parto ou alocação exige revisão manual |
| Consulta de histórico e ausência de duplicação por reenvio Telegram | `/historico`, chaves de comando; testes de duplicação simultânea, retry após falha parcial, correção, identificador ambíguo e evento parcial sem alvo | Localmente verificado com store em memória |
| Saúde do processo de polling | `/health` verifica a tarefa de polling e retorna `503` quando parada | Localmente verificado sem rede externa |
| 16 abas/schema Sheets e escrita `RAW` append-only | `TAB_HEADERS`, bootstrap e testes fake do adaptador | Localmente verificado com API simulada; folha real não verificada |
| Métricas do MVP sem thresholds inventados | `docs/mvp-golden-set.md`, `agro-notes-metrics` e `metrics.py` | Parcial: snapshot implementado; não executado sem planilha; métricas de acurácia aguardam anotação humana |
| Golden set com avaliação real de intenção/slots | `docs/mvp-golden-set.md` | Pendente: rotulagem humana/modelo real |
| Fluxo técnico real: Telegram → áudio → STT → Sheets → resposta | Nenhuma credencial/planilha está configurada no checkout ou ambiente desta execução | Pendente de acesso externo |

## Limite de correções

Correções com efeito pontual (`WEIGHING`, `VACCINATION`, `HEALTH_OBSERVATION`) podem ser ligadas por ID explícito ou, para uma correção natural sem ID, ao evento aplicado mais recente e compatível do mesmo usuário. Alvo e data são herdados quando faltam e a prévia mostra o fato anterior e o novo antes de confirmar. Vacinação direcionada a grupo pode ser corrigida apenas mantendo o mesmo grupo; mudança de grupo exige revisão manual. O histórico ativo deixa de exibir a versão corrigida e conserva ambas as linhas no log. Correções que recriariam animais/outcomes ou reescreveriam intervalos de alocação ficam em `MANUAL_REVIEW`; nenhum efeito compensatório é inventado.

## Próximo gate verificável

O checkout não contém `.env`, `credentials/google-service-account.json`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_ALLOWED_USER_IDS`, `GOOGLE_SHEET_ID` nem `OPENAI_API_KEY`. Sem esses recursos, não há como provar a definição de pronto real. Quando a implantação local estiver configurada, repetir o fluxo de áudio da seção 21 e o caso de parto da seção 22, depois reconciliar abas `06_Eventos`, `07_Evento_Animais`, `08A_Resultados_Parto`, `02_Animais`, `03_Identificadores_Animal`, `02A_Vinculos_Genealogicos`, `20_Event_Effects` e `99_Audit_Log`.
