<?php

declare(strict_types=1);

namespace Drupal\farm_api_test_allowed_resources\Hook;

use Drupal\Core\Hook\Attribute\Hook;

/**
 * API hook implementations for farm_api_test_allowed_resources.
 */
class ApiHooks {

  /**
   * Implements hook_farm_api_allow_resource_types().
   */
  #[Hook('farm_api_allow_resource_types')]
  public function farmApiAllowResourceTypes() {

    // Allow view entities.
    return [
      'view',
    ];
  }

  /**
   * Implements hook_farm_api_allow_resource_types_alter().
   */
  #[Hook('farm_api_allow_resource_types_alter')]
  public function farmApiAllowResourceTypesAlter(&$entity_types) {

    // Disallow log entities.
    if (in_array('log', $entity_types)) {
      unset($entity_types[array_search('log', $entity_types)]);
    }
  }

}
