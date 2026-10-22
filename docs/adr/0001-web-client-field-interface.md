# Interface web própria para operações de campo

Status: proposed — construir somente um protótipo se os gates de viabilidade descritos abaixo forem atendidos.

Para reduzir atrito em celular e oferecer um conjunto curto de fluxos em português brasileiro, a recomendação é avaliar um cliente React/TypeScript complementar, limitado a operações de campo e conectado ao farmOS pela API JSON:API. O Drupal continuaria como interface completa, backend, fonte única dos dados e lugar para administração; esta proposta não autoriza iniciar uma interface de produção antes da validação do protótipo. O MVP não promete uso offline. Rust/WASM fica fora do escopo enquanto não houver benchmark que demonstre um gargalo computacional relevante.

## Contexto e evidências

O repositório já tem telas e fluxos Drupal para painel, tarefas pendentes, busca/listagem de registros, Assets, Logs, Quantities, locais, inventário, quick forms e administração. Os guias descrevem Assets e Logs como registros centrais e quick forms como caminhos focados que escrevem sobre o mesmo modelo flexível de Asset/Log. Ver [navegação](../guide/index.md), [quick forms](../guide/quick.md), [Assets](../guide/assets.md), [Logs](../guide/logs.md), [localização](../guide/location.md), [inventário](../guide/inventory.md), [mapas](../guide/mapping.md) e [quantidades](../guide/quantities.md).

O `farm_api` usa JSON:API do Drupal: `/api` anuncia recursos disponíveis e metadados do servidor, `/api/schema` descreve os esquemas, e os recursos são endereçados por tipo e bundle. Os esquemas e campos podem variar conforme instalação e módulos ativos; portanto, não se deve codificar a suposição de que toda fazenda tem o mesmo conjunto de recursos. O repositório também documenta filtros, paginação e ordenação em [API](../development/api/index.md). A API e o servidor OAuth são componentes configuráveis; em instalações farmOS 4, confirmar que ambos estão habilitados e configurados é pré-requisito.

O módulo Quick expõe o recurso de configuração `quick_form` na API ([`ApiHooks.php`](../../modules/core/quick/src/Hook/ApiHooks.php)); isso não equivale a expor a execução do formulário Drupal como operação JSON:API. Quick forms como Inventário e Plantio contêm lógica de apresentação, validação e criação coordenada de entidades no servidor ([Inventory.php](../../modules/quick/inventory/src/Plugin/QuickForm/Inventory.php), [Planting.php](../../modules/quick/planting/src/Plugin/QuickForm/Planting.php)). Uma tela React que substitua esses formulários deve reproduzir os passos de gravação usando operações API suportadas e testar seus efeitos, ou manter esse fluxo no Drupal. Não presumir que o endpoint de entidade representa a lógica do plugin.

## Telas e fluxos candidatos

Este é um escopo de descoberta para uma experiência simples em pt-BR, não um requisito de paridade com todo o farmOS. Usar rótulos diretos e consistentes com o idioma do usuário; manter nomes e valores persistidos conforme o contrato da API. Priorizar controles grandes, formulários curtos, feedback explícito de gravação e compatibilidade com telas estreitas. Confirmar os fluxos com pessoas usuárias antes de congelar o MVP.

