<?php

declare(strict_types=1);

namespace Drupal\farm_land;

use Drupal\Core\Entity\ContentEntityInterface;
use Drupal\Core\Field\FieldStorageDefinitionInterface;

/**
 * Helper methods for farm_land.
 */
class FarmLandHelper {

  /**
   * Land type options helper.
   *
   * @return array
   *   Returns an array of land types for use in form select options.
   */
  public static function landTypeOptions(): array {
    /** @var \Drupal\farm_land\Entity\FarmLandTypeInterface[] $types */
    $types = \Drupal::entityTypeManager()->getStorage('land_type')->loadMultiple();
    $options = [];
    foreach ($types as $id => $type) {
      $options[$id] = $type->getLabel();
    }
    return $options;
  }

  /**
   * Allowed values callback function for the land type field.
   *
   * @param \Drupal\Core\Field\FieldStorageDefinitionInterface $definition
   *   The field definition.
   * @param \Drupal\Core\Entity\ContentEntityInterface|null $entity
   *   The entity being created if applicable.
   * @param bool $cacheable
   *   Boolean indicating if the allowed values can be cached. Defaults to TRUE.
   *
   * @return array
   *   Returns an array of allowed values for use in form select options.
   */
  public static function landTypeAllowedValues(FieldStorageDefinitionInterface $definition, ?ContentEntityInterface $entity = NULL, bool &$cacheable = TRUE): array {
    return FarmLandHelper::landTypeOptions();
  }

}
