<?php

declare(strict_types=1);

namespace Drupal\farm_flag\Hook;

use Drupal\Core\Hook\Attribute\Hook;
use Drupal\farm_flag\Form\EntityFlagActionForm;
use Drupal\farm_flag\Routing\EntityFlagActionRouteProvider;

/**
 * Entity hook implementations for farm_flag.
 */
class EntityHooks {

  /**
   * Implements hook_entity_type_build().
   */
  #[Hook('entity_type_build')]
  public function entityTypeBuild(array &$entity_types) {

    // Enable the entity flag action on entity types with a flag field.
    foreach (['asset', 'log', 'plan'] as $entity_type) {
      if (!empty($entity_types[$entity_type])) {
        $route_providers = $entity_types[$entity_type]->getRouteProviderClasses();
        $route_providers['flag'] = EntityFlagActionRouteProvider::class;
        $entity_types[$entity_type]->setHandlerClass('route_provider', $route_providers);
        $entity_types[$entity_type]->setLinkTemplate('flag-action-form', '/' . $entity_type . '/flag');
        $entity_types[$entity_type]->setFormClass('flag-action-form', EntityFlagActionForm::class);
      }
    }
  }

}
