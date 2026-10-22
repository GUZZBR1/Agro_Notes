<?php

declare(strict_types=1);

namespace Drupal\farm_import_csv\Hook;

use Drupal\Core\Database\Connection;
use Drupal\Core\Entity\EntityInterface;
use Drupal\Core\Hook\Attribute\Hook;

/**
 * Entity hook implementations for farm_import_csv.
 */
class EntityHooks {

  public function __construct(
    protected Connection $database,
  ) {}

  /**
   * Implements hook_entity_delete().
   */
  #[Hook('entity_delete')]
  public function entityDelete(EntityInterface $entity) {

    // If an asset, log, or taxonomy term is deleted, delete associated record
    // from the farm_import_csv_entity table.
    if (in_array($entity->getEntityType()->id(), ['asset', 'log', 'taxonomy_term'])) {
      $this->database->delete('farm_import_csv_entity')->condition('entity_type', $entity->getEntityType()->id())->condition('entity_id', $entity->id())->execute();
    }
  }

}
