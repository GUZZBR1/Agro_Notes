<?php

declare(strict_types=1);

namespace Drupal\farm_import_csv\Hook;

use Drupal\Core\Hook\Attribute\Hook;

/**
 * Update hook implementations for farm_import_csv.
 */
class UpdateHooks {

  /**
   * Implements hook_farm_update_managed_config().
   */
  #[Hook('farm_update_managed_config')]
  public function farmUpdateManagedConfig() {
    return [
      'views.view.farm_import_csv_asset',
      'views.view.farm_import_csv_log',
      'views.view.farm_import_csv_taxonomy_term',
    ];
  }

}
