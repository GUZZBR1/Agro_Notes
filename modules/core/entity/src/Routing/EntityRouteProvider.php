<?php

declare(strict_types=1);

namespace Drupal\farm_entity\Routing;

use Drupal\Core\Entity\EntityTypeInterface;
use Drupal\entity\Routing\DefaultHtmlRouteProvider;

/**
 * Override entity route provider methods.
 */
class EntityRouteProvider extends DefaultHtmlRouteProvider {

  /**
   * {@inheritdoc}
   */
  protected function getAddFormRoute(EntityTypeInterface $entity_type) {

    // Override the add form title callback.
    $route = parent::getAddFormRoute($entity_type);
    if (!is_null($route)) {
      $route->setDefault('_title_callback', '\Drupal\farm_entity\Controller\EntityController::addBundleTitle');
      return $route;
    }
    return NULL;
  }

  /**
   * {@inheritdoc}
   */
  protected function getEditFormRoute(EntityTypeInterface $entity_type) {

    // Override the edit form title callback.
    $route = parent::getEditFormRoute($entity_type);
    if (!is_null($route)) {
      $route->setDefault('_title_callback', '\Drupal\farm_entity\Controller\EntityController::editTitle');
      return $route;
    }
    return NULL;
  }

}
