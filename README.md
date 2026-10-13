# Agro Notes

MVP de captura de eventos de manejo animal por Telegram, com interpretação estruturada, validação determinística, confirmação e armazenamento append-only no Google Sheets.

## Requisitos

- Python 3.11 ou superior
- Token de bot Telegram e ID(s) numéricos autorizados
- Chave Groq (provider inicial) ou OpenAI
- Planilha Google compartilhada com o e-mail da service account
- JSON de credenciais da service account salvo localmente

## Configuração

1. Crie e ative um ambiente virtual; instale `pip install -e .`. Para desenvolvimento, use `pip install -e '.[dev]'`.
2. Copie `.env.example` para `.env` e preencha os segredos e `GOOGLE_SHEET_ID`. `TELEGRAM_ALLOWED_USER_IDS` aceita IDs separados por vírgulas. Groq é o provider inicial para interpretação e transcrição; defina `INTERPRETATION_PROVIDER` e `TRANSCRIPTION_PROVIDER` independentemente como `groq` ou `openai` para selecionar cada integração. Os nomes anteriores `AI_PROVIDER`, `FARM_PROPERTY_ID`, `FARM_TIMEZONE`, `GOOGLE_CREDENTIALS_FILE` e `GROQ_MODEL` continuam aceitos como aliases. Os modelos Groq são configuráveis.
3. Coloque o JSON de service account no caminho de `GOOGLE_CREDENTIALS_FILE`; compartilhe a planilha com o e-mail `client_email` do JSON, com permissão de editor.
4. Inicie com `uvicorn agro_notes.main:app --host 0.0.0.0 --port 8000 --workers 1`. A inicialização cria abas vazias e cabeçalhos ausentes; ela para se encontrar cabeçalhos incompatíveis.
5. Garanta saída HTTPS para Telegram, Google APIs e o provider de IA escolhido. Long polling não exige webhook público; o processo precisa permanecer ativo.

O processo deve ter **um único worker**: o bloqueio de escrita é local ao processo, e o Google Sheets não oferece transação nem restrição única. `GET /health` retorna `503` se o polling do Telegram estiver parado. O endpoint não valida a saúde posterior da planilha ou do provider de IA.

## Fluxo

Envie texto ou áudio em português no chat privado do bot. Chats de grupo são recusados para evitar expor dados da fazenda a participantes que não estão na whitelist. O bot pede esclarecimentos quando faltam campos; eventos elegíveis são gravados após validação, e os que exigem confirmação mostram uma prévia antes da gravação. `/historico <identificador>` consulta os eventos recentes. `/cancel` descarta a última solicitação pendente. O arquivo de áudio fica apenas em memória durante a transcrição; o texto transcrito e metadados de origem são persistidos na planilha. Falhas de download/transcrição ficam auditadas com a referência do áudio, sem salvar os bytes. Configure acesso e retenção da planilha de acordo com esses dados.

Expressões `hoje`, `ontem` e `amanhã` usam o fuso de `FARM_TIMEZONE`. Se a fala não trouxer data, cadastro, entrada, parto, transferência, vacinação e observação recebem o dia local da propriedade no momento da captura; pesagens exigem data explícita. Expressões de data que o sistema não reconhece pedem esclarecimento.

Escopo: nascimento/cadastro, entrada, parto, pesagem, transferência de lote, vacinação reportada (para um animal ou lote identificado) e observação de saúde reportada. Correções simples mostram o evento e valor anterior na prévia e só gravam após confirmação. O histórico individual considera a alocação do animal no lote na data do evento. O sistema não diagnostica nem executa protocolos veterinários.

## Métricas

Com a planilha configurada, execute `agro-notes-metrics` para gerar um snapshot JSON de esclarecimentos, correções, duplicações, efeitos parciais/revertidos, consultas ao histórico e tempo até gravação. Acurácia de intenção, slots, resolução de animal e utilidade de esclarecimento ficam `null` até haver anotações humanas do golden set; os números são descritivos e não definem gates arbitrários.

Para comparar os modelos de interpretação de produção `openai/gpt-oss-20b` e `openai/gpt-oss-120b` realmente ativos na conta Groq, configure `GROQ_API_KEY` e execute `agro-notes-evaluate-groq`. O relatório usa o golden set sintético e inclui acerto, schema, erros, retry, latência e custo estimado com a tabela de preços Groq consultada em 2026-10-13. Modelos preview não entram na seleção automática. Se somente um estiver ativo, o relatório indica `SINGLE_MODEL_AVAILABLE`. Sem chave, não há chamada externa. O caso de duplicidade fica a cargo da suíte de integração local, pois idempotência pertence ao app e não ao modelo.

Para comparar `whisper-large-v3-turbo` e `whisper-large-v3` em áudio próprio, copie [o exemplo de manifesto](docs/stt-evaluation-manifest.example.json), substitua os caminhos por áudios PT-BR locais e confira as transcrições de referência; execute `agro-notes-evaluate-stt caminho/manifesto.json`. O relatório não inclui áudio nem transcrição, apenas WER, recall de termos críticos, latência, erros, retries e custo estimado. Use gravações que cubram voz limpa/baixa, duração curta/longa, ruído, fala rápida, sotaques, números, animais e lotes; não há gravações reais versionadas neste repositório.

Os smoke tests são `agro-notes-evaluate-groq`, `agro-notes-evaluate-stt`, `agro-notes-smoke-telegram` (valida `getMe`, sem enviar mensagem) e `agro-notes-smoke-sheets` (valida o bootstrap e cria/lê/apaga uma aba temporária). Para validar recebimento real do Telegram, inicie o app e envie `/start`, texto, voz e callbacks com um usuário autorizado; o smoke `getMe` sozinho não prova recebimento.

A integração usa a [API OpenAI-compatible da Groq](https://console.groq.com/docs/openai), a [API Groq Speech to Text](https://console.groq.com/docs/speech-to-text), o conjunto documentado de [Structured Outputs](https://console.groq.com/docs/structured-outputs) e o [catálogo de modelos e preços](https://console.groq.com/docs/models). Logs de provider registram provider, modelo, latência, resultado, validade de schema, retries, request ID e uso/duração quando fornecidos, sem chave, prompt ou transcrição.

## Limitações operacionais

- A planilha precisa estar no schema esperado; bootstrap não migra dados existentes.
- O cabeçalho `06_Eventos` inclui `time_source`. Antes de iniciar com uma planilha existente, insira uma coluna inteira nessa posição e defina o cabeçalho `time_source`; não renomeie uma coluna existente, pois isso deslocaria o significado dos dados históricos. Marque as linhas legadas como `UNKNOWN_LEGACY` (a origem não pode ser reconstruída com segurança). O bootstrap interrompe a inicialização diante de cabeçalhos incompatíveis.
- Escritas em várias abas podem falhar parcialmente. O bot registra efeitos e exige reconciliação manual em vez de repetir automaticamente.
- Botões de confirmação carregam um identificador de comando persistido e são vinculados à mensagem enviada, ao chat e ao usuário. Confirmações antigas deixam de valer quando o estado pendente é encerrado ou substituído.
- A confirmação de ponta a ponta requer credenciais e uma planilha/bot reais; testes locais usam serviços simulados.
