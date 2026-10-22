<?php

declare(strict_types=1);

namespace Drupal\farm_location\Hook;

use Drupal\Core\Hook\Attribute\Hook;

/**
 * Update hook implementations for farm_location.
 */
class UpdateHooks {

  /**
   * Implements hook_farm_update_managed_config().
   */
  #[Hook('farm_update_managed_config')]
  public function farmUpdateManagedConfig() {
    return [
      'views.view.farm_asset_geojson',
      'views.view.farm_location_reference',
    ];
  }

}
