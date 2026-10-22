<?php

declare(strict_types=1);

namespace Drupal\farm_structure\Hook;

use Drupal\Core\Hook\Attribute\Hook;

/**
 * API hook implementations for farm_structure.
 */
class ApiHooks {

  /**
   * Implements hook_farm_api_allow_resource_types().
   */
  #[Hook('farm_api_allow_resource_types')]
  public function farmApiAllowResourceTypes() {
    return [
      'structure_type',
    ];
  }

}
