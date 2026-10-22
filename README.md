# Agro Notes — runtime local de testes

Esta branch remove o bot do Telegram e a integração com Google Drive para permitir exercitar o núcleo de registros pecuários localmente. A CLI usa propostas JSON explícitas, validação determinística e um armazenamento em memória. Ela não inicia serviços, não lê `.env` e não chama Telegram, Google Drive, Google Sheets ou provedores de IA.

## Requisitos

- Python 3.11 ou superior
- Dependências do projeto instaladas (`pip install -e '.[dev]'`)

## Executar

```sh
agro-notes-local --property-id FAZENDA-001 --actor-id 7
```

Também é possível executar sem instalar o pacote:

```sh
PYTHONPATH=src python -m agro_notes.local_cli --property-id FAZENDA-001 --actor-id 7
```

A entrada e a saída usam JSON Lines: envie uma ação JSON por linha. O comando fica aberto até receber EOF (`Ctrl-D` no terminal).

### Fluxo de exemplo

```json
{"action":"record","message_id":"animal-001","captured_at":"2026-10-22T12:00:00Z","proposal":{"events":[{"event_type":"ANIMAL_CREATED","payload":{"display_identifier":"42","species":"CATTLE"},"time_expression":"hoje","confidence":0.99}]}}
{"action":"confirm","pending_id":"LOCAL:7:animal-001"}
{"action":"record","message_id":"weight-001","captured_at":"2026-10-22T12:01:00Z","proposal":{"events":[{"event_type":"WEIGHING","payload":{"animal_identifier":"42","weight_kg":701},"time_expression":"hoje","confidence":0.99}]}}
{"action":"confirm","pending_id":"LOCAL:7:weight-001"}
{"action":"inspect"}
```

Cada linha é uma ação. Os `pending_id` deste exemplo correspondem aos `message_id` fornecidos; em outros casos, use o valor retornado pela CLI. Em uma execução separada, se a CLI retornar `LOCAL:7:cancel-001` para uma prévia ainda pendente, descarte-a assim:

```json
{"action":"cancel","pending_id":"LOCAL:7:cancel-001"}
```

O `actor-id` é uma identidade local escolhida explicitamente no comando. Os registros existem apenas na memória do processo e desaparecem quando ele termina. O interpretador aceita propostas já estruturadas em JSON; esta branch não interpreta texto livre nem áudio.

## Verificação local

```sh
python -m pytest -q
```

O armazenamento Google Sheets continua disponível como módulo legado isolado, mas a CLI local não o usa para conexão nem lê credenciais. Os comandos de avaliação de modelos são separados e podem enviar fixtures sintéticas a provedores quando executados explicitamente; a CLI local não os chama.