| Prioridade | Tela/fluxo em pt-BR | Dados e decisões necessárias |
| --- | --- | --- |
| Essencial | Conectar à fazenda e entrar | Informar URL da instância, iniciar OAuth, exibir erros de conexão e encerrar sessão. O formulário de login não deve coletar senha para usar Password Grant sem justificativa e validação de segurança. |
| Essencial | Hoje / tarefas | Consultar Logs pendentes atrasados ou próximos, abrir um registro e marcá-lo como concluído ou atualizar a data. O repositório define essas listas no painel. |
| Essencial | Encontrar local ou item | Busca por nome e tipo; exibir local atual e estado arquivado quando disponível. Seleção de Asset deve respeitar as permissões da API. |
| Essencial | Registrar atividade ou observação | Data, tipo, um ou mais Assets relacionados, local/movimento quando necessário, nota, quantidade opcional e estado pendente/concluído. Confirmar os campos usados na operação-piloto. |
| Essencial | Consultar detalhe e histórico | Identificação do Asset, relações relevantes, localização atual e Logs associados; suportar paginação e estados vazios/erro. |
| Condicional | Ajustar inventário | Selecionar Asset, quantidade, medida/unidade e incremento, decremento ou redefinição. A gravação é um Log com Quantity e o inventário resultante depende dos Logs concluídos. |
| Posterior | Plantio, nascimento e outros fluxos compostos | Esses quick forms podem criar vários registros relacionados e executar regras específicas. Mantê-los no Drupal até provar que as operações JSON:API necessárias e a sequência de gravação são equivalentes. |
| Posterior | Mapa e edição de geometria | A interface Drupal oferece mapa, GPS, desenho de geometria e hierarquia de locais. Recriar essas capacidades eleva custo; deixar fora do primeiro MVP, exceto se a pesquisa de campo provar que são centrais. |
| Posterior | Relatórios, configuração, gestão de usuários e taxonomias | Permanecem na interface Drupal. Não duplicar administração no cliente. |

## Opções consideradas

| Opção | Custo inicial e manutenção | Vantagens | Riscos/limites |
| --- | --- | --- | --- |
| Manter e aprimorar a interface Drupal | Menor custo incremental. Estimativa de **1–3 pessoa-semanas** para adaptar e validar até três fluxos existentes para celular e pt-BR; varia conforme traduções e mudanças necessárias. | Usa formulários, permissões e validações já executados no servidor; preserva quick forms compostos, administração e uma única superfície de autenticação. | Menos controle sobre navegação e interação focadas; melhorias visuais continuam ligadas ao ciclo Drupal e às escolhas existentes de formulários. É a alternativa de contingência se o protótipo não mostrar ganho de uso. |
| Cliente React/TypeScript sobre JSON:API | Estimativa inicial de **6–10 pessoa-semanas** para login/API, busca e detalhe de Asset, tarefas e até dois fluxos simples de gravação, acessibilidade básica e piloto. Cada fluxo composto, mapa ou operação de sincronização adiciona custo. | Permite desenhar uma experiência mobile-first pequena, independente das telas administrativas e com vocabulário pt-BR próprio. JSON:API conserva o farmOS como fonte única dos registros. | Duplica trabalho de interface, tratamento de erros, autorização, validação e testes; configurações de API/OAuth e CORS variam entre instâncias. O cliente não herda automaticamente formulários, validações ou permissões visuais do Drupal. |
| Rust/WASM no cliente | **Sem custo/benefício demonstrado para o escopo inicial**. Como ordem de grandeza, um módulo específico teria custo adicional de **1–3 pessoa-semanas** para integração, build e medição, além da manutenção do toolchain. | Pode valer para processamento local intensivo e repetido, se perfilamento mostrar que o JavaScript não atende ao tempo de resposta desejado. | Não reduz latência de rede, custo de renderização comum, espera da API ou problemas de autenticação. Traz compilação, distribuição, depuração e competências adicionais. Não usar como aposta de desempenho. |

As faixas são estimativas de planejamento, não orçamento fechado: uma pessoa engenheira familiarizada com Drupal e TypeScript, até duas instâncias-piloto e sem paridade de administração, mapas completos ou modo offline. Incluem implementação e validação do escopo citado; não incluem provisionamento de hospedagem, suporte contínuo, migração de dados ou alterações de backend. A estimativa do cliente deve ser revista depois do spike de API/autenticação.

## Decisão e limites

