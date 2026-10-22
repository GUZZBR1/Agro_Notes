<?php

declare(strict_types=1);

namespace Drupal\farm_ui_map\Hook;

use Drupal\Core\Entity\Display\EntityViewDisplayInterface;
use Drupal\Core\Entity\EntityDisplayRepositoryInterface;
use Drupal\Core\Entity\EntityInterface;
use Drupal\Core\Hook\Attribute\Hook;
use Drupal\Core\Routing\RouteMatchInterface;

/**
 * Theme hook implementations for farm_ui_map.
 */
class ThemeHooks {

  public function __construct(
    protected EntityDisplayRepositoryInterface $entityDisplayRepository,
    protected RouteMatchInterface $routeMatch,
  ) {}

  /**
   * Implements hook_ENTITY_TYPE_view().
   */
  #[Hook('asset_view')]
  public function assetView(array &$build, EntityInterface $entity, EntityViewDisplayInterface $display, $view_mode) {
    /** @var \Drupal\asset\Entity\AssetInterface $entity */

    // Bail if not the map_popup view mode.
    if ($view_mode !== 'map_popup') {
      return $build;
    }

    // The default view mode is used if a map_popup view mode is not provided.
    // Alter the default view mode to only include common fields.
    $view_mode_options = $this->entityDisplayRepository->getViewModeOptionsByBundle('asset', $entity->bundle());
    if (!array_key_exists($view_mode, $view_mode_options)) {
      $common_fields = ['name', 'type', 'flag', 'notes', 'location'];
      $build = array_filter($build, function ($key) use ($common_fields) {
        return strpos($key, '#') === 0 || in_array($key, $common_fields);
      }, ARRAY_FILTER_USE_KEY);
    }

    return $build;
  }

  /**
   * Implements hook_preprocess_HOOK().
   */
  #[Hook('preprocess_block__farm_local_actions_block')]
  public function preprocessBlockFarmLocalActionsBlock(&$variables, $block) {
    if ($this->routeMatch->getRouteName() === 'farm_ui_map.asset.map_popup') {
      $variables['content']['#dropbutton_type'] = 'small';
    }
  }

  /**
   * Implements hook_farm_dashboard_panes().
   */
  #[Hook('farm_dashboard_panes')]
  public function farmDashboardPanes() {
    return [
      'dashboard_map' => [
        'block' => 'map_block',
        'args' => [
          'map_type' => 'dashboard',
        ],
        'region' => 'top',
      ],
    ];
  }

  /**
   * Implements hook_menu_local_actions_alter().
   */
  #[Hook('menu_local_actions_alter')]
  public function menuLocalActionsAlter(&$local_actions) {

    // Include asset.add.log.* location actions on the asset.map_popup route.
    foreach ($local_actions as $id => $local_action) {
      if (strpos($id, 'farm.actions:farm.asset.add.log.') === 0) {
        $local_actions[$id]['appears_on'][] = 'farm_ui_map.asset.map_popup';
      }
    }
  }

}
