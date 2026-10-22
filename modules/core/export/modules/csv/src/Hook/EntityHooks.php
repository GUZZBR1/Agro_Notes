<?php

declare(strict_types=1);

namespace Drupal\farm_export_csv\Hook;

use Drupal\Core\Hook\Attribute\Hook;
use Drupal\farm_export_csv\Form\EntityCsvActionForm;
use Drupal\farm_export_csv\Routing\EntityCsvActionRouteProvider;

/**
 * Entity hook implementations for farm_export_csv.
 */
class EntityHooks {

  /**
   * Implements hook_entity_type_build().
   */
  #[Hook('entity_type_build')]
  public function entityTypeBuild(array &$entity_types) {

    // Enable the entity CSV export action on assets, logs, and quantities.
    foreach (['asset', 'log', 'quantity'] as $entity_type) {
      if (!empty($entity_types[$entity_type])) {
        $route_providers = $entity_types[$entity_type]->getRouteProviderClasses();
        $route_providers['csv'] = EntityCsvActionRouteProvider::class;
        $entity_types[$entity_type]->setHandlerClass('route_provider', $route_providers);
        $entity_types[$entity_type]->setLinkTemplate('csv-action-form', '/' . $entity_type . '/csv');
        $entity_types[$entity_type]->setFormClass('csv-action-form', EntityCsvActionForm::class);
      }
    }
  }

}
