<?php

declare(strict_types=1);

namespace Drupal\farm_ui_dashboard\Controller;

use Drupal\Component\Plugin\Exception\PluginException;
use Drupal\Core\Block\BlockManagerInterface;
use Drupal\Core\Controller\ControllerBase;
use Drupal\Core\DependencyInjection\AutowireTrait;
use Drupal\Core\Entity\EntityStorageInterface;
use Drupal\Core\Layout\LayoutPluginManagerInterface;
use Drupal\Core\Url;
use Drupal\views\Views;

/**
 * Dashboard controller.
 *
 * @ingroup farm
 */
class DashboardController extends ControllerBase {

  use AutowireTrait;

  public function __construct(
    protected LayoutPluginManagerInterface $layoutPluginManager,
    protected BlockManagerInterface $blockManager,
  ) {}

  /**
   * Builds the farm dashboard page.
   *
   * @return array
   *   Render array.
   *
   * @throws \Drupal\Component\Plugin\Exception\InvalidPluginDefinitionException
   * @throws \Drupal\Component\Plugin\Exception\PluginNotFoundException
   */
  public function dashboard() {

    // Start with the guided introduction and preserve module dashboard groups.
    $build = [
      'top' => [
        'getting_started' => $this->buildGettingStarted(),
      ],
    ];
    $groups = $this->moduleHandler()->invokeAll('farm_dashboard_groups');
    foreach ($groups as $region => $region_groups) {
      $build[$region] = array_merge($build[$region] ?? [], $region_groups);
    }

    // Ask modules for dashboard panes.
    $panes = $this->moduleHandler()->invokeAll('farm_dashboard_panes');
    $this->moduleHandler()->alter('farm_dashboard_panes', $panes);

    // Add each pane to the dashboard.
    foreach ($panes as $id => $pane) {

      // Keep the world map off the first-run dashboard.
      if ($id === 'dashboard_map') {
        continue;
      }

      // Set default values.
      $args = [];
      $output = [];
      $title = '';
      $region = 'first';
      $group = 'default';
      $weight = 0;

      // Use any provided args.
      if (!empty($pane['args'])) {
        $args = $pane['args'];
      }

      // If 'view' and 'view_display_id' are provided, display the view.
      if (!empty($pane['view']) && !empty($pane['view_display_id'])) {

        // Load the view. Note that this
        // returns a special ViewExecutable object, not a View entity.
        $view = Views::getView($pane['view']);

        // Skip if the view doesn't exist or access check fails.
        if (empty($view) || !$view->access($pane['view_display_id'])) {
          continue;
        }

        // Set the display so we get the correct title.
        $view->setDisplay($pane['view_display_id']);

        // Set the title.
        $title = $view->getTitle();

        // Build the views renderable output.
        $output = $view->buildRenderable($pane['view_display_id'], $args);
      }

      // Or if a block is provided, display the block.
      elseif (!empty($pane['block'])) {

        // Create an instance of the block plugin.
        // Skip if a plugin exception is thrown.
        try {
          $block = $this->blockManager->createInstance($pane['block'], $args);
        }
        catch (PluginException $e) {
          continue;
        }

        // Skip if block access check fails.
        if (!$block->access($this->currentUser())) {
          continue;
        }

        // Build renderable array of the block.
        $output = $block->build();
      }

      // If a specific title was provided, use it.
      if (!empty($pane['title'])) {
        $title = $pane['title'];
      }

      // If a region was provided, use it.
      if (!empty($pane['region'])) {
        $region = $pane['region'];
      }

      // If a group was provided, use it.
      if (!empty($pane['group'])) {
        $group = $pane['group'];
      }

      // If a weight was provided, use it.
      if (!empty($pane['weight'])) {
        $weight = $pane['weight'];
      }

      // Create a container for the dashboard pane.
      $container = [
        '#type' => 'container',
        '#weight' => $weight,
        '#attributes' => [
          'class' => ['dashboard-pane'],
        ],
      ];

      // If a title is set, make it a fieldset.
      if (!empty($title)) {
        $container['#type'] = 'fieldset';
        $container['#title'] = $title;
      }

      // Include output inside the container.
      $container[] = $output;

      // Add the container to the build array.
      $build[$region][$group][$id] = $container;
    }

    // Get the layout.
    $layoutInstance = $this->layoutPluginManager->createInstance('layout_twocol', []);

    // Define the regions.
    $region_names = ['top', 'first', 'second', 'bottom'];
    $regions = [];
    foreach ($region_names as $name) {
      $regions[$name] = !empty($build[$name]) ? $build[$name] : [];
    }

    // Build the layout.
    $render = $layoutInstance->build($regions);

    return $render;
  }

