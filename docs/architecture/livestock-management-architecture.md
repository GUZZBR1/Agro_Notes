# Arquitetura proposta — manejo pecuário no Agro Notes

Data: 2026-10-20. Branch inspecionada: `codex/livestock-management`.
Estado: arquitetura aprovada pelo Architect (rodada 4) e pelo Critic adversarial (rodada 1), em 2026-10-20. Liberada para handoff de implementação nas etapas 1–2, condicionada aos gates de produto e ativação; não representa implementação concluída nem aceite do produtor.
Escopo: evolução incremental de captura conversacional para registros de manejo, localização, planejamento e consultas. Complexidade total ALTA; primeira entrega delimitada MÉDIA.

## Resultado, limites e evidência

O produtor deve poder registrar um animal, situá-lo fisicamente, consultar seu histórico e usar as correções simples já suportadas com rastreabilidade (correção de movimento/localização não é suportada no piloto), preservando os fluxos atuais de Telegram. Etapas posteriores poderão atender movimentações coletivas, tarefas planejadas, coortes sem identificação individual e interfaces de campo. A arquitetura não presume corte, leite, espécie única, protocolo veterinário, exigência regulatória nem disponibilidade de internet.

### Fatos verificados no checkout

- `README.md:3`, `:29`, `:37`: texto/voz, interpretação, validação, confirmação quando exigida e sete eventos pecuários; não é todo evento que exige confirmação hoje.
- `src/agro_notes/domain.py:18`, `:69`, `:75`, `:142`: enum fechado, peso em kg, troca de lote e tempo de ocorrência em **data**, sem sequência intradiária.
- `src/agro_notes/validation.py:56`: contexto confiável substitui IDs de propriedade, ator e evento produzidos pelo modelo.
- `src/agro_notes/application.py:34`: porta `EventStore` já existe, embora exponha nomes de abas e operações específicas. `:1027` grava eventos/efeitos em etapas, reconhece falha parcial e exige reconciliação manual.
- `src/agro_notes/application.py:1380`: alocação de lote grava `location_id` vazio; `:1437` consulta alocação aberta atual. Não há modelo operacional de pastos só porque uma coluna existe.
- `src/agro_notes/sheets.py:1`, `:18`: ausência de transações entre abas e unicidade garantida; várias abas previstas, inclusive administrações, não significam funcionalidades executáveis.
- `src/agro_notes/main.py:39`, `src/agro_notes/process_lock.py:17`: instância única, lock no mesmo host; isso não protege dois hosts.
- `src/agro_notes/application.py:1642`, `:1669`, `src/agro_notes/settings.py:13`: propriedade configurada por instância; `Telegram_Access` é autoridade de acesso. Ter `property_id` nas linhas não significa SaaS multitenant pronto.
- `src/agro_notes/exports.py:164`, `tests/test_application.py:1677`: exportação por propriedade e testes de exclusão de linhas alheias.
- `pyproject.toml`: Python 3.11+, Pydantic, aiogram, FastAPI, Sheets, pytest e Ruff. Sem configuração de typechecker; não inventar comando mypy como gate existente.

### Referências primárias consultadas

