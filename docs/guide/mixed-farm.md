# Começar com uma fazenda de lavoura e pecuária

O farmOS usa os mesmos ativos, locais e registros para lavoura e pecuária. A
etapa **Instalar módulos** do assistente de configuração pode habilitar os dois
lados de uma operação mista; não é necessário criar outro perfil ou fork.

Como ponto de partida, selecione estas opções no assistente:

| Seção do assistente | Selecione | O que habilita |
| --- | --- | --- |
| O que você faz? | Plantas | Ativos de planta e registros de tipos de planta |
| Complemento de plantas | Cultivar plantas a partir de sementes | Registro de semeadura e formulário rápido de plantio |
| Complemento de plantas | Transplantar | Registro de transplante e formulário rápido de plantio |
| O que você faz? | Animais | Ativos de animais e registros de tipos de animal |
| Complemento de animais | Acompanhar nascimentos | Registro de nascimento e formulário rápido de nascimento |
| Complemento de animais | Acompanhar registros médicos | Registro médico |
| Complemento de animais | Acompanhar movimentação de animais | Registro de atividade e formulário rápido de movimentação |
| Onde você faz isso? | Terra | Ativos de área e tipos padrão de propriedade, campo, canteiro, piquete e marco |
| Quais eventos registra? | Atividades gerais | Registros de atividade para trabalhos sem um tipo especializado |
| Quais eventos registra? | Colheitas | Registros de colheita |

O assistente também habilita o tipo padrão de quantidade quando módulos de
registro são selecionados. Os tipos padrão de área organizam registros de
plantas e animais. Use ativos individuais de Planta e Animal quando essas forem
as unidades de manejo; adicione grupos ou recursos de inventário se precisar
acompanhar rebanhos, lotes ou contagens de animais em conjunto.

## Adicionar quando necessário

Mantenha a configuração inicial enxuta e adicione estes módulos pela tela de
módulos do farmOS quando a operação precisar:

- **Insumos e inventário de materiais:** registros de insumo e ativos de material.
- **Animais em grupo ou por contagem:** ativos de grupo, observações e
  formulários rápidos de inventário.
- **Análises de solo ou água:** registros de testes laboratoriais e locais de
  terra ou água.
- **Estruturas e equipamentos:** registros de construções, estufas, equipamentos
  e manutenção.
- **Sementes, produtos e outros estoques:** os módulos de ativos e inventário
  correspondentes.
- **Acesso à API, integrações e camadas de mapa externas:** habilite somente
  quando uma integração ou provedor for escolhido.

Essas opções habilitam módulos existentes do farmOS. A
[demonstração local em Docker](../hosting/local-preview.md) instala o mesmo
conjunto inicial; o acesso sem login fica restrito a essa demonstração local de
uma pessoa e não faz parte da autenticação normal do farmOS nem da configuração
de produção.
