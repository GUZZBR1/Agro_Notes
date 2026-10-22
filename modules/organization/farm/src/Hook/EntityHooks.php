<?php

declare(strict_types=1);

namespace Drupal\farm_farm\Hook;

use Drupal\Core\Hook\Attribute\Hook;

/**
 * Entity hook implementations for farm_farm.
 */
class EntityHooks {

  /**
   * Implements hook_entity_type_alter().
   */
  #[Hook('entity_type_alter')]
  public function entityTypeAlter(array &$entity_types) {

    // Add a constraint to log entities to ensure that all referenced assets are
    // in the same farm organization.
    if (isset($entity_types['log'])) {
      $entity_types['log']->addConstraint('LogAssetFarm');
    }
  }

}
