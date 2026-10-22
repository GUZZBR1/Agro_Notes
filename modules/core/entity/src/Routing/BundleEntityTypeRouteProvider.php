<?php

declare(strict_types=1);

namespace Drupal\farm_entity\Routing;

use Drupal\Core\Entity\EntityTypeInterface;
use Drupal\entity\Routing\DefaultHtmlRouteProvider;

/**
 * Deny access to the entity type add form.
 *
 * New entity types of entities with bundle plugins cannot be created in the UI.
 *
 * @See https://www.drupal.org/project/farm/issues/3196423
 */
class BundleEntityTypeRouteProvider extends DefaultHtmlRouteProvider {

  /**
   * {@inheritdoc}
   */
  protected function getAddFormRoute(EntityTypeInterface $entity_type) {
    $route = parent::getAddFormRoute($entity_type);
    if (!empty($route)) {
      $route->setRequirement('_access', 'FALSE');
    }
    return $route;
  }

}
