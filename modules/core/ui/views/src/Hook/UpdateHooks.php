<?php

declare(strict_types=1);

namespace Drupal\farm_ui_views\Hook;

use Drupal\Core\Hook\Attribute\Hook;

/**
 * Update hook implementations for farm_ui_views.
 */
class UpdateHooks {

  /**
   * Implements hook_farm_update_managed_config().
   */
  #[Hook('farm_update_managed_config')]
  public function farmUpdateManagedConfig() {
    return [
      'views.view.farm_asset',
      'views.view.farm_inventory',
      'views.view.farm_log',
      'views.view.farm_log_quantity',
      'views.view.farm_organization',
      'views.view.farm_organization_asset',
      'views.view.farm_organization_log',
      'views.view.farm_people',
      'views.view.farm_plan',
    ];
  }

}