1. Preservar a interface Drupal como interface completa e fallback de fluxos não cobertos. Não substituir nem reescrever o backend e não criar um segundo modelo de dados persistido.
2. Fazer primeiro um protótipo React/TypeScript de escopo curto. Se aprovado, o cliente apenas lê e grava recursos farmOS via JSON:API. Não criar uma API paralela nem espelhar entidades em uma base própria. Mapas de tela/estado transitório podem existir, mas Assets, Logs, Quantities, taxonomias e permissões continuam pertencendo ao farmOS.
3. Manter a integração com a API atrás de uma fronteira pequena. Descobrir os recursos instalados em `/api` e seus esquemas em `/api/schema`; testar permissões e relações na instância alvo. Se o farmOS.js não passar pelos gates de versão e OAuth, integrar JSON:API diretamente por um cliente TypeScript pequeno, sem imitar sua camada de sincronização.
4. Não adotar farmOS.js como dependência obrigatória no primeiro corte. A documentação oficial o classifica explicitamente como **experimental**, recomenda fixar versões beta exatas, descreve suporte ao modelo farmOS 2.x e registra apenas Password Grant como método de autorização disponível no cliente. Isso não demonstra compatibilidade com farmOS 4 nem atende diretamente à recomendação geral de Authorization Code para clientes terceiros. Avaliar a biblioteca somente depois de provar a versão, compatibilidade e fluxo de autenticação com a instância escolhida.
5. Não incluir fila offline, sincronização ou edição desconectada no MVP. A documentação do farmOS.js descreve esquema em cache e merge *last-write-wins*, mas isso não resolve o contrato de gravação, persistência, repetição de requisições, conflitos compreensíveis para pessoas, dados de mídia ou comportamento quando dois usuários editam o mesmo registro. Se operação sem rede for requisito, tratá-la como fase de arquitetura própria.
6. Não usar Rust/WASM até existir um benchmark reproduzível mostrando um gargalo de computação local e melhoria suficiente para compensar a integração. O cenário mais plausível a medir seria processamento geométrico em lote ou cálculo local; a renderização do mapa e a rede precisam ser medidas separadamente.

## Autenticação, dependências e riscos

- **Pré-requisitos por instância:** confirmar versão farmOS, `farm_api`, `farm_api_oauth`, chaves OAuth, consumidor, escopos/roles, HTTPS e domínios permitidos. A documentação farmOS 4 informa que API/OAuth deixaram de estar habilitados por padrão e que chaves não são mais geradas automaticamente. Isso cria trabalho de instalação e suporte por instância, além do frontend.
- **OAuth inconsistente entre documentação geral e biblioteca:** a documentação da API recomenda Authorization Code e Refresh Token para clientes terceiros e diz que Password Grant é legado/opcional; a documentação de `farmOS.js` diz que Password Grant é o único método disponível na biblioteca. O fluxo definitivo precisa passar por spike com a versão real do servidor e o consumidor configurado. Não embutir segredo OAuth em código distribuído ao navegador; Client Credentials depende de segredo que não pode ser protegido num cliente público. Revisar onde tokens ficam, expiração, revogação e armazenamento antes do piloto; não copiar automaticamente o exemplo de `localStorage` do farmOS.js.
- **CORS e hospedagem:** se a aplicação ficar em outra origem, o consumidor OAuth precisa permitir essa origem e a implantação de cada instância precisa ser documentada. Comparar servir o bundle no mesmo domínio/path com hospedagem independente; testar preflight e cabeçalhos antes da escolha.
- **Autorização:** aplicar no servidor como fonte de verdade. Testar os perfis Manager, Worker e Viewer e respostas de acesso negado; esconder botão na interface não é controle de acesso.
- **Variedade de instalação:** tipos, bundles, campos, termos e módulos ativos podem variar. A UI deve tolerar recurso opcional ausente e não fazer a instância instalar módulos sem decisão administrativa.
- **Lógica de negócio:** operações compostas implementadas em quick forms Drupal não são automaticamente reproduzidas por criar entidades. Incluir cada operação composta somente após comparar gravações/validações e efeitos sobre dados.
- **Celular e campo:** medir em aparelhos modestos, teclado e formulários com uma mão, sol, conectividade intermitente e latência real. Sem suporte offline, avisar quando não houver conexão, preservar rascunho apenas durante a sessão se viável e não confirmar sucesso antes da resposta da API.
- **Privacidade e exposição de token:** um cliente SPA guarda credenciais no ambiente do navegador; scripts de terceiros ou XSS podem expor tokens. Rever dependências, política de conteúdo e estratégia de sessão. Se a revisão exigir segredo ou sessão segura fora do navegador, estimar um BFF como infraestrutura adicional antes de prosseguir, sem adicioná-lo por padrão.

