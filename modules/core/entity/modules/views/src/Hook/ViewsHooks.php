<?php

declare(strict_types=1);

namespace Drupal\farm_entity_views\Hook;

use Drupal\Core\Hook\Attribute\Hook;

/**
 * Views hook implementations for farm_entity_views.
 */
class ViewsHooks {

  /**
   * Implements hook_views_data_alter().
   */
  #[Hook('views_data_alter')]
  public function viewsDataAlter(array &$data) {

    // Add support for state_machine filters.
    // Because Drupal core does not provide full Views integration for base
    // fields we must manually add support for certain fields.
    // Workaround for core issue #2489476.
    $status_filter = [
      'id' => 'state_machine_state',
      'field_name' => 'status',
    ];
    $tables = [
      'log_field_data',
      'log_field_revision',
      'plan_field_data',
      'plan_field_revision',
    ];
    foreach ($tables as $table) {
      if (!empty($data[$table]['status'])) {
        $data[$table]['status']['filter'] = $status_filter;
      }
    }
  }

}
