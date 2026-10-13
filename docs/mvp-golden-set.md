# MVP-GOLDEN-SET

Frases de referência da especificação. Estes casos aguardam rotulagem humana para avaliação do interpretador; a suíte automatizada testa validação determinística e aplicação com propostas fixas, sem chamar um modelo pago. Não há meta de acurácia definida.

As expressões `hoje`, `ontem` e `amanhã` são resolvidas no fuso da propriedade. Quando a fala não informa uma data, cadastro, entrada, parto, transferência, vacinação e observação usam o dia local da propriedade no momento da captura. Pesagem exige data explícita, como no golden set. Expressões de data desconhecidas continuam pedindo esclarecimento; a expressão original, quando existe, permanece no evento.

| Fala | Família esperada | Slots essenciais | Política esperada |
|---|---|---|---|
| Cadastre a vaca 184. | `ANIMAL_CREATED` | `display_identifier=184`, `species=BOVINE` | `CONFIRM` |
| A vaca 184 entrou hoje. | `ANIMAL_ENTERED` | animal 184, data hoje | `CONFIRM` |
| A 184 pesou 512 kg hoje. | `WEIGHING` | animal 184, `weight_kg=512`, hoje | `AUTO_APPLY` |
| Pesei a 184. | `WEIGHING` | animal 184; peso ausente | `NEEDS_CLARIFICATION` |
| A 184 pesou quinhentos e doze quilos. | `WEIGHING` | animal 184, `weight_kg=512`; data ausente | `NEEDS_CLARIFICATION` |
| Não era 87 kg, era 78. | `WEIGHING` | corrigir a última pesagem aplicada e inequívoca do usuário; preservar alvo/data e ligar por `correction_of` | `CONFIRM`; sem evento anterior compatível, `NEEDS_CLARIFICATION` |
| Passei a 184 para o lote 7. | `LOT_TRANSFER` | animal 184, destino 7 | `CONFIRM` |
| A 184 foi pro lote sete hoje. | `LOT_TRANSFER` | animal 184, destino 7, hoje | `CONFIRM` |
| Passei ela pro sete. | `LOT_TRANSFER` | animal e lote ambíguos | `NEEDS_CLARIFICATION` |
| A 184 pariu hoje. | `CALVING` | matriz 184; outcomes ausentes | `NEEDS_CLARIFICATION` |
| A 184 pariu uma fêmea. | `CALVING` | matriz 184; um outcome vivo, fêmea, sem identificador falado | `CONFIRM` |
| A 184 pariu uma fêmea número 391. | `CALVING` | matriz 184; cria viva, fêmea, identificador 391 | `CONFIRM` |
| A 184 pariu gêmeos. | `CALVING` | matriz 184; dois outcomes | `NEEDS_CLARIFICATION` se os resultados individuais faltarem |
| A 184 está mancando. | `HEALTH_OBSERVATION` | animal 184, sinal reportado | `AUTO_APPLY` |
| A 184 está machucada na pata traseira direita. | `HEALTH_OBSERVATION` | animal 184, observação e região reportadas | `AUTO_APPLY` |
| A 184 está doente desde ontem. | `HEALTH_OBSERVATION` | animal 184, observação, data ontem | `AUTO_APPLY` |
| Vacinei a 184 contra clostridiose. | `VACCINATION` | animal 184, produto relatado | `CONFIRM` |
| Vacinei a 184 hoje. | `VACCINATION` | animal 184, produto ausente, hoje | `NEEDS_CLARIFICATION` |
| Vacinei o lote. | `VACCINATION` | alvo é grupo; lote específico ausente | `NEEDS_CLARIFICATION` |
| Vacinei a vaca errada. | fora do escopo sem contexto corrigível | sem alvo inequívoco | rejeitar/clarificar; nunca adivinhar |

## Medidas a coletar

Registrar para cada avaliação: resolução de animal, acerto de intenção, extração de slots, taxa de esclarecimento e utilidade do esclarecimento, correções solicitadas, duplicações de evento, efeitos parciais, correções/reversões, tempo até gravação e sucesso de consulta. Os eventos e auditorias já guardam IDs, estado, alvos, respostas e resultados para derivar a maior parte dessas medidas; confiança de transcrição permanece indisponível quando o provedor não a retornar.
