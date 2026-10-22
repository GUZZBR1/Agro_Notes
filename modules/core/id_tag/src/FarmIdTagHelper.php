<?php

declare(strict_types=1);

namespace Drupal\farm_id_tag;

/**
 * Helper methods for farm_id_tag.
 */
class FarmIdTagHelper {

  /**
   * ID tag type options helper.
   *
   * @param string $bundle
   *   The asset bundle to get allowed values for.
   *
   * @return array
   *   Returns an array of allowed values for use in form select options.
   */
  public static function idTagTypeOptions(string $bundle): array {
    /** @var \Drupal\farm_id_tag\Entity\FarmIDTagTypeInterface[] $types */
    $types = \Drupal::entityTypeManager()->getStorage('tag_type')->loadMultiple();
    $options = [];
    foreach ($types as $id => $type) {
      $bundles = $type->getBundles();
      if (empty($bundles) || in_array($bundle, $bundles)) {
        $options[$id] = $type->getLabel();
      }
    }
    return $options;
  }

}
