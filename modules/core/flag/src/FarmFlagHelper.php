<?php

declare(strict_types=1);

namespace Drupal\farm_flag;

use Drupal\Core\Entity\ContentEntityInterface;
use Drupal\Core\Field\FieldStorageDefinitionInterface;

/**
 * Helper methods for farm_flag.
 */
class FarmFlagHelper {

  /**
   * Flag options helper.
   *
   * @param string|null $entity_type
   *   The entity type. Returns all flags if NULL.
   * @param string[] $bundles
   *   Array of bundle ids to limit to. An empty array loads all bundles.
   * @param bool $intersection
   *   A flag indicating to return an intersection of the allowed options.
   *
   * @return array
   *   Returns an array of flags for use in form select options.
   */
  public static function flagOptions(?string $entity_type = NULL, array $bundles = [], bool $intersection = FALSE): array {
    /** @var \Drupal\farm_flag\Entity\FarmFlagInterface[] $flags */
    $flags = \Drupal::entityTypeManager()->getStorage('flag')->loadMultiple();

    // If an entity type is provided, begin the filtering process...
    if (!empty($entity_type)) {

      // If no bundles are specified, load all bundles of the entity type.
      if (empty($bundles) && $bundle_entity_type = \Drupal::entityTypeManager()->getDefinition($entity_type)->getBundleEntityType()) {
        $bundles = array_keys(\Drupal::entityTypeManager()
          ->getStorage($bundle_entity_type)
          ->loadMultiple());
      }

      // Find only the flags that apply to the entity type and bundles.
      $flags = array_filter($flags, function ($flag) use ($entity_type, $bundles, $intersection) {
        $flag_entity_types = $flag->getEntityTypes();

        // The flag applies if no entity type is specified.
        if (empty($flag_entity_types)) {
          return TRUE;
        }

        // Otherwise the flag must specify the entity type.
        if (!array_key_exists($entity_type, $flag_entity_types)) {
          return FALSE;
        }

        // The flag applies to the bundle if:
        // Case 1: The flag specifies 'all' bundles of the entity type.
        $bundle_applies = in_array('all', $flag_entity_types[$entity_type]);

        // Case 2: No intersection.
        // The flag applies if any of the requested bundles are supported.
        $bundle_applies |= !$intersection && !empty(array_intersect($bundles, $flag_entity_types[$entity_type]));

        // Case 3: Intersection.
        // The flag only applies if all the requested bundles are supported.
        $bundle_applies |= $intersection && empty(array_diff($bundles, $flag_entity_types[$entity_type]));

        return $bundle_applies;
      });
    }

    // Assemble the options.
    $options = [];
    foreach ($flags as $id => $flag) {
      $options[$id] = $flag->label();
    }
    return $options;
  }

  /**
   * Allowed values callback function for the flags field.
   *
   * @param \Drupal\Core\Field\FieldStorageDefinitionInterface $definition
   *   The field storage definition.
   * @param \Drupal\Core\Entity\ContentEntityInterface|null $entity
   *   The entity being created if applicable.
   * @param bool $cacheable
   *   Boolean indicating if the allowed values can be cached. Defaults to TRUE.
   *
   * @return array
   *   Returns an array of allowed values for use in form select options.
   */
  public static function flagAllowedValues(FieldStorageDefinitionInterface $definition, ?ContentEntityInterface $entity = NULL, bool &$cacheable = TRUE): array {
    $entity_type = NULL;
    $bundles = [];
    if (!empty($entity)) {
      $cacheable = FALSE;
      $entity_type = $entity->getEntityTypeId();
      $bundles = [$entity->bundle()];
    }
    return FarmFlagHelper::flagOptions($entity_type, $bundles);
  }

}