- [Modelo farmOS](https://farmos.org/model/): Assets e Logs como registros centrais, além de Quantities, Plans e outros tipos. Inspira a separação entre identidade e fato, sem exigir um supermodelo genérico.
- [Grupos](https://farmos.org/model/logic/group/): associação histórica e relação entre movimentos de grupo e membros. A proposta local escolhe semântica própria explícita, detalhada abaixo.
- [Inventário](https://farmos.org/model/logic/inventory/): ajustes por reset, incremento e decremento com medida/unidade. A proposta de coortes é futura e precisa de decisão de contagem.
- [API](https://farmos.org/development/api/): módulo `farm_api`, JSON:API, UUIDs e descoberta por `/api` e `/api/schema`. Só uma instância concreta determinará os recursos/bundles realmente disponíveis.
- [Repositório](https://github.com/farmOS/farmOS) e [licença](https://github.com/farmOS/farmOS/blob/4.x/LICENSE.txt): referências da pesquisa anterior; revalidar versão e licença antes de reutilizar qualquer arquivo. Nenhum código ou texto de documentação será transplantado por este plano.

### Inferências

O desenho atual favorece evolução própria. A concentração em `MVPProcessor`, leituras completas de abas e ausência de transação dificultam crescimento, mas não provam necessidade imediata de banco novo. Dados e volume reais ainda não foram medidos. Não há evidência de uma instalação farmOS do produtor que precise de sincronização.

## RALPLAN-DR

Princípios:

1. Identidade, evento executado, intenção planejada e estado técnico têm contratos diferentes.
2. Lote organizacional, localização física e quantidade de cabeças têm significado independente.
3. O servidor decide identidade, autorização e invariantes; interpretação produz somente propostas.
4. Fatos e correções preservam proveniência; projeções são deriváveis e indicam conflitos.
5. Cada entrega fecha um fluxo utilizável com falha recuperável antes de ampliar o domínio.

Top 3 drivers: continuidade dos fluxos Telegram existentes; consistência temporal/auditabilidade do rebanho; custo operacional proporcional à necessidade comprovada.

Opção A — Agro Notes próprio, monólito modular: adapta conceitos úteis do farmOS à stack atual. Vantagens: menor ruptura, confirmação por voz integrada e regras locais explícitas. Contra: equipe passa a manter domínio, consultas e migrações; risco de reinventar recursos maduros. Escolha recomendada para a primeira entrega.

Opção B — Agro Notes como interface + integração farmOS API: usa instância farmOS para registros definidos em contrato. Vantagens: interoperabilidade e recursos existentes. Contra: duas autenticações, mapeamento temporal, falhas remotas e divergências; sincronização bidirecional exige política de autoridade. Reabrir quando existir instalação-alvo e responsável operacional. Não combinar duas fontes de verdade por padrão.

Opção C — adotar/substituir por farmOS e manter adaptador Telegram: concentra manejo na plataforma existente. Vantagens: maior cobertura de gestão disponível e menos domínio próprio. Contra: migração, operação Drupal/PHP, compatibilidade da UX e avaliação de extensões/licenças; perde-se parte do investimento em persistência atual. Reabrir se interface/mapas/planejamento farmOS forem requisitos prioritários e demonstração com dados representativos comprovar aderência.

Tensão central: A minimiza ruptura mas aumenta manutenção; B permite interoperabilidade mas acrescenta conflitos; C oferece plataforma maior mas exige mudança de operação. Adotar farmOS continua alternativa real para obter Assets/Logs/Quantities/Plans e sua API; manter aplicação própria exige manutenção dessas capacidades. Sheets evita migração imediata, mas não transaciona; derivar localização do diário reduz efeitos parciais e aumenta custo de leitura. IDs/exportações estáveis ajudam migração futura, mas não tornam uma troca de plataforma gratuita ou automaticamente reversível.

## Decisões propostas e perguntas abertas

Decidir agora para delimitar execução: manter stack e Telegram; manter single writer/Sheets na primeira fatia; movimento individual primeiro; não atribuir efeito pecuário a uma intenção; recusar temporalidade ambígua na primeira entrega; reutilizar portas e funções existentes antes de extrair abstrações.

Decisões que precisam de dados do produtor antes da respectiva etapa:

- Corte/leite/mista e espécies: bloqueiam módulos especializados, não cadastro de locais.
- Individuais/coortes/misto: bloqueiam contagem consolidada e movimentação parcial de coorte.
- Conectividade e dispositivos: bloqueiam escolha de aplicação offline.
- Volume, usuários simultâneos e operação multi-host: bloqueiam escolha final do armazenamento futuro.
- Instância farmOS e autoridade por recurso: bloqueiam desenvolvimento do conector.
- Precisão operacional necessária (dia, horário ou ordem declarada), múltiplos grupos e pastos simultâneos: bloqueiam movimentações históricas complexas.
- Papéis de consulta/registro/administração, retenção e acesso a transcrições: levantar antes de ampliar usuários ou publicar interface web.

Essas decisões não autorizam presumir prescrições, doses, carência, vacinação obrigatória ou conformidade. Novos registros de saúde são fatos relatados com origem.

## Domínio e invariantes

### Identidades e relações

`Property` delimita dados; inicialmente uma propriedade por instância. `Animal` mantém ID interno, espécie conhecida ou explicitamente ausente, identificadores históricos e genealogia existente. Identificador visível não vira chave primária. `Group` representa lote organizacional; `GroupMembership` é temporal. Preservar restrição operacional atual de uma alocação ativa por animal até decisão explícita.

Novo `Location` possui ID, propriedade, nome, tipo configurado (pasto/curral/outro), ativo/inativo. Hierarquia, coordenadas e polígonos ficam fora do piloto. Inativação impede novo destino, preserva históricos e animais registrados no local, e permite a saída desses animais para outro local ativo. Não declara o local vazio. Nomes ambíguos exigem desambiguação; não selecionar por similaridade silenciosamente.

`LastRecordedLocation` é consulta derivada exclusivamente de movimentos publicados do animal; não há tabela de ocupações nem fechamento/abertura persistidos no piloto. A futura `LocationAssignment` temporal só entra na etapa 3 com contrato próprio. No piloto, “ocupação” em linguagem de produto significa essa última evidência registrada, sem representação persistida de intervalos. Mudança de grupo não muda localização; movimento físico não muda lote. Origem desconhecida é aceita como desconhecida após prévia explícita, nunca preenchida a partir de `area_id` do grupo. No piloto, não há cadastro de grupo implícito durante movimento.

### Eventos, quantidades e planejamento

Fixar três tipos novos e payloads estritos (`extra=forbid`), sem alterar o formato dos sete tipos antigos:

- `LOCATION_CREATED`: proposta requer `name` não vazio e `location_type` em `PASTURE|CORRAL|OTHER`; `notes` opcional. Servidor gera `location_id`, define `active=true` e propriedade. Alvo `target_scope=LOCATION`; não exige nem cria animal.
- `LOCATION_DEACTIVATED`: proposta requer `location_identifier` não vazio, `reason` opcional. Servidor resolve `location_id` na propriedade e define `active=false`. Alvo `LOCATION`; sem linha em `07_Evento_Animais`.
- `ANIMAL_MOVED`: proposta requer `animal_identifier`, `to_location_identifier` não vazios e `time_expression` no envelope. `notes` opcional. Servidor resolve `animal_id`, `to_location_id`, `from_location_id` (nulo se desconhecido) e `previous_movement_event_id` (nulo se nenhum). Alvo `INDIVIDUAL`; destinatário animal segue contrato existente de alvos.

Payload persistido dos três tipos inclui `schema_version=1`, mais campos resolvidos acima e campos originais da proposta. Versão é inserida pelo servidor, não inferida pelo LLM. `property_id`, `actor_id`, `event_id`, `command_id` e data validada ficam no envelope existente; IDs resolvidos são recusados no payload de proposta. Campos obrigatórios ausentes pedem esclarecimento; tipo/versão desconhecido é rejeitado para escrita e apresentado como registro não suportado na leitura, nunca sucesso fictício.

Para local, `location_id` no payload identifica o alvo sem reutilizar `animal_id`; estender explicitamente `_event_row`/prévia/sucesso/histórico/exportação, pois `application.py:1451` atualmente pressupõe `GROUP` ou `INDIVIDUAL`. Cadastro e inativação usam dia de captura como data administrativa, sem backdate no piloto.

Mover para a última localização registrada, com leitura íntegra e sem pendência, é no-op com resposta “já está registrado nesse local”; não grava novo evento de domínio nem alega nova movimentação. Inativar local já inativo também é no-op. Destino inativado entre prévia e confirmação invalida a confirmação. Todos os três tipos novos exigem prévia/confirm e exatamente um evento por comando; qualquer comando com tipo novo e outro evento, novo ou legado, pede separação antes de qualquer escrita de domínio. Registro de conversa/auditoria da rejeição é permitido; lote de eventos puramente legado mantém contrato existente.

`Measurement` futura representa medida, valor finito, unidade, alvo, método/origem quando informado e evento. A primeira entrega preserva `weight_kg` existente; não migrar pesagens só para obter generalidade. Conversão exige tabela explícita; kg de indivíduo, média de grupo e contagem são métricas diferentes.

`Task` futura: intenção com estado `PLANNED`, `CANCELLED` ou `COMPLETED`, alvo e data pretendida. Concluir exige evento executado vinculado e validação; data futura isolada pede esclarecimento. Confirmar interpretação não conclui tarefa, e `APPLIED` é estado técnico, não certeza veterinária.

`Cohort` futura: população não individualizada com unidade cabeças e ajustes auditados. Grupos de animais identificados não são automaticamente coortes. Mistura só após política que evite dupla contagem e defina quando um indivíduo sai da população agregada; até lá, relatórios mostram métricas separadas.

### Tempo e correção

Manter `occurred_on` dos registros existentes; nunca fabricar horário de meia-noite como precisão real. Novos movimentos do piloto aceitam no máximo um movimento por animal/data e apenas data posterior à última movimentação publicada. A data deve ser explícita ou resolvida de expressão fornecida (por exemplo hoje/ontem) e nunca posterior ao dia original de captura no fuso da propriedade. Amanhã/data ISO futura geram esclarecimento sobre intenção, sem movimento aplicado nem criação automática de tarefa. Confirmar depois da meia-noite preserva a âncora original. Persistir `time_precision=DAY`, compatível com `application.py:1451`; consulta promete apenas “última localização registrada em DD/MM”, sem posição física atual ou ordem intradiária. Backdate conflitante, segunda movimentação do dia e correção que modifica ocupações vão para revisão sem escrita parcial de domínio.

Etapa temporal posterior acrescenta precisão (preservando `DAY` legado e introduzindo precisão de instante em contrato futuro), horário com fuso quando fornecido e sequência operacional declarada quando necessária. Intervalos passam a ser semiabertos `[início, fim)` com resolução única por instante; empates sem informação suficiente continuam conflito. Data de gravação não é ordem física presumida. Correção gera vínculo com fato anterior e recalcula intervalos/projeções afetados em cópia antes de publicar. Não sobrepor ocupações ativas silenciosamente.

## Componentes e contratos

Manter um processo de aplicação e módulos internos:

1. Entrada: `telegram_bot.py`, interpretadores/transcrição existentes. Captura IDs e referências; nenhuma escrita de domínio pelo LLM.
2. Validação: `domain.py`/`validation.py`; tipos, unidades, contexto confiável, ambiguidades e prévia.
3. Casos de uso: `application.py`; autorização, resolução, estados de conversa e commit. Extrair para um novo `locations.py` apenas resolução temporal e decisões puras que a primeira fatia realmente introduzir.
4. Persistência: `EventStore` e `GoogleSheetsStore`; novas operações explícitas de local, publicação e consulta do diário de movimentos. Porta futura de transação só quando backend transacional for escolhido, sem fingir que Sheets a implementa.
5. Consulta: histórico e `exports.py`; derivar última localização registrada de movimentos publicados; pendências bloqueiam nova movimentação e aparecem junto da última evidência confirmada, sem afirmar localização atual. Distinguir desconhecido, vazio e conflito.
6. Operação: reconciliação auditada, backup/exportação, métricas existentes. Manter exportações consistentes com o lock atual.

Recursos novos propostos: `src/agro_notes/locations.py`, `tests/test_locations.py`, `src/agro_notes/reconcile_locations.py` e `tests/test_reconcile_locations.py` (CLI administrativa local de listar/inspecionar/finalizar por command_id e suspender animal; aborto somente na preparação ininterrupta com prova definida no protocolo, com operador autorizado explícito e o mesmo ProcessLock; não edição manual de células); aba `11_Locais` (nome reservado; confirmar ausência antes de migrar), com campos `location_id property_id name location_type active source_event_id recorded_at`. Não criar `12_Ocupacoes`. Cada versão de local só é elegível quando seu `source_event_id` está publicado; filtrar eventos publicados **antes** de eleger a versão vigente por local. Reusar `20_Event_Effects` e `99_Audit_Log`; não criar um segundo diário redundante.

## Fluxos críticos

Cadastro/local: usuário autorizado fornece nome/tipo; servidor detecta colisões; prévia; confirmação; grava evento/registro; disponibiliza ID e nome.

Movimento individual: resolver animal/destino → ler diário, comandos pendentes e catálogo de locais com sucesso → bloquear se houver pendência do animal → derivar última localização publicada → validar data/destino → prévia explícita com origem conhecida/desconhecida → confirmar callback → revalidar autorização, pendência e estado → publicar um evento → responder. Alteração de origem/destino antes da confirmação invalida a prévia.

### Protocolo de publicação do piloto (R1/R2)

Aplica-se apenas aos três tipos novos, sob o single writer; não reutilizar cegamente `_commit`/`_safe_event_failure`, pois o caminho atual pode marcar falha depois de APPLIED (`application.py:1027`, `:1849`). O marco único de publicação é a primeira linha completa `06_Eventos` com `processing_status=APPLIED` para o `event_id`, escrita **depois** da auditoria e dos efeitos necessários. IDs/payload dessa linha devem coincidir com o evento preparado. Uma vez publicado, falha de entrega Telegram/conversa não rebaixa o evento para parcial.

Ordem obrigatória:

1. Validar cardinalidade de um evento, autorização, leituras íntegras e ausência de pendência. Persistir na conversa um comando `COMMITTING` com evento/IDs resolvidos e âncora temporal; conferir que foi lido antes de qualquer efeito. Não começar publicação se essa confirmação falhar.
2. Append do evento `APPLYING`. Preparar somente efeitos necessários, com IDs estáveis: versão de local para cadastro/inativação; alvo individual para movimento. Movimento não escreve encerramento nem abertura de ocupação. Efeitos preparados não entram em consultas de domínio antes da publicação.
3. Gravar auditoria `EVENT_PREPARED` com IDs estáveis, ator e conteúdo validado. Falha de auditoria antes da publicação mantém pendência. Não chamar este registro de sucesso concluído.
4. Congelar o envelope completo (IDs, alvo, payload/schema, data/âncora, referências de efeitos e auditoria) e persistir em `06_Eventos` a linha `processing_status=PUBLISHING`. Confirmar por leitura positiva que a linha íntegra corresponde ao envelope antes de enviar APPLIED. PUBLISHING é compromisso irrevogável de concluir aquele evento, não publicação para consulta.
5. Só após essa confirmação, append da linha `APPLIED`, único marco de publicação, e leitura de confirmação. Timeout/leitura negativa não provam cancelamento do append remoto; mantêm bloqueio. Recuperação só pode concluir o mesmo event_id/envelope congelado, jamais abortar ou substituir por outro comando.
6. Encerrar conversa e responder Telegram. Falha aqui é entrega pendente de evento publicado; retry apenas confirma/reenvia resultado. Consulta reconhece publicação mesmo se conversa continua `COMMITTING`.

Ordem lógica global de publicação é a ordem append-only das primeiras linhas APPLIED de cada `event_id` em `06_Eventos`; duplicatas idênticas não criam nova publicação, payload divergente é conflito. Nunca ordenar a planilha fonte manualmente. Essa ordem resolve leitura de versões de catálogo e auditoria, não inventa ordem física intradiária. Para movimento, escolher maior data válida entre publicados; empates de datas em dados corrompidos são conflito, não desempate arbitrário.

### Resultado remoto incerto e recuperação (bloqueador P0 da rodada 2)

Não usar ausência momentânea de linha como prova de que uma chamada `.append(...).execute()` falhou definitivamente. Depois de qualquer tentativa de PUBLISHING, só há caminho de conclusão do mesmo envelope. A proposta adota regra conservadora mais forte que “não abortar após confirmação”: nem PUBLISHING **tentado e incerto** pode ser abortado.

Timeout do próprio PUBLISHING: não enviar APPLIED; manter COMMITTING/APPLYING como pendência durável já registrada e bloquear o animal. A reconciliação lê a linha exata: se presente e íntegra, segue para APPLIED; se ausente, pode reenviar **o mesmo** PUBLISHING/event_id/envelope, aguardando leitura positiva. Repetições são limitadas por tentativa operacional; se indisponível, manter pendência e encerrar tentativa, sem loop infinito. Linhas PUBLISHING idênticas tardias colapsam; nenhuma delas muda envelope, publica fato ou libera bloqueio. APPLIED nunca é enviado sem leitura positiva de PUBLISHING. Não há criação recursiva de intenções ou novos IDs para tentar resolver uma intenção incerta.

ABORTED é permitido somente em preparação **antes de qualquer envio de PUBLISHING**, com evidência positiva no fluxo ininterrupto do escritor único de que a chamada não foi iniciada. Não basta consultar e não encontrar PUBLISHING. Após restart/troca de processo ou resultado incerto, o piloto não possui prova durável dessa ausência de envio e proíbe aborto; reconciliação deve concluir o mesmo evento ou manter pendência/suspensão se houver suspeita. Essa limitação deliberada evita adicionar um segundo journal de publicação. A ação CLI `abort` recusa comandos recuperados após restart ou que chegaram à tentativa de publicação; em termos práticos, aborto seguro é reservado ao cancelamento da preparação dentro da execução que ainda detém essa evidência. O CLI de recuperação opera principalmente inspect/finalize, nunca decide aborto pela ausência de APPLIED/PUBLISHING.

Precedência por evento/comando: APPLIED íntegro prevalece sobre linhas preparatórias tardias; PUBLISHING confirmado ou tentado sem resolução é irrevogável; ABORTED só encerra preparação com a prova acima e sem publicação em voo; demais estados são pendência. Qualquer combinação incompatível de ABORTED e PUBLISHING/APPLIED é corrupção e bloqueia o alvo para revisão, não seleção arbitrária. `COMMITTING`, `APPLYING`, `PARTIALLY_APPLIED` e resultado indeterminado sem publicação/resolução válida bloqueiam **qualquer novo command_id** de movimento do mesmo animal. Pendência de local bloqueia mutações do local e seu uso como destino. Leitura necessária falhando impede escrita; alvo pendente indeterminável bloqueia mutações novas até recuperação.

Falha parcial: `/pendencias` lista comandos e suspensões da propriedade, alvo, data e estado; `/localizacao <animal>` mostra última localização registrada publicada + pendência/suspensão, sem localização posterior confirmada. Leitura falhando informa indisponibilidade. Operador nomeado verifica evidência, completa apenas efeitos ausentes e publica o mesmo event_id/envelope. APPLIED remoto tardio e repetição de recuperação idêntica resultam em uma publicação lógica. Payload divergente é conflito. Depois de APPLIED, limpar apenas pendência de entrega; nunca apagar/rebaixar o fato por falha Telegram.

Reconciliação relê estado sob lock, autoriza operador, consulta suspensão administrativa e é idempotente. No restart, reconstruir bloqueios **antes** de receber movimentos. APPLIED tardio pode resolver a pendência de publicação, mas não remove suspensão administrativa. O piloto não promete exactly-once físico nem cancelamento de chamadas Sheets em voo.

### Suspensão persistente por animal (bloqueador P1 da rodada 2)

Escolha: bloqueio administrativo individual durável, separado de correção de fato. Recurso proposto `src/agro_notes/movement_controls.py` e testes correspondentes, usando SQLite da biblioteca padrão em arquivo de **volume persistente local**, compartilhado pelo bot/CLI no mesmo host; não usar o diretório temporário do ProcessLock. Não há nova dependência. Esse recurso é autoridade exclusiva dos bloqueios administrativos; o diário de fatos continua Sheets.

Tabela append-only `movement_holds`: `control_id` único, `sequence` inteiro monotônico atribuído na transação, `property_id`, `animal_id`, `action` (`SUSPEND`/`RESUME`), `suspect_event_id`, `reason`, `actor_id`, `recorded_at`, `resumes_control_id` opcional. O commit SQLite é o marco da suspensão; reexecução com mesmo control_id não duplica. SUSPEND exige evento suspeito publicado pertencente ao animal/propriedade e motivo não vazio; suspensão vigente é último SUSPEND ainda não retomado explicitamente. O registro é a trilha administrativa; réplica informativa em `99_Audit_Log` pode falhar sem remover bloqueio local.

CLI administrativo `reconcile_locations suspend --animal ... --event ... --reason ...` adquire o mesmo ProcessLock (bot parado), valida operador administrativo explicitamente configurado e acesso à propriedade, e confirma commit durável. Só operadores locais autorizados pelo responsável da fazenda podem suspender; usuário Telegram comum não remove bloqueios. Sem commit confirmado, CLI não anuncia suspensão aplicada, e bot só reinicia após leitura do armazenamento de controles. Falha de leitura/arquivo ausente/corrompido bloqueia movimentos globalmente; inicialização de base vazia é operação explícita do primeiro setup, nunca recuperação automática de arquivo perdido. Backup/restauração desse banco integra o procedimento de operação e migração de host.

#### Identidade e continuidade da autoridade SQLite (rodada 3)

Bot e CLI devem usar a mesma configuração operacional: `MOVEMENT_CONTROLS_DB_PATH` é caminho absoluto canônico, e ambos abrem a base existente em modo que não cria arquivo ausente. Rejeitar caminho relativo, divergência entre configurações e substituição do arquivo enquanto o serviço está ativo. Metadados imutáveis da base: `database_id` aleatório gerado no primeiro setup, `installation_id`, `property_id`, `google_sheet_id` e `schema_version`. A configuração da instalação contém os IDs esperados, fora do volume restaurável do banco; abrir base de outra instalação/propriedade/planilha, ou novo banco vazio com identidade diferente, bloqueia movimentos. Uma migração de host preserva installation_id/database_id; criar identidade nova não é modo de recuperar holds perdidos.

**Limite explícito:** identidade e leitura válidas não provam atualidade. SQLite sozinho não detecta um backup antigo válido com os mesmos IDs. Espelhamento no Sheets é informativo e não fornece prova de continuidade, especialmente quando falhou. Não há liberação baseada só em `integrity_check`, contagem de linhas ou maior sequência observada na cópia restaurada.

Contrato operacional de manutenção obrigatório:

1. Antes de restaurar, substituir volume, mudar caminho ou migrar host, o operador desabilita movimentos em configuração de implantação (`MOVEMENTS_ENABLED=false`, fora do volume SQLite e não restaurada junto com ele), para bot e CLI publicador, para os processos e adquire exclusividade de manutenção. CLI de inspeção/cópia continua possível; nenhuma nova publicação/reconciliação/suspensão concorre com a cópia. Rotinas de recuperação e novos hosts começam desabilitados; não herdam habilitação do snapshot do banco.
2. Se a autoridade vigente ainda existir, capturar cópia integral consistente com todos os processos parados, incluindo dados confirmados do WAL mediante mecanismo de backup SQLite, e criar manifesto de verificação da cópia: IDs, versão, última sequence, contagem de controles e hash do conteúdo canônico de todos os registros/metadados. Comparar o manifesto **obtido agora da fonte vigente** com a base destino e verificar integridade/referências. O manifesto é evidência da manutenção, não segundo banco nem autoridade concorrente de holds; um manifesto antigo não prova atualidade.
3. Somente o operador autorizado pode reabilitar movimentos em configuração de implantação depois de registrar origem vigente, exclusividade durante cópia, identidade e paridade integral verificadas. Desabilitar a instância antiga antes de iniciar a nova. Reabilitação global após cópia fiel não remove nenhum SUSPEND individual e não equivale a RESUME.
4. Se o volume vigente foi perdido, há apenas backup anterior, ou a continuidade é desconhecida, manter `MOVEMENTS_ENABLED=false` mesmo que a restauração abra normalmente. Não reconstruir ausência de holds a partir de mirror Sheets incompleto. Retomada exigirá recuperação demonstrável da autoridade vigente ou um fluxo futuro explicitamente aprovado de revisão da perda; não existe atalho de retomada no piloto.

Restart ordinário no mesmo volume preservado e sem operação de restauração segue a configuração existente; mudança/restauração não é restart ordinário. Uma cópia antiga substituída silenciosamente fora desse procedimento pode ser indistinguível para SQLite; tal operação viola o contrato suportado e não é apresentada como detectável automaticamente. Por isso, restauração/migração automatizada deve executar o gate de desabilitação antes de tocar no volume, e o responsável operacional aceita essa obrigação antes de ativar o piloto. A verificação não depende de sincronização autoritativa com outro armazenamento.

Checar hold antes da prévia, na confirmação e antes de finalizar reconciliação. Hold impede novos movimentos e novas tentativas de publicação por recuperação; não pode cancelar requisição remota já em voo. Um APPLIED tardio é registrado normalmente, mas a suspensão permanece e a consulta aponta que a evidência está sob revisão. `/pendencias` inclui control_id, motivo, event_id e ator autorizado; `/localizacao` indica “registro sob revisão; movimentações suspensas”.

Como correção de movimento publicado está fora do piloto, **não disponibilizar RESUME no piloto**. Suspensão persiste através de restart até um fluxo futuro de revisão/correção aprovado. Esse fluxo deverá exigir operador explicitamente autorizado, motivo e referência à resolução/correção e append RESUME com `resumes_control_id`; somente essa ação poderá liberar aquele hold, sem apagar histórico. Reservar action RESUME no schema não autoriza o executor a criar atalho de desbloqueio agora. Testar que tentativas de retomada no piloto são recusadas e que registro não autorizado/incompatível não libera o animal.

Movimento coletivo posterior: congelar membros na ocorrência e mostrar total/lista resumida, não usar membros de hoje para evento passado. Persistir snapshot de destinatários aprovado; mudança antes da confirmação invalida prévia. Um animal que entra no lote depois não recebe localização retroativa. Caso haja falha de aplicação entre membros, indicar quais aplicaram; ativar em produção somente com reconciliação por membro comprovada ou transação.

Consulta: mostrar lote, última localização registrada e data da última evidência separadamente; localização desconhecida permanece desconhecida. Eventos de saúde de grupo preservam contexto histórico já existente. Não reconstruir silenciosamente alcance clínico a partir de membros atuais.

## Persistência, migração e integração

Piloto Sheets: criar novas abas com cabeçalhos versionados e bootstrap idempotente; preservar headers existentes, cuja incompatibilidade hoje causa erro. Guardar metadados de versão em mecanismo explícito de migração, sem usar configuração administrativa como tabela genérica improvisada. Backfill inicial de local é zero: `location_id` vazio significa desconhecido. Backup anterior, validação de IDs/referências e manifesto de contagens antes/depois; não editar planilha ativa à mão como processo de migração.

Rollback do piloto: desativar novos comandos, manter dados/eventos; leitores anteriores devem ignorar recursos novos sem tratar evento desconhecido como sucesso. Validar downgrade em cópia antes de alegar reversibilidade. Alteração incompatível de enum/leitor exige manter versão compatível em vez de reimplantar cegamente release antiga.

Banco futuro: avaliar PostgreSQL transacional se houver necessidade de múltiplos escritores/hosts, atomicidade coletiva ou degradação medida de consultas. Não adicionar dependência agora. Desenhar unicidade por propriedade+comando, integridade de referências, versionamento otimista e transação de evento/projeções/outbox. Migração: snapshot com bloqueio de escrita, importação reexecutável por IDs, paridade de históricos/exportações, contagens e amostras de correções; corte único de autoridade. Sheets vira exportação, sem dual-write operacional. Rollback pós-novas-escritas exige exportar/reconciliar delta antes de voltar; simples troca de configuração perderia dados.

Conector farmOS condicionado: descobrir schemas da instância, tabela de mapeamento `(property_id, external_instance, resource_type, local_id, external_uuid)` e versão de mapeamento; escolher direção e autoridade por recurso. Começar importação/consulta read-only ou exportação unidirecional mediante caso real. Outbox persistida com retries limitados, falhas visíveis e dedup; no timeout após POST consultar UUID remoto antes de repetir. Divergência de versão vira conflito revisável, não last-write-wins automático. Nunca espelhar exclusão remota como exclusão do diário local.

## Segurança, dados, operação e offline

Continuar autorização antes de ler, interpretar, confirmar ou exportar; revalidar revogação no commit. `property_id` e ator são server-side. Consultas e chaves externas incluem propriedade. Não transformar `19_Usuarios` em autoridade concorrente de `Telegram_Access`.

Aplicar acesso mínimo à planilha e segredos fora do código; exportações seguem conexão do usuário existente. Revisar campos sensíveis em auditoria/transcrições e políticas de acesso/retenção antes de ampliar público. Logs operacionais guardam IDs e classes de erro, não tokens ou conteúdo bruto. Backup deve ser restaurável em cópia; auditar quem reconcilia e quais fatos foram afetados.

Métricas: comandos aceitos/rejeitados, ambiguidades, falhas parciais pendentes, latência de consulta, tamanho de leitura e conflitos temporais. Orçamento de desempenho será fixado com dados representativos antes de exigir crescimento; não prometer número sem medir.

Telegram depende de rede para entregar ao servidor; fila durável de transcrição não é operação offline no campo. Se necessário, etapa própria de cliente com armazenamento local protegido, UUID de comando estável, hora/dispositivo e estado “não sincronizado”; servidor reautoriza, valida e confirma conflitos ao sincronizar. Não prometer execução enquanto aparelho está offline. PWA, app e sincronização bidirecional ficam dependentes de requisitos de campo; nenhum service worker nesta primeira fatia.

## Entregas e handoff

1. **Contratos e proteção do legado:** `domain.py`, `validation.py`, testes existentes. Registrar invariantes, fixtures de legado e decisões temporais; confirmar reconciliação disponível. Aceite: sete eventos continuam reconhecidos com semântica atual e novos tipos inválidos falham sem efeitos.
2. **Locais e movimento individual:** `locations.py` novo, `domain.py`, `application.py`, `sheets.py`, interpretadores, `telegram_bot.py`, `exports.py`. Implementar cadastro/inativação, prévia/confirm, publicação, localização derivada, `/localizacao` e `/pendencias`. Aceite: todos os casos P0 do test-spec passam; ambiguidade temporal não altera domínio; falha parcial não gera sucesso.
3. **Tempo e grupos:** mesmas fronteiras mais snapshots versionados; decidir precisão temporal e regras de conflito; reconciliação por alvo. Aceite: retroatividade e mudanças no grupo não mudam fatos sem revisão; membros são reproduzíveis historicamente. Só iniciar após etapa 2 estável.
4. **Planejamento/medições/coortes:** selecionar fluxo com produtor; contratos `Task` e/ou `Measurement`; coortes somente com regra de contagem aprovada. Aceite: intenção não afeta estoque/ocupação; ausência de dupla contagem; origem/unidade preservadas. Não é pacote obrigatório único.
5. **Escala/interface/integração:** escolher apenas ramos exigidos pelos gatilhos documentados (banco, offline, farmOS). Aceite: migration dry-run/paridade ou contrato de sincronização/UX offline validado, conforme ramo.

As etapas 1–2 estão liberadas para implementação pela aprovação do Architect (rodada 4) e do Critic (rodada 1). Etapas 3–5 continuam condicionadas aos gatilhos descritos e não autorizam inventar requisitos. Responsável por aceitação: líder de execução, com revisão independente dos invariantes temporais e falhas.

## Gate de ativação e inventário de capacidades (R5/R6)

Antes de ativar o piloto, o responsável do produto e um representante do produtor validam cenários reais de movimentação: individual, no máximo uma por dia, sem correção de localização e com revisão manual. Registrar resultado e aceite em evidência de homologação; rejeição desses limites bloqueia ativação e retorna à etapa temporal, sem fingir que a arquitetura cobre a rotina. O responsável da fazenda nomeia pessoa autorizada e substituto para reconciliação, que demonstram `/pendencias` e conclusão e suspensão em cópia, incluindo recusa de abort após envio incerto; identidade ainda não informada é gate pendente, não nome inventado.

Inventário de capacidades:

- **Existente:** cadastro/entrada, parto e genealogia associada, peso individual, troca de lote, vacinação/saúde relatadas, histórico, correções simples suportadas e exportações.
- **Proposto no piloto:** catálogo plano de locais, inativação, movimento individual publicado, última localização registrada, consulta/bloqueio de pendências e reconciliação técnica, com controles administrativos duráveis de suspensão. Correção de movimento publicado está fora do piloto.
- **Condicionado ao roadmap:** movimentos coletivos/temporais avançados, tarefas, medidas adicionais, coortes, reprodução além do parto, cadastro de saída/venda/morte, interface web, offline e conector farmOS.
- **Fora do escopo desta arquitetura operacional:** prescrição/decisão veterinária automática, garantia regulatória, financeiro de vendas, produção de leite, alimentação/formulação de dieta e custeio. Podem originar PRDs futuros após decisão de produto; não ampliar esta entrega.

A fronteira de ciclo de vida (ativo, saiu/vendido, morto, reentrada e correções) precisa de decisão futura antes de qualquer indicador de “rebanho presente/ativo”. Até lá, contagens significam apenas registros cadastrados e não estimativa de animais vivos ou presentes; última localização não prova permanência. Venda como evento de saída não pressupõe módulo financeiro.

## Riscos e condição de conclusão

Principais riscos: simular transação em Sheets; confundir lote/pasto; ordenar fatos com precisão inexistente; relatórios combinarem coortes e indivíduos; crescer o monólito sem limite; desenvolver conector sem cliente; ampliar fontes de dados sensíveis sem controle. Mitigações estão nos gates e testes correspondentes.

Arquitetura estará pronta para handoff quando revisão adversarial tiver resposta por objeção, nenhum bloqueador P0 sem tratamento, paths citados conferidos e primeira fatia puder ser executada sem decisões de produto escondidas. Implementação estará concluída somente quando aceites da fatia, testes e ensaio de falha/migração passarem; este documento não afirma que passaram.
