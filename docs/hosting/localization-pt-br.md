# Localização em português do Brasil

O farmOS usa os módulos de idioma e tradução do Drupal. O módulo opcional
**farmOS Localization** (`farm_l10n`) habilita `Language`, `Interface
Translation` (`locale`) e `Configuration Translation`. Ele atualiza as
traduções automaticamente a cada 30 dias e permite escolher o idioma padrão da
interface em **Configurações da fazenda > Idioma**. O perfil mantém inglês como
idioma base da configuração do site; a opção **Idioma selecionado** controla a
interface e pode ser definida como português do Brasil (`pt-br`).

## Ativar português do Brasil

1. Habilite o módulo `farm_l10n` em **Estender** ou execute `drush en
   farm_l10n -y` na raiz da instalação.
2. Acesse **Configuração > Regional e idioma > Idiomas** e adicione
   **Português (Brasil)**. Aguarde o download das traduções disponíveis.
3. Em **Configurações da fazenda > Idioma**, selecione português do Brasil como
   idioma padrão da interface. Se desejar, use a opção para atualizar o idioma
   dos usuários existentes; cada usuário pode escolher outro idioma no perfil.

O projeto já seleciona a negociação **Idioma selecionado** em farmOS. Essa
configuração mantém uma escolha explícita para a interface em vez de inferir o
idioma pelo navegador. A documentação oficial do Drupal descreve a adição de
idiomas e o download das traduções [na tela de idiomas](https://www.drupal.org/docs/user_guide/en/language-add.html).

## Formatos regionais

Em **Configuração > Regional e idioma > Configurações regionais**, escolha
**Brasil** como país padrão. O [guia do Drupal sobre configurações regionais](https://www.drupal.org/docs/user_guide/en/config-basic.html)
documenta esse ajuste. Isso não define o fuso horário da propriedade:
selecione o fuso IANA que corresponde à localização da fazenda em
**Configurações da fazenda > Informações da fazenda**. O Brasil tem mais de um
fuso horário, portanto não há um valor único apropriado para todas as
instalações.

Em **Configuração > Regional e idioma > Formatos de data**, revise os formatos
curto, médio e longo. Como ponto de partida para a interface, use `d/m/Y` no
formato curto (por exemplo, `22/10/2026`); nos formatos por extenso, use os
códigos de data do PHP e confirme a apresentação com a interface em português.
O [guia do módulo DateTime do Drupal](https://www.drupal.org/docs/8/core/modules/datetime/datetime-overview)
documenta onde ajustar os formatos de data. O Drupal 11 também mudou seus padrões
de data de instalação para formatos mais reconhecíveis internacionalmente; por
isso, não presuma que uma instalação já existente herdou um formato
brasileiro.

Para quantidades na interface em português, use a vírgula como separador
decimal. A edição luso-brasileira do [Sistema Internacional de Unidades do
Inmetro](https://www.gov.br/inmetro/pt-br/assuntos/metrologia-cientifica/documentos-tecnicos-em-metrologia/si_versao_final.pdf/view)
recomenda espaço para agrupar milhares em textos técnicos e esclarece que a
convenção de escrita pode variar em dados e sistemas computacionais. Revise os
formatadores numéricos de campos e listas que sua instalação usa, pois seus
separadores podem ser configurados por campo ou visualização. Não converta
valores da API ou arquivos CSV: o farmOS armazena e importa decimais com ponto,
independentemente da apresentação localizada.

## Unidades e vocabulário rural

Em **Configurações da fazenda > Quantidade**, mantenha **Métrico** para uma
instalação brasileira. Essa opção já é o padrão do farmOS. Ela não converte
automaticamente registros existentes nem traduz termos da taxonomia de
unidades. Cadastre unidades usadas pela operação e preserve símbolos
reconhecidos, como `kg`, `L`, `m` e `ha`; mantenha um espaço entre o valor e o
símbolo (por exemplo, `12,3 kg`). Consulte o [SI em português publicado pelo
Inmetro](https://www.gov.br/inmetro/pt-br/assuntos/metrologia-cientifica/documentos-tecnicos-em-metrologia/si_versao_final.pdf/view)
para grafia e símbolos.

Para revisar traduções rurais, considere o contexto agronômico. A Embrapa
registra que **semeadura** e **plantio** podem ser usados de modo sobreposto,
mas também distingue semeadura de plantio em certas operações e culturas;
evite definir uma equivalência única para todos os formulários. Para colocar
mudas no local de cultivo, use **transplante**; para retirar o produto, use
**colheita**. O [Caderno de Campo da Produção Integrada da Cebola do MAPA](https://www.gov.br/agricultura/pt-br/assuntos/sustentabilidade/producao-integrada/arquivos-publicacoes-producao-integrada/caderno-de-campo-rt.pdf/%40%40download/file)
usa “semeadura (ou plantio)” e “transplante de mudas”; a Embrapa discute a
distinção contextual entre [semeadura direta e plantio direto](https://www.embrapa.br/en/web/agencia-de-informacao-tecnologica/tematicas/sistema-plantio-direto/fundamentos/conceitos/semeadura-direta-e-plantio-direto).

As traduções de interface vêm do servidor de traduções do Drupal e do projeto
farmOS; não são incluídas como um catálogo local neste repositório. O
[servidor de traduções do Drupal](https://localize.drupal.org/) lista português
do Brasil para o Drupal 11.4.10, que é a versão declarada neste projeto, mas
isso não garante cobertura de todas as strings do farmOS ou de módulos
adicionais. Consulte o [estado da tradução farmOS por versão](https://localize.drupal.org/translate/projects/farm)
antes de adotar o idioma: strings sem tradução aparecem no idioma de origem.
Termos agronômicos fora desse escopo, nomes de cultivares e unidades locais
devem ser revisados por falantes familiarizados com a operação antes de serem
adicionados como traduções personalizadas.
