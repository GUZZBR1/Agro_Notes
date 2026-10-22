<?php

declare(strict_types=1);

namespace Drupal\data_stream\Hook;

use Drupal\Core\Hook\Attribute\Hook;

/**
 * Update hook implementations for data_stream.
 */
class UpdateHooks {

  /**
   * Implements hook_farm_update_managed_config().
   */
  #[Hook('farm_update_managed_config')]
  public function farmUpdateManagedConfig() {
    return [
      'views.view.data_stream_basic_data',
    ];
  }

}
