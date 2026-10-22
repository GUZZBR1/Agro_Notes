# Demonstração local de uma fazenda mista

Esta configuração inicia farmOS localmente com um conjunto inicial para
lavoura e pecuária. Ela é destinada a uma única pessoa no mesmo computador e
não substitui uma instalação de produção.

Na raiz do repositório, execute:

    mkdir -p docker/local/www docker/local/db
    docker compose -p farmos-local -f docker/docker-compose.local.yml up -d

Na primeira inicialização, o instalador cria o site, seleciona português do
Brasil para a interface, usa `d/m/Y` para datas curtas e habilita módulos para
áreas, plantas, animais, semeadura, transplante, colheita, nascimento, registros
médicos, atividades e movimentações. A senha administrativa é gerada
aleatoriamente e não é exibida. Se precisar entrar como administradora, redefina
a senha com Drush.

O instalador concede ao papel anônimo permissões de criação e edição por tipo
de ativo e registro que estiver habilitado. Ele reaplica essas permissões ao ser
executado novamente, inclusive em sites locais já instalados. Para atualizar
uma instalação existente, execute:

    docker compose -p farmos-local -f docker/docker-compose.local.yml run --rm install

## Limites de acesso

O serviço web fica vinculado a `127.0.0.1`. Para atender ao fluxo local sem
tela de login, esta demonstração concede acesso anônimo à criação e gestão de
registros de ativos, atividades e quantidades; as alterações ficam sem
atribuição a uma pessoa. As páginas de login e recuperação de senha redirecionam
ao painel. Rotas negadas mantêm o status de acesso negado, mas exibem o painel
sem formulário de login. Não exponha esta configuração à rede nem a use em
produção. Uma instalação de produção mantém autenticação normal e escolhe
módulos pelo assistente de configuração do farmOS.

Arquivos e banco de dados ficam em `docker/local/`, pasta ignorada pelo Git.
Para parar os serviços:

    docker compose -p farmos-local -f docker/docker-compose.local.yml down

## Conferir a instalação

Verifique a saída do instalador, liste os módulos habilitados e abra
`http://localhost`:

    docker compose -p farmos-local -f docker/docker-compose.local.yml logs install
    docker compose -p farmos-local -f docker/docker-compose.local.yml exec www /opt/drupal/vendor/bin/drush pm:list --status=enabled

O conjunto inicial mantém opcionais inventário de materiais, animais agrupados
ou por contagem, análises de solo e água, estruturas, equipamentos, produtos e
integrações de API. Habilite esses módulos pelo farmOS ou com Drush quando a
operação precisar deles.