## Plano incremental e gates

1. **Validar tarefas e linguagem (1 pessoa-semana):** observar pessoas usuárias e escolher no máximo três tarefas de campo; acordar vocabulário pt-BR, dados obrigatórios e taxa aceitável de erro. Confirmar se mapa, inventário ou gravação sem rede é essencial.
2. **Spike da instância/API (1–2 pessoa-semanas):** numa instalação farmOS 4 de teste, comprovar descoberta `/api` e `/api/schema`, escopos, CORS, OAuth do cliente, leitura filtrada/paginada e gravação/edição de um Asset e Log. Testar autorização por role, respostas de erro e requisitos de módulos/chaves. Testar farmOS.js contra essa matriz de versão/autenticação e registrar incompatibilidades. Sem alterar backend.
3. **Protótipo descartável (2–3 pessoa-semanas):** React/TypeScript em celular para busca/detalhe, tarefas e um formulário de Log. Não incluir sincronização offline nem Rust/WASM. Executar com dados de teste e comparar com o fluxo Drupal atual.
4. **Gate de decisão do MVP:** seguir somente se tarefas do piloto forem concluídas com menor tempo ou menor taxa de erro sem elevar erros de gravação, se a API/auth puder ser configurada de forma repetível e se o custo por instância for aceitável. Caso contrário, voltar a melhorias no Drupal.
5. **MVP pequeno e rollout coexistente:** implementar apenas os fluxos aprovados, observar falhas de leitura/gravação, latência e abandono, manter Drupal acessível e documentar instalação, OAuth, CORS e atualização do bundle. Expandir por fluxo com teste de regressão; reavaliar offline separadamente.

### Medidas antes de escalar

- Tempo para concluir cada tarefa e número de toques/campos; taxa de conclusão e abandono; erros de seleção e correções posteriores.
- Sucesso de leitura/gravação por role, duplicidade após retry e rejeições por validação; proporção de fluxos que ainda dependem de quick form Drupal.
- Carregamento inicial (p50/p95), tempo de resposta JSON:API (p50/p95) e consumo de dados em rede móvel com aparelhos alvo. Separar tempo de API, rede, parsing e renderização.
- Para considerar WASM: perfil de CPU em operação representativa e repetível, duração JS atual versus WASM no mesmo dispositivo, tamanho adicional do bundle e custo de build. Só avançar se a diferença melhorar uma tarefa observável do produto.
- Para considerar offline: duração e tipo das quedas de conectividade, quantos registros precisam ser criados sem rede, tolerância de perda/duplicidade, estratégia de conflito, anexos e prazo para sincronizar. Testar dois clientes editando o mesmo registro; não assumir que *last-write-wins* é aceitável.

## Fontes

- farmOS, [API e JSON:API](https://farmos.org/development/api/); documentação versionada no checkout em [docs/development/api](../development/api/index.md).
- farmOS, [autenticação OAuth](https://farmos.org/development/api/authentication/).
- farmOS, [farmOS.js: aviso experimental e compatibilidade](https://farmos.org/development/farmos-js/), [remotes/autorização](https://farmos.org/development/farmos-js/remotes/), [schemas](https://farmos.org/development/farmos-js/schemata/) e [entidades](https://farmos.org/development/farmos-js/entities/).
- farmOS, [mudanças de v4 e v3.5](https://farmos.org/blog/2026/farmos-v4-and-v3.5/).
- Observação da pesquisa externa em 2026-10-22: a documentação geral da API recomenda Authorization Code/Refresh Token para terceiros; a página remotes do farmOS.js aponta Password Grant como único método disponível no cliente. Confirmar o estado para a versão concreta antes de qualquer integração.