  /**
   * Builds a first-run guide using counts from the current farm.
   */
  protected function buildGettingStarted(): array {
    $asset_storage = $this->entityTypeManager()->getStorage('asset');
    $land_count = $this->countAssets($asset_storage, ['land']);
    $animal_count = $this->countAssets($asset_storage, ['animal']);
    $plant_count = $this->countAssets($asset_storage, ['plant']);
    $log_count = (int) $this->entityTypeManager()->getStorage('log')->getAggregateQuery()
      ->accessCheck(TRUE)
      ->count()
      ->execute();
    $completed = (int) ($land_count > 0) + (int) (($animal_count + $plant_count) > 0) + (int) ($log_count > 0);

    return [
      '#type' => 'container',
      '#attributes' => ['class' => ['farm-dashboard-start']],
      '#attached' => ['library' => ['farm_ui_dashboard/getting_started']],
      '#cache' => [
        'contexts' => ['user.permissions'],
        'tags' => ['asset_list', 'log_list', 'config:asset_type_list', 'config:log_type_list'],
      ],
      'title' => [
        '#type' => 'html_tag',
        '#tag' => 'h2',
        '#value' => $this->t('Sua fazenda começa aqui'),
      ],
      'intro' => [
        '#type' => 'html_tag',
        '#tag' => 'p',
        '#value' => $this->t('Siga estes passos para organizar a propriedade e começar a registrar o que acontece nela.'),
      ],
      'progress' => [
        '#type' => 'html_tag',
        '#tag' => 'p',
        '#value' => $this->t('@completed de 3 etapas concluídas', ['@completed' => $completed]),
        '#attributes' => ['class' => ['farm-dashboard-start__progress']],
      ],
      'steps' => [
        '#type' => 'container',
        '#attributes' => ['class' => ['farm-dashboard-start__steps']],
        'property' => $this->buildStep(
          1,
          $this->t('Cadastre a primeira área'),
          $this->t('Comece registrando a propriedade ou outra área da fazenda. Os limites no mapa podem ser desenhados depois.'),
          $land_count ? $this->formatPlural($land_count, '1 área cadastrada', '@count áreas cadastradas') : $this->t('Nenhuma área cadastrada ainda.'),
          $land_count > 0,
          [
            $this->createLink($this->t('Cadastrar propriedade'), 'entity.asset.add_form', ['asset_type' => 'land'], 'button button--primary'),
          ],
        ),
        'records' => $this->buildStep(
          2,
          $this->t('Cadastre áreas, talhões ou animais'),
          $this->t('Inclua os animais e as culturas da fazenda. Você também pode organizar áreas em talhões.'),
          $this->t('@areas áreas, @animals animais e @plants plantas cadastrados', ['@areas' => $land_count, '@animals' => $animal_count, '@plants' => $plant_count]),
          ($land_count + $animal_count + $plant_count) > 0,
          [
            $this->createLink($this->t('Adicionar talhão'), 'entity.asset.add_form', ['asset_type' => 'land']),
            $this->createLink($this->t('Adicionar animal'), 'entity.asset.add_form', ['asset_type' => 'animal']),
            $this->createLink($this->t('Adicionar cultura'), 'entity.asset.add_form', ['asset_type' => 'plant']),
          ],
        ),
        'activity' => $this->buildStep(
          3,
          $this->t('Registre a primeira atividade'),
          $this->t('Anote um plantio, manejo, observação ou outra atividade para manter o histórico da fazenda.'),
          $this->formatPlural($log_count, '1 atividade registrada', '@count atividades registradas'),
          $log_count > 0,
          [
            $this->createLink($this->t('Registrar atividade'), 'entity.log.add_page', [], 'button button--primary'),
          ],
        ),
      ],
    ];
  }

  /**
   * Counts visible, active assets from the specified types.
   */
  protected function countAssets(EntityStorageInterface $storage, array $types): int {
    return (int) $storage->getAggregateQuery()
      ->accessCheck(TRUE)
      ->condition('type', $types, 'IN')
      ->condition('archived', FALSE)
      ->count()
      ->execute();
  }

  /**
   * Builds one step in the getting started guide.
   */
  protected function buildStep(int $number, $title, $description, $count, bool $complete, array $links): array {
    return [
      '#type' => 'container',
      '#attributes' => [
        'class' => ['farm-dashboard-step', $complete ? 'is-complete' : 'is-pending'],
      ],
      'number' => [
        '#type' => 'html_tag',
        '#tag' => 'span',
        '#value' => (string) $number,
        '#attributes' => ['class' => ['farm-dashboard-step__number']],
      ],
      'title' => [
        '#type' => 'html_tag',
        '#tag' => 'h2',
        '#value' => $title,
      ],
      'description' => [
        '#type' => 'html_tag',
        '#tag' => 'p',
        '#value' => $description,
      ],
      'count' => [
        '#type' => 'html_tag',
        '#tag' => 'p',
        '#value' => $count,
        '#attributes' => ['class' => ['farm-dashboard-step__count']],
      ],
      'status' => [
        '#type' => 'html_tag',
        '#tag' => 'p',
        '#value' => $complete ? $this->t('Etapa concluída') : $this->t('Próximo passo'),
        '#attributes' => ['class' => ['farm-dashboard-step__status']],
      ],
      'actions' => [
        '#type' => 'container',
        '#attributes' => ['class' => ['farm-dashboard-step__actions']],
        'items' => $links,
      ],
    ];
  }

  /**
   * Creates a route link for a getting started action.
   */
  protected function createLink($title, string $route_name, array $parameters = [], string $class = 'button'): array {
    return [
      '#type' => 'link',
      '#title' => $title,
      '#url' => Url::fromRoute($route_name, $parameters),
      '#attributes' => ['class' => [$class]],
    ];
  }

}
