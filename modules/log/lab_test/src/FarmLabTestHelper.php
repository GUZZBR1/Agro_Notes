<?php

declare(strict_types=1);

namespace Drupal\farm_lab_test;

use Drupal\Core\Entity\ContentEntityInterface;
use Drupal\Core\Field\FieldStorageDefinitionInterface;

/**
 * Helper methods for farm_lab_test.
 */
class FarmLabTestHelper {

  /**
   * Lab test type options helper.
   *
   * @return array
   *   Returns an array of lab test types for use in form select options.
   */
  public static function labTestTypeOptions(): array {
    /** @var \Drupal\farm_lab_test\Entity\FarmLabTestTypeInterface[] $lab_test_types */
    $lab_test_types = \Drupal::entityTypeManager()->getStorage('lab_test_type')->loadMultiple();
    $options = [];
    foreach ($lab_test_types as $id => $lab_test_type) {
      $options[$id] = $lab_test_type->getLabel();
    }
    return $options;
  }

  /**
   * Allowed values callback function for the lab test type field.
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
  public static function labTestTypeAllowedValues(FieldStorageDefinitionInterface $definition, ?ContentEntityInterface $entity = NULL, bool &$cacheable = TRUE): array {
    return FarmLabTestHelper::labTestTypeOptions();
  }

}
