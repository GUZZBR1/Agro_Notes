<?php

declare(strict_types=1);

namespace Drupal\farm_location;

use Drupal\Core\Entity\ContentEntityInterface;
use Drupal\Core\Field\FieldDefinitionInterface;

/**
 * Default value callbacks for location fields.
 */
class LocationDefaultValues {

  /**
   * Sets the default value for asset is_location boolean field.
   *
   * @param \Drupal\Core\Entity\ContentEntityInterface $entity
   *   The entity being created.
   * @param \Drupal\Core\Field\FieldDefinitionInterface $definition
   *   The field definition.
   *
   * @return array
   *   An array of default value keys with each entry keyed with the "value"
   *   key.
   *
   * @see \Drupal\Core\Field\FieldConfigBase::getDefaultValue()
   */
  public static function isLocation(ContentEntityInterface $entity, FieldDefinitionInterface $definition): array {
    $default = FALSE;

    // Load the entity bundle.
    $bundle = \Drupal::service('entity_type.manager')->getStorage('asset_type')->load($entity->bundle());

    // Use the bundle's is_location third-party setting as a default.
    $is_location = $bundle->getThirdPartySetting('farm_location', 'is_location');
    if (!empty($is_location)) {
      $default = TRUE;
    }

    return [
      ['value' => $default],
    ];
  }

  /**
   * Sets the default value for asset is_fixed boolean field.
   *
   * @param \Drupal\Core\Entity\ContentEntityInterface $entity
   *   The entity being created.
   * @param \Drupal\Core\Field\FieldDefinitionInterface $definition
   *   The field definition.
   *
   * @return array
   *   An array of default value keys with each entry keyed with the "value"
   *   key.
   *
   * @see \Drupal\Core\Field\FieldConfigBase::getDefaultValue()
   */
  public static function isFixed(ContentEntityInterface $entity, FieldDefinitionInterface $definition): array {
    $default = FALSE;

    // Load the entity bundle.
    $bundle = \Drupal::service('entity_type.manager')->getStorage('asset_type')->load($entity->bundle());

    // Use the bundle's is_fixed third-party setting as a default.
    $is_fixed = $bundle->getThirdPartySetting('farm_location', 'is_fixed');
    if (!empty($is_fixed)) {
      $default = TRUE;
    }

    return [
      ['value' => $default],
    ];
  }

  /**
   * Sets the default value for log movement boolean field.
   *
   * @param \Drupal\Core\Entity\ContentEntityInterface $entity
   *   The entity being created.
   * @param \Drupal\Core\Field\FieldDefinitionInterface $definition
   *   The field definition.
   *
   * @return array
   *   An array of default value keys with each entry keyed with the "value"
   *   key.
   *
   * @see \Drupal\Core\Field\FieldConfigBase::getDefaultValue()
   */
  public static function isMovement(ContentEntityInterface $entity, FieldDefinitionInterface $definition): array {
    $default = FALSE;

    // Load the entity bundle.
    $bundle = \Drupal::service('entity_type.manager')->getStorage('log_type')->load($entity->bundle());

    // Use the bundle's is_movement third-party setting as a default.
    $is_movement = $bundle->getThirdPartySetting('farm_location', 'is_movement');
    if (!empty($is_movement)) {
      $default = TRUE;
    }

    return [
      ['value' => $default],
    ];
  }

}
