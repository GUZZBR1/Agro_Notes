<?php

declare(strict_types=1);

namespace Drupal\farm_ui_views\Hook;

use Drupal\Core\Extension\ModuleHandlerInterface;
use Drupal\Core\Hook\Attribute\Hook;

/**
 * Theme hook implementations for farm_ui_views.
 */
class ThemeHooks {

  public function __construct(
    protected ModuleHandlerInterface $moduleHandler,
  ) {}

  /**
   * Implements hook_local_tasks_alter().
   */
  #[Hook('local_tasks_alter')]
  public function localTasksAlter(&$local_tasks) {

    // Remove the local task plugin definition for farm entity collection links.
    $entity_types = [
      'asset',
      'log',
      'organization',
      'plan',
    ];
    foreach ($entity_types as $type) {
      if (!empty($local_tasks["entity.{$type}.collection"])) {
        unset($local_tasks["entity.{$type}.collection"]);
      }
    }
  }

  /**
   * Implements hook_farm_dashboard_groups().
   */
  #[Hook('farm_dashboard_groups')]
  public function farmDashboardGroups() {
    $groups = [];

    // If the plan module is enabled, add a plans group.
    if ($this->moduleHandler->moduleExists('plan')) {
      $groups['second']['plans'] = [
        '#weight' => 10,
      ];
    }

    // Add a logs group.
    $groups['first']['logs'] = [
      '#weight' => 10,
    ];
    return $groups;
  }

  /**
   * Implements hook_farm_dashboard_panes().
   */
  #[Hook('farm_dashboard_panes')]
  public function farmDashboardPanes() {
    $panes = [];

    // If the plan module is enabled, add active plans pane.
    if ($this->moduleHandler->moduleExists('plan')) {
      $panes['active_plans'] = [
        'view' => 'farm_plan',
        'view_display_id' => 'block_active',
        'group' => 'plans',
        'region' => 'second',
        'weight' => 0,
      ];
    }

    // Add upcoming and late logs panes.
    $panes['upcoming_tasks'] = [
      'view' => 'farm_log',
      'view_display_id' => 'block_upcoming',
      'group' => 'logs',
      'region' => 'first',
      'weight' => 10,
    ];
    $panes['late_tasks'] = [
      'view' => 'farm_log',
      'view_display_id' => 'block_late',
      'group' => 'logs',
      'region' => 'first',
      'weight' => 11,
    ];

    return $panes;
  }

}
