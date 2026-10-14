# Agro Notes

MVP de captura de eventos de manejo animal por Telegram, com interpretação estruturada, validação determinística, confirmação e armazenamento append-only no Google Sheets.

## Requisitos

- Python 3.11 ou superior
- Token de bot Telegram e códigos de convite para cadastro
- Chave Groq (provider inicial) ou OpenAI
- Planilha Google compartilhada com o e-mail da service account
- JSON de credenciais da service account salvo localmente

## Configuração

1. Crie e ative um ambiente virtual; instale `pip install -e .`. Para desenvolvimento, use `pip install -e '.[dev]'`.
2. Copie `.env.example` para `.env` e preencha os segredos e `GOOGLE_SHEET_ID`. `TELEGRAM_ALLOWED_USER_IDS` é opcional e serve somente para migrar usuários antigos no primeiro acesso; convites novos são administrados pelo comando abaixo. Groq é o provider inicial para interpretação e transcrição; defina `INTERPRETATION_PROVIDER` e `TRANSCRIPTION_PROVIDER` independentemente como `groq` ou `openai` para selecionar cada integração. Os nomes anteriores `AI_PROVIDER`, `FARM_PROPERTY_ID`, `FARM_TIMEZONE`, `GOOGLE_CREDENTIALS_FILE` e `GROQ_MODEL` continuam aceitos como aliases. Os modelos Groq são configuráveis.
3. Coloque o JSON de service account no caminho de `GOOGLE_CREDENTIALS_FILE`; compartilhe a planilha com o e-mail `client_email` do JSON, com permissão de editor.
4. Inicie com `uvicorn agro_notes.main:app --host 0.0.0.0 --port 8000 --workers 1 --no-access-log`. A inicialização cria abas vazias e cabeçalhos ausentes; ela para se encontrar cabeçalhos incompatíveis.
5. Garanta saída HTTPS para Telegram, Google APIs e o provider de IA escolhido. Long polling não exige webhook público; o processo precisa permanecer ativo.

O processo deve ter **um único worker**: o bloqueio de escrita é local ao processo, e o Google Sheets não oferece transação nem restrição única. `GET /health` retorna `503` se o polling do Telegram estiver parado. O endpoint não valida a saúde posterior da planilha ou do provider de IA.

## Fluxo

No primeiro contato privado, envie `/start` e depois `/acesso SEU_CODIGO`. O código é consumido uma vez (ou até o limite configurado), e a autorização fica vinculada ao ID numérico do Telegram. Códigos, resgates, tentativas e revogações ficam na aba `Telegram_Access`; somente o hash SHA-256 do convite é armazenado. Gere um convite com `python -m agro_notes.access_admin create-code --expires-in-hours 72 --max-uses 1`; o código é exibido uma única vez. O comando requer credenciais de serviço Google e acesso de escrita à planilha. Guarde o `ID para revogação` exibido para uso em `python -m agro_notes.access_admin revoke-code <ID>`. Revogue uma pessoa com `python -m agro_notes.access_admin revoke-user <TELEGRAM_USER_ID>`. Compartilhe o convite apenas em canal privado.

Execute `revoke-code` na mesma máquina e ambiente de arquivos do bot, com o bot parado. Um bloqueio local SQLite impede que esse comando rode enquanto a instância do bot estiver ativa; uma implantação em outra máquina precisa primeiro parar o bot nela antes de executar a revogação.

Envie texto ou áudio em português no chat privado do bot. Chats de grupo são recusados. O bot pede esclarecimentos quando faltam campos; eventos elegíveis são gravados após validação, e os que exigem confirmação mostram uma prévia antes da gravação. Pesagens recebidas por voz sempre exigem confirmação explícita após a prévia, pois o provider STT não fornece uma confiança calibrada para validar números reconhecidos. `/historico <identificador>` consulta os eventos recentes. `/cancel` descarta a última solicitação pendente. O arquivo de áudio fica apenas em memória durante a transcrição; o texto transcrito e metadados de origem são persistidos na planilha. Falhas de download/transcrição ficam auditadas com a referência do áudio, sem salvar os bytes. Configure acesso e retenção da planilha de acordo com esses dados.

Expressões `hoje`, `ontem` e `amanhã` usam o fuso de `FARM_TIMEZONE`. Se a fala não trouxer data, cadastro, entrada, parto, transferência, vacinação e observação recebem o dia local da propriedade no momento da captura; pesagens exigem data explícita. Expressões de data que o sistema não reconhece pedem esclarecimento.

Para conectar o Drive pessoal e salvar uma exportação XLSX, configure as credenciais OAuth seguindo [docs/GOOGLE_DRIVE_OAUTH_SETUP.md](docs/GOOGLE_DRIVE_OAUTH_SETUP.md). A planilha Google do Agro Notes continua sendo a fonte de verdade; o Drive pessoal recebe somente exportações.

Escopo: nascimento/cadastro, entrada, parto, pesagem, transferência de lote, vacinação reportada (para um animal ou lote identificado) e observação de saúde reportada. Correções simples mostram o evento e valor anterior na prévia e só gravam após confirmação. O histórico individual considera a alocação do animal no lote na data do evento. O sistema não diagnostica nem executa protocolos veterinários.

