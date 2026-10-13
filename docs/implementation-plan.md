# MVP V1 — plano de implementação

## Estado do ponto de partida

- Repositório clonado sem arquivos de aplicação ou commits.
- Contrato de MVP recebido em 2026-10-12; os sete eventos, um property_id, PT-BR, Telegram, whitelist, Google Sheets e single writer estão congelados.
- A especificação funcional fornecida pelo proprietário governa esta implementação.

## Arquitetura

Telegram (aiogram polling) → autorização por whitelist → download/transcrição → interpretação estruturada → validação determinística e resolução por propriedade → esclarecimento/preview/confirm → fila serializada de command → event append-only e efeitos idempotentes em Sheets → consulta ao histórico → resposta. Vacinação reportada pode ter como alvo um animal ou um lote explicitamente resolvido; o histórico do animal projeta eventos de lote a partir das alocações vigentes na data do evento.

O LLM nunca escreve diretamente. `property_id`, ator, command_id e event_id são atribuídos/validados pelo servidor. Fonte de dados será uma interface de armazenamento com adaptador Google Sheets e implementação em memória para testes. O MVP documenta e aplica limites de rate/file size, logs operacionais sem o texto bruto; transcrições, respostas e referências de áudio podem ser persistidas na planilha e não guarda áudio após transcrição.

## Fases e critérios de aceite

1. **Contrato e domínio:** Pydantic para as sete famílias de evento; alvos/medidas/outcomes; whitelist e propriedade como fronteira de resolução; desconhecidos explícitos; rejeitar intenções fora do MVP.
2. **Persistência:** abas mínimas e headers; append de command/event/target/outcome/identifier/allocation/relationship/effects/audit; resoluções indexadas por property_id; idempotência por command_id; single writer e estado parcial explícito.
3. **Interação:** Telegram texto/áudio, transcrição, esclarecimento, preview e confirmação; callbacks autorizados e persistência recuperável; comandos de consulta de histórico. O arquivo de áudio fica em memória durante a transcrição e não é persistido; transcrições e metadados de origem permanecem na planilha conforme acesso e retenção configurados.
4. **Verificação:** testes unitários e integração ponta a ponta com fakes para os sete eventos, clarificação, confirmação, duplicate update, failure partial, autorização e histórico; teste de inicialização de planilha fake; lint/type checks se suportados.
5. **Operação:** `.env.example`, setup da planilha, instruções de credenciais e execução local. Prova real com Telegram, OpenAI e Google Sheets requer segredos/contas do proprietário; sem essas credenciais o limite será reportado claramente.

## Escopo negativo

Sem leite, estoque, finanças, alimentação, compra/venda, morte executável, protocolos clínicos, hardware, offline, WhatsApp ou mensagens de escrita arbitrária. Não apagar nem sobrescrever fatos; correções geram novo evento relacionado. Sem segredo real no repositório.

## Riscos que moldam a implementação

- Sheets não oferece transação distribuída entre abas: writer serializa commands; efeitos são registrados/aplicados sequencialmente e falha parcial nunca retorna sucesso total.
- Apêndice de uma linha é único por pedido, mas command_id e chaves idempotentes também serão conferidos sob o single writer.
- Se ocorrer timeout após o servidor ter escrito sem resposta, reconciliação pela chave precede retry.
- Sem credenciais e folha configurada, a prova real externa não pode ser declarada concluída; integração simulada continua necessária.
