<?php

declare(strict_types=1);

namespace Drupal\farm_log_quantity;

/**
 * Helper methods for farm_log_quantity.
 */
class FarmLogQuantityHelper {

  /**
   * Returns the default quantity type.
   *
   * @param string|null $log_type
   *   The log type (optional).
   *
   * @return string|null
   *   The log's default quantity type, or NULL if a default is unavailable.
   */
  public static function defaultQuantityType(?string $log_type = NULL): ?string {

    // If a log type is specified, attempt to look up the default quantity type
    // from the log type's third party settings.
    if (!empty($log_type)) {
      $log_type_definition = \Drupal::service('entity_type.manager')->getStorage('log_type')->load($log_type);
      $type = $log_type_definition->getThirdPartySetting('farm_log_quantity', 'default_quantity_type', NULL);
      if (!empty($type)) {
        return $type;
      }
    }

    // If the farm_quantity_standard module is installed, default to "standard".
    if (\Drupal::moduleHandler()->moduleExists('farm_quantity_standard')) {
      return 'standard';
    }

    // Look up all quantity types and take the first one.
    /** @var \Drupal\quantity\Entity\QuantityInterface[] $quantity_types */
    $quantity_types = \Drupal::service('entity_type.manager')->getStorage('quantity_type')->loadMultiple();
    foreach ($quantity_types as $quantity_type) {
      if (!empty($quantity_type->id())) {
        return $quantity_type->id();
      }
    }

    // Otherwise return NULL.
    return NULL;
  }

}
