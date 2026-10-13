# Agro Notes

MVP de captura de eventos de manejo animal por Telegram, com interpretação estruturada, validação determinística, confirmação e armazenamento append-only no Google Sheets.

## Requisitos

- Python 3.11 ou superior
- Token de bot Telegram e ID(s) numéricos autorizados
- Chave OpenAI
- Planilha Google compartilhada com o e-mail da service account
- JSON de credenciais da service account salvo localmente

## Configuração

1. Crie e ative um ambiente virtual; instale `pip install -e .`. Para desenvolvimento, use `pip install -e '.[dev]'`.
2. Copie `.env.example` para `.env` e preencha os segredos e `GOOGLE_SHEET_ID`. `TELEGRAM_ALLOWED_USER_IDS` aceita IDs separados por vírgulas.
3. Coloque o JSON de service account no caminho de `GOOGLE_CREDENTIALS_FILE`; compartilhe a planilha com o e-mail `client_email` do JSON, com permissão de editor.
4. Inicie com `uvicorn agro_notes.main:app --host 0.0.0.0 --port 8000 --workers 1`. A inicialização cria abas vazias e cabeçalhos ausentes; ela para se encontrar cabeçalhos incompatíveis.
5. Garanta saída HTTPS para Telegram, Google APIs e OpenAI. Long polling não exige webhook público; o processo precisa permanecer ativo.

O processo deve ter **um único worker**: o bloqueio de escrita é local ao processo, e o Google Sheets não oferece transação nem restrição única. `GET /health` retorna `503` se o polling do Telegram estiver parado. O endpoint não valida a saúde posterior da planilha ou da API OpenAI.

## Fluxo

Envie texto ou áudio em português no chat privado do bot. Chats de grupo são recusados para evitar expor dados da fazenda a participantes que não estão na whitelist. O bot pede esclarecimentos quando faltam campos; eventos elegíveis são gravados após validação, e os que exigem confirmação mostram uma prévia antes da gravação. `/historico <identificador>` consulta os eventos recentes. `/cancel` descarta a última solicitação pendente. O arquivo de áudio fica apenas em memória durante a transcrição; o texto transcrito e metadados de origem são persistidos na planilha. Falhas de download/transcrição ficam auditadas com a referência do áudio, sem salvar os bytes. Configure acesso e retenção da planilha de acordo com esses dados.

Expressões `hoje`, `ontem` e `amanhã` usam o fuso de `FARM_TIMEZONE`. Se a fala não trouxer data, cadastro, entrada, parto, transferência, vacinação e observação recebem o dia local da propriedade no momento da captura; pesagens exigem data explícita. Expressões de data que o sistema não reconhece pedem esclarecimento.

Escopo: nascimento/cadastro, entrada, parto, pesagem, transferência de lote, vacinação reportada (para um animal ou lote identificado) e observação de saúde reportada. Correções simples mostram o evento e valor anterior na prévia e só gravam após confirmação. O histórico individual considera a alocação do animal no lote na data do evento. O sistema não diagnostica nem executa protocolos veterinários.

## Métricas

Com a planilha configurada, execute `agro-notes-metrics` para gerar um snapshot JSON de esclarecimentos, correções, duplicações, efeitos parciais/revertidos, consultas ao histórico e tempo até gravação. Acurácia de intenção, slots, resolução de animal e utilidade de esclarecimento ficam `null` até haver anotações humanas do golden set; os números são descritivos e não definem gates arbitrários.

## Limitações operacionais

- A planilha precisa estar no schema esperado; bootstrap não migra dados existentes.
- O cabeçalho `06_Eventos` inclui `time_source`. Antes de iniciar com uma planilha existente, insira uma coluna inteira nessa posição e defina o cabeçalho `time_source`; não renomeie uma coluna existente, pois isso deslocaria o significado dos dados históricos. Marque as linhas legadas como `UNKNOWN_LEGACY` (a origem não pode ser reconstruída com segurança). O bootstrap interrompe a inicialização diante de cabeçalhos incompatíveis.
- Escritas em várias abas podem falhar parcialmente. O bot registra efeitos e exige reconciliação manual em vez de repetir automaticamente.
- Botões de confirmação carregam um identificador de comando persistido e são vinculados à mensagem enviada, ao chat e ao usuário. Confirmações antigas deixam de valer quando o estado pendente é encerrado ou substituído.
- A confirmação de ponta a ponta requer credenciais e uma planilha/bot reais; testes locais usam serviços simulados.
