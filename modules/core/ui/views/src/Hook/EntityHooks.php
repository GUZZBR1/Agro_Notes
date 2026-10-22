<?php

declare(strict_types=1);

namespace Drupal\farm_ui_views\Hook;

use Drupal\Core\Hook\Attribute\Hook;

/**
 * Entity hook implementations for farm_ui_views.
 */
class EntityHooks {

  /**
   * Implements hook_entity_type_build().
   */
  #[Hook('entity_type_build')]
  public function entityTypeBuild(array &$entity_types) {
    /** @var \Drupal\Core\Entity\EntityTypeInterface[] $entity_types */

    // Override the "collection" link path for assets, logs, organizations,
    // and plans to use the Views provided by this module.
    $collection_paths = [
      'asset' => '/assets',
      'log' => '/logs',
      'organization' => '/organizations',
      'plan' => '/plans',
    ];
    foreach ($collection_paths as $entity_type => $path) {
      if (!empty($entity_types[$entity_type])) {
        $entity_types[$entity_type]->setLinkTemplate('collection', $path);
      }
    }
  }

}