## Métricas

Com a planilha configurada, execute `agro-notes-metrics` para gerar um snapshot JSON de esclarecimentos, correções, duplicações, efeitos parciais/revertidos, consultas ao histórico e tempo até gravação. Acurácia de intenção, slots, resolução de animal e utilidade de esclarecimento ficam `null` até haver anotações humanas do golden set; os números são descritivos e não definem gates arbitrários.

Para comparar os modelos de interpretação de produção `openai/gpt-oss-20b` e `openai/gpt-oss-120b` realmente ativos na conta Groq, configure `GROQ_API_KEY` e execute `agro-notes-evaluate-groq`. O relatório usa o golden set sintético e inclui acerto, schema, erros, retry, latência e custo estimado com a tabela de preços Groq consultada em 2026-10-13. Modelos preview não entram na seleção automática. Se somente um estiver ativo, o relatório indica `SINGLE_MODEL_AVAILABLE`. Sem chave, não há chamada externa. O caso de duplicidade fica a cargo da suíte de integração local, pois idempotência pertence ao app e não ao modelo.

Para comparar `whisper-large-v3-turbo` e `whisper-large-v3` em áudio próprio, copie [o exemplo de manifesto](docs/stt-evaluation-manifest.example.json), substitua os caminhos por áudios PT-BR locais e confira as transcrições de referência; execute `agro-notes-evaluate-stt caminho/manifesto.json`. O manifesto precisa conter casos e arquivos de áudio existentes; aliases explícitos permitem comparar formas faladas e numéricas (como “lote sete” e “lote 7”) sem alterar a transcrição de referência. Marque cada caso com `matrix_tags`; o harness só recomenda vencedor depois de cobrir voz limpa/baixa, duração curta/longa, ruído, fala rápida, sotaques, números, animais e lotes. O exemplo não cobre áudio longo nem sotaques e não inclui gravações reais, que devem ser fornecidas e rotuladas por uma pessoa. O relatório não inclui áudio nem transcrição, apenas WER, recall de termos críticos, latência, erros, retries e custo estimado.

Para preparar a futura rodada de fala rural, consulte [`FIELD_EVAL_V1`](docs/FIELD_EVAL_SPEC.md), o [protocolo de gravação](docs/FIELD_RECORDING_PROTOCOL.md), as [métricas](docs/FIELD_METRICS.md) e o [modelo de risco](docs/FIELD_RISK_MODEL.md). O corpus em `eval/field_eval_v1.jsonl` contém 150 casos **sintéticos**, não evidência de fala de campo. Valide-o sem credenciais com `agro-notes-field-eval validate`; o comando `agro-notes-field-eval demo` apenas demonstra as métricas em uma previsão deliberadamente errada e não valida modelo algum. Para pontuar previsões text-only, use `agro-notes-field-eval evaluate --predictions <arquivo.jsonl>`.

Os smoke tests são `agro-notes-evaluate-groq`, `agro-notes-evaluate-stt`, `agro-notes-smoke-telegram` e `agro-notes-smoke-sheets` (valida o bootstrap e cria/lê/apaga uma aba temporária). O smoke do Telegram confere `getMe`, recusa webhook ou atualizações antigas pendentes e aguarda até 30 segundos por um código enviado de um chat privado por um usuário autorizado. Rode-o com o app parado para evitar conflito de polling; ele confirma o recebimento, responde ao chat e reconhece somente a atualização de desafio. Depois, inicie o app e valide `/start`, texto, voz e callbacks no E2E.

A integração usa a [API OpenAI-compatible da Groq](https://console.groq.com/docs/openai), a [API Groq Speech to Text](https://console.groq.com/docs/speech-to-text), o conjunto documentado de [Structured Outputs](https://console.groq.com/docs/structured-outputs) e o [catálogo de modelos e preços](https://console.groq.com/docs/models). Logs de provider registram provider, modelo, latência, resultado, validade de schema, retries, request ID e uso/duração quando fornecidos, sem chave, prompt ou transcrição.

## Limitações operacionais

- A planilha precisa estar no schema esperado; bootstrap não migra dados existentes.
- O cabeçalho `06_Eventos` inclui `time_source`. Antes de iniciar com uma planilha existente, insira uma coluna inteira nessa posição e defina o cabeçalho `time_source`; não renomeie uma coluna existente, pois isso deslocaria o significado dos dados históricos. Marque as linhas legadas como `UNKNOWN_LEGACY` (a origem não pode ser reconstruída com segurança). O bootstrap interrompe a inicialização diante de cabeçalhos incompatíveis.
- Escritas em várias abas podem falhar parcialmente. O bot registra efeitos e exige reconciliação manual em vez de repetir automaticamente.
- Botões de confirmação carregam um identificador de comando persistido e são vinculados à mensagem enviada, ao chat e ao usuário. Confirmações antigas deixam de valer quando o estado pendente é encerrado ou substituído.
- A confirmação de ponta a ponta requer credenciais e uma planilha/bot reais; testes locais usam serviços simulados.
